#!/usr/bin/env python
"""Notification worker — a separate process, never a thread inside the API.

Why a separate process
----------------------
A background delivery thread in the API would make ``/ready`` lie about a subsystem it
does not check, would contend with the per-request session model, and would double-send
every message the moment a second API replica existed. Delivery is an independent
workload with an independent failure mode, so it gets an independent process.

Behaviour
---------
- Runs bounded dispatch cycles on a fixed interval. It never busy-loops: when there is no
  work it sleeps the full interval, so an idle worker costs approximately nothing.
- Handles SIGTERM and SIGINT. It finishes the cycle in flight, then exits 0. ``docker
  compose stop`` therefore never interrupts a delivery mid-flight or leaves a row with an
  incremented attempt and no outcome.
- Spawns no threads and no children.
- Exposes no network port. Nothing needs to reach it.
- A cycle that raises is logged and the loop continues; one bad cycle must not kill the
  worker and silently stop all delivery.

Configuration
-------------
    NOTIFICATION_WORKER_INTERVAL_SECONDS   default 15
    NOTIFICATION_BATCH_SIZE                default 50
    NOTIFICATION_MAX_ATTEMPTS              default 5
    NOTIFICATION_WORKER_MAX_CYCLES         default 0 (unbounded; >0 is for tests)
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path
from types import FrameType

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

_running = True


def _handle_stop(signum: int, _frame: FrameType | None) -> None:
    """Request a clean stop. The current cycle is allowed to finish."""

    global _running
    _running = False
    _log("stop_requested", signal=signal.Signals(signum).name)


def _log(event: str, **fields: object) -> None:
    """One structured line per event, to stdout, so the container log is the log."""

    print(json.dumps({"component": "notification-worker", "event": event, **fields}), flush=True)


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    interval = float(os.getenv("NOTIFICATION_WORKER_INTERVAL_SECONDS", "15"))
    max_cycles = int(os.getenv("NOTIFICATION_WORKER_MAX_CYCLES", "0"))

    from app.commerce.db import SessionLocal
    from app.commerce.notifications import get_sender
    from app.commerce.services import dispatch_pending_notifications

    # Resolve the sender once at startup so a misconfigured channel fails immediately and
    # visibly, rather than on the first notification hours later.
    try:
        sender_name = get_sender().name
    except Exception as exc:  # noqa: BLE001
        _log("startup_failed", error=f"{type(exc).__name__}: {exc}")
        return 1

    _log("started", interval_seconds=interval, sender=sender_name, pid=os.getpid())

    cycles = 0
    while _running:
        try:
            with SessionLocal() as session:
                counts = dispatch_pending_notifications(session)
            if counts["claimed"]:
                _log("cycle", **counts)
        except Exception as exc:  # noqa: BLE001
            # A failed cycle must not kill the worker: that would stop all delivery
            # silently while the container still looks alive.
            _log("cycle_failed", error=f"{type(exc).__name__}: {exc}")

        cycles += 1
        if max_cycles and cycles >= max_cycles:
            _log("max_cycles_reached", cycles=cycles)
            break

        # Sleep in short slices so a stop signal is honoured promptly instead of waiting
        # out the whole interval.
        slept = 0.0
        while _running and slept < interval:
            time.sleep(min(0.5, interval - slept))
            slept += 0.5

    _log("stopped", cycles=cycles)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
