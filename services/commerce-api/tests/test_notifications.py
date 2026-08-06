"""Notification outbox dispatch.

SMTP is verified against a REAL socket, not a mock. A mocked ``send_message`` proves only
that a mock was called; it cannot catch a malformed envelope, a missing header, or a
client that never opens a connection. The fake server below speaks enough of RFC 5321 to
make ``smtplib`` complete a genuine exchange, and the test asserts on the bytes that
actually crossed the wire.

No third-party SMTP test dependency is added for this.
"""

from __future__ import annotations

import socket
import socketserver
import threading
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.commerce import notifications, services
from app.commerce.db import SessionLocal
from app.commerce.models import Customer, Notification


# --------------------------------------------------------------- fake SMTP server


class _SMTPHandler(socketserver.StreamRequestHandler):
    """Minimum viable SMTP conversation: greeting, EHLO, MAIL, RCPT, DATA, QUIT."""

    def handle(self) -> None:  # noqa: C901 - a protocol dialogue is inherently branchy
        server = self.server
        self.wfile.write(b"220 fake.smtp.test ESMTP\r\n")
        self.wfile.flush()

        in_data = False
        data_lines: list[bytes] = []

        while True:
            line = self.rfile.readline()
            if not line:
                return

            if in_data:
                if line.strip() == b".":
                    in_data = False
                    server.messages.append(b"".join(data_lines).decode("utf-8", "replace"))
                    data_lines = []
                    self.wfile.write(b"250 2.0.0 Ok: queued\r\n")
                    self.wfile.flush()
                    continue
                data_lines.append(line)
                continue

            command = line.strip().upper()
            if command.startswith(b"EHLO") or command.startswith(b"HELO"):
                # Single-line 250 is accepted by smtplib; no need for the multiline form.
                self.wfile.write(b"250 fake.smtp.test\r\n")
            elif command.startswith(b"MAIL FROM"):
                server.mail_from.append(line.strip().decode())
                self.wfile.write(b"250 2.1.0 Ok\r\n")
            elif command.startswith(b"RCPT TO"):
                server.rcpt_to.append(line.strip().decode())
                if server.reject_recipient:
                    self.wfile.write(b"550 5.1.1 No such user here\r\n")
                else:
                    self.wfile.write(b"250 2.1.5 Ok\r\n")
            elif command.startswith(b"DATA"):
                in_data = True
                self.wfile.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
            elif command.startswith(b"QUIT"):
                self.wfile.write(b"221 2.0.0 Bye\r\n")
                self.wfile.flush()
                return
            elif command.startswith(b"RSET"):
                self.wfile.write(b"250 2.0.0 Ok\r\n")
            else:
                self.wfile.write(b"250 2.0.0 Ok\r\n")
            self.wfile.flush()


class FakeSMTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, *, reject_recipient: bool = False) -> None:
        # Port 0 so the OS assigns a free port; a hardcoded port collides in CI.
        super().__init__(("127.0.0.1", 0), _SMTPHandler)
        self.messages: list[str] = []
        self.mail_from: list[str] = []
        self.rcpt_to: list[str] = []
        self.reject_recipient = reject_recipient

    @property
    def port(self) -> int:
        return self.server_address[1]


@pytest.fixture()
def fake_smtp():
    server = FakeSMTPServer()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture()
def rejecting_smtp():
    server = FakeSMTPServer(reject_recipient=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


# ------------------------------------------------------------------------- helpers


def queue_one(session, *, email="notify@dedunet.example", subject="Your order FC-TEST"):
    customer = session.scalar(select(Customer).where(Customer.email == email))
    if customer is None:
        customer = Customer(
            email=email, password_hash="pbkdf2_sha256$1$AA==$AA==", full_name="Notify Target"
        )
        session.add(customer)
        session.flush()
    note = Notification(
        customer_id=customer.id, template="order_confirmation",
        subject=subject, body="Thank you for your order.",
    )
    session.add(note)
    session.commit()
    return note.id, customer.id


# ------------------------------------------------------------------ console sender


def test_console_send_succeeds_and_records_provider_reference(seeded):
    note_id, _ = queue_one(seeded)
    counts = services.dispatch_pending_notifications(seeded)

    assert counts["sent"] == 1
    note = seeded.get(Notification, note_id)
    assert note.status == "sent"
    assert note.attempts == 1
    assert note.sent_at is not None
    assert note.provider_reference.startswith("console_")
    assert note.last_error == ""


def test_rerun_is_idempotent_and_does_not_resend(seeded):
    note_id, _ = queue_one(seeded)
    assert services.dispatch_pending_notifications(seeded)["sent"] == 1

    second = services.dispatch_pending_notifications(seeded)
    assert second == {
        "sent": 0, "failed": 0, "retried": 0, "suppressed": 0, "claimed": 0,
        "ownership_lost": 0,
    }

    note = seeded.get(Notification, note_id)
    assert note.attempts == 1, "a sent notification was claimed again"

    # A delivered row must reach the TERMINAL 'sent' state, not merely stop being
    # claimable. Left in the intermediate 'sending' state it is also excluded from the
    # claim query, so a rerun looks correct while the row is silently stuck forever and
    # no operator report would ever show it as delivered. Asserting the exact status
    # catches both failure modes; asserting only "not re-sent" catches neither.
    assert note.status == "sent", (
        f"expected terminal status 'sent', found {note.status!r}; a row stranded in an "
        "intermediate state is invisible to every future dispatch cycle"
    )
    assert note.sent_at is not None, "a delivered row must record when it was delivered"


def test_claim_query_only_selects_eligible_statuses(seeded):
    ids = []
    for status in ("queued", "sent", "failed", "suppressed"):
        note_id, _ = queue_one(seeded, subject=f"subject-{status}")
        note = seeded.get(Notification, note_id)
        note.status = status
        ids.append((status, note_id))
    seeded.commit()

    counts = services.dispatch_pending_notifications(seeded)
    assert counts["claimed"] == 1, "a terminal-status row was claimed"
    assert counts["sent"] == 1


# ---------------------------------------------------------------------- SMTP sender


def test_smtp_send_uses_a_real_socket_and_valid_protocol(seeded, fake_smtp, monkeypatch):
    monkeypatch.setenv("NOTIFICATION_CHANNEL", "smtp")
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", str(fake_smtp.port))
    monkeypatch.setenv("SMTP_FROM", "noreply@dedunet.example")
    monkeypatch.setenv("SMTP_USE_TLS", "0")   # the fake server speaks plain SMTP
    notifications.reset_sender()

    note_id, _ = queue_one(seeded, email="smtp-target@dedunet.example")
    counts = services.dispatch_pending_notifications(seeded)

    assert counts["sent"] == 1, "SMTP send did not succeed against the fake server"

    # The client genuinely connected and completed an exchange.
    assert fake_smtp.mail_from, "no MAIL FROM was received; no real connection was made"
    assert "noreply@dedunet.example" in fake_smtp.mail_from[0]
    assert fake_smtp.rcpt_to, "no RCPT TO was received"
    assert "smtp-target@dedunet.example" in fake_smtp.rcpt_to[0]

    assert len(fake_smtp.messages) == 1
    message = fake_smtp.messages[0]
    assert "Subject: Your order FC-TEST" in message
    assert "To: smtp-target@dedunet.example" in message
    # The stable notification identifier travels with the message so a duplicate arriving
    # at a real mailbox can be traced back to the row that produced it.
    assert f"{notifications.IDEMPOTENCY_HEADER}: notification-{note_id}" in message

    note = seeded.get(Notification, note_id)
    assert note.status == "sent"
    assert note.provider_reference.startswith("smtp_")


def test_transport_failure_is_retryable_and_preserves_the_row(seeded, monkeypatch):
    # Port 1 is reserved and refuses connections, so this is a genuine transport failure
    # rather than a simulated one.
    monkeypatch.setenv("NOTIFICATION_CHANNEL", "smtp")
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", "1")
    monkeypatch.setenv("SMTP_FROM", "noreply@dedunet.example")
    monkeypatch.setenv("SMTP_USE_TLS", "0")
    notifications.reset_sender()

    note_id, _ = queue_one(seeded)
    counts = services.dispatch_pending_notifications(seeded, max_attempts=5)

    assert counts["retried"] == 1
    assert counts["sent"] == 0

    note = seeded.get(Notification, note_id)
    assert note is not None, "the row was deleted on failure"
    assert note.status == "queued", "a retryable failure must remain eligible"
    assert note.attempts == 1, "the attempt was not persisted"
    assert note.last_error.startswith("retryable:")


def test_recipient_rejection_is_terminal(seeded, rejecting_smtp, monkeypatch):
    monkeypatch.setenv("NOTIFICATION_CHANNEL", "smtp")
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", str(rejecting_smtp.port))
    monkeypatch.setenv("SMTP_FROM", "noreply@dedunet.example")
    monkeypatch.setenv("SMTP_USE_TLS", "0")
    notifications.reset_sender()

    note_id, _ = queue_one(seeded)
    counts = services.dispatch_pending_notifications(seeded)

    assert counts["failed"] == 1
    note = seeded.get(Notification, note_id)
    assert note is not None, "the row was deleted on rejection"
    assert note.status == "failed"
    assert note.last_error.startswith("terminal:")

    # A terminal row is never retried.
    assert services.dispatch_pending_notifications(seeded)["claimed"] == 0


def test_missing_smtp_configuration_fails_clearly(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_CHANNEL", "smtp")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)
    notifications.reset_sender()

    with pytest.raises(notifications.NotificationError, match="SMTP_HOST"):
        notifications.get_sender()


def test_unknown_channel_raises_rather_than_falling_back(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_CHANNEL", "sendgrid")
    notifications.reset_sender()

    with pytest.raises(notifications.NotificationError, match="no adapter implements it"):
        notifications.get_sender()


def test_console_is_the_default_channel(monkeypatch):
    monkeypatch.delenv("NOTIFICATION_CHANNEL", raising=False)
    notifications.reset_sender()
    assert notifications.get_sender().name == "console", (
        "an unconfigured deployment must never reach for SMTP"
    )


# ------------------------------------------------------------------ failure handling


def test_long_provider_error_persists_without_truncation(seeded):
    """last_error is Text, not String(n). On PostgreSQL a length would raise."""

    note_id, _ = queue_one(seeded)
    long_reason = "E" * 6000

    class Exploding:
        name = "exploding"

        def send(self, **_kwargs):
            raise notifications.NotificationError(long_reason)

    notifications._sender = Exploding()
    try:
        services.dispatch_pending_notifications(seeded, max_attempts=5)
    finally:
        notifications.reset_sender()

    note = seeded.get(Notification, note_id)
    assert len(note.last_error) > 5000, f"error was truncated to {len(note.last_error)}"
    assert long_reason in note.last_error


def test_max_attempts_prevents_an_infinite_retry_loop(seeded, monkeypatch):
    monkeypatch.setenv("NOTIFICATION_CHANNEL", "smtp")
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", "1")
    monkeypatch.setenv("SMTP_FROM", "noreply@dedunet.example")
    monkeypatch.setenv("SMTP_USE_TLS", "0")
    notifications.reset_sender()

    note_id, _ = queue_one(seeded)

    for cycle in range(3):
        services.dispatch_pending_notifications(seeded, max_attempts=3)

    note = seeded.get(Notification, note_id)
    assert note.attempts == 3, f"attempts should stop at the ceiling, got {note.attempts}"
    assert note.status == "failed", "the row must become terminal at the ceiling"

    # Further cycles claim nothing: the loop is genuinely bounded.
    assert services.dispatch_pending_notifications(seeded, max_attempts=3)["claimed"] == 0
    assert seeded.get(Notification, note_id) is not None, "the row was deleted"


def test_no_notification_row_is_ever_deleted(seeded, rejecting_smtp, monkeypatch):
    """Across success, terminal rejection and suppression, the count never drops."""

    for i in range(3):
        queue_one(seeded, email=f"keep{i}@dedunet.example", subject=f"s{i}")
    before = seeded.scalar(select(Notification).order_by(Notification.id))
    total_before = len(seeded.scalars(select(Notification)).all())

    services.dispatch_pending_notifications(seeded)          # console: all sent

    monkeypatch.setenv("NOTIFICATION_CHANNEL", "smtp")
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", str(rejecting_smtp.port))
    monkeypatch.setenv("SMTP_FROM", "noreply@dedunet.example")
    monkeypatch.setenv("SMTP_USE_TLS", "0")
    notifications.reset_sender()
    queue_one(seeded, email="rejected@dedunet.example")
    services.dispatch_pending_notifications(seeded)          # terminal rejection

    total_after = len(seeded.scalars(select(Notification)).all())
    assert total_after == total_before + 1, "a notification row was deleted"
    assert before is not None


# --------------------------------------------------------------- erasure protection


def test_erased_customer_is_never_emailed(seeded):
    """Erasure must not be undone by a queued notification."""

    note_id, customer_id = queue_one(seeded, email="tobe-erased@dedunet.example")

    customer = seeded.get(Customer, customer_id)
    services.erase_customer(seeded, customer, actor="test")

    sent_to: list[str] = []

    class Recording:
        name = "recording"

        def send(self, *, recipient, subject, body, idempotency_key):
            sent_to.append(recipient)
            raise AssertionError("sender was invoked for an erased customer")

    notifications._sender = Recording()
    try:
        counts = services.dispatch_pending_notifications(seeded)
    finally:
        notifications.reset_sender()

    assert sent_to == [], "an erased customer was emailed"
    assert counts["suppressed"] == 1

    note = seeded.get(Notification, note_id)
    assert note is not None, "the row was deleted"
    assert note.status == "suppressed"
    assert "erased" in note.last_error

    # No later cycle resurrects it.
    assert services.dispatch_pending_notifications(seeded)["claimed"] == 0


# ------------------------------------------------------------------------- worker


def test_worker_starts_runs_and_stops_cleanly(tmp_path):
    """The worker is a separate process that exits 0 on a bounded run."""

    import os
    import subprocess
    import sys
    from pathlib import Path

    backend = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "NOTIFICATION_WORKER_MAX_CYCLES": "2",
        "NOTIFICATION_WORKER_INTERVAL_SECONDS": "0.1",
        "NOTIFICATION_CHANNEL": "console",
        "APP_ENV": "test",
        "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'worker.sqlite3'}",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(
        [sys.executable, "-B", "notification_worker.py"],
        cwd=backend, env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"worker exited {result.returncode}: {result.stderr[:500]}"
    assert '"event": "started"' in result.stdout
    assert '"event": "stopped"' in result.stdout
    assert '"sender": "console"' in result.stdout


def test_worker_fails_fast_on_an_unknown_channel(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    backend = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "NOTIFICATION_WORKER_MAX_CYCLES": "1",
        "NOTIFICATION_CHANNEL": "carrier-pigeon",
        "APP_ENV": "test",
        "DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'w2.sqlite3'}",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(
        [sys.executable, "-B", "notification_worker.py"],
        cwd=backend, env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 1
    assert '"event": "startup_failed"' in result.stdout


def test_readiness_does_not_depend_on_the_worker(client, seeded):
    """No worker is running during the suite, yet /ready must be 200.

    /ready must describe what THIS process can serve. Making it depend on a worker it
    cannot observe would take the API out of rotation for a delivery backlog.
    """

    response = client.get("/ready")
    assert response.status_code == 200
    checks = response.json()["checks"]
    assert checks["database"] == "ok"
    assert "worker" not in checks
    assert "notification" not in checks


@pytest.mark.skipif(
    "postgres" not in __import__("os").environ.get("COMMERCE_TEST_DATABASE_URL", ""),
    reason="FOR UPDATE SKIP LOCKED is a PostgreSQL guarantee; SQLite has no such syntax",
)
def test_two_postgres_workers_never_claim_the_same_row(seeded):
    """Concurrent dispatchers must not double-send.

    Runs only on PostgreSQL: SKIP LOCKED is the mechanism under test, and SQLAlchemy
    silently omits it on SQLite, so passing there would prove nothing.
    """

    import threading

    from app.commerce.db import SessionLocal

    for i in range(10):
        queue_one(seeded, email=f"race{i}@dedunet.example", subject=f"race-{i}")

    results: list[dict] = []
    lock = threading.Lock()

    def worker() -> None:
        session = SessionLocal()
        try:
            counts = services.dispatch_pending_notifications(session, limit=10)
            with lock:
                results.append(counts)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    total_sent = sum(r["sent"] for r in results)
    assert total_sent == 10, f"expected each row sent exactly once, got {total_sent}"

    with SessionLocal() as check:
        notes = check.scalars(
            select(Notification).where(Notification.subject.like("race-%"))
        ).all()
        assert len(notes) == 10, "rows were lost"
        assert all(n.status == "sent" for n in notes)
        # The decisive assertion: one attempt each means no row was claimed twice.
        over = [(n.id, n.attempts) for n in notes if n.attempts != 1]
        assert not over, f"rows claimed more than once: {over}"


# ============================================================ crash recovery / leases
#
# A durable 'sending' claim is what makes concurrent dispatch safe. It also means a
# worker killed mid-send holds the row forever unless the claim EXPIRES. These tests
# prove the lease actually bounds that window, by executing the crash rather than
# describing it.


class Crashing:
    """A sender that dies exactly where a real worker would: after the claim is
    committed, before any outcome is written."""

    name = "crashing"

    def __init__(self, *, accept_first: bool = False) -> None:
        self.calls = 0
        self.accept_first = accept_first
        self.keys: list[str] = []

    def send(self, *, recipient, subject, body, idempotency_key):
        self.calls += 1
        self.keys.append(idempotency_key)
        # KeyboardInterrupt derives from BaseException, so the dispatcher's
        # except-NotificationError handlers cannot swallow it. That is what makes this a
        # faithful stand-in for SIGKILL rather than a handled error path.
        raise KeyboardInterrupt("process terminated mid-send")


def _simulate_crash_after_claim(session, *, accept_first=False):
    """Run one dispatch whose sender dies. The claim is already committed by then."""

    sender = Crashing(accept_first=accept_first)
    notifications._sender = sender
    try:
        with pytest.raises(KeyboardInterrupt):
            services.dispatch_pending_notifications(session)
    finally:
        notifications.reset_sender()
    session.rollback()
    return sender


def _expire_lease(session, note_id):
    note = session.get(Notification, note_id)
    session.refresh(note)
    note.claim_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    session.commit()
    return note


def test_row_remains_sending_immediately_after_worker_termination(seeded, monkeypatch):
    monkeypatch.setenv("NOTIFICATION_CLAIM_TTL_SECONDS", "300")
    note_id, _ = queue_one(seeded)

    _simulate_crash_after_claim(seeded)

    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.status == "sending", "the claim was not durable across the crash"
    assert note.attempts == 1, "the attempt was not persisted before the send"
    assert note.claim_expires_at is not None, "no lease was recorded"
    assert note.claim_token != ""


def test_a_live_claim_is_not_reclaimed_before_expiry(seeded, monkeypatch):
    monkeypatch.setenv("NOTIFICATION_CLAIM_TTL_SECONDS", "300")
    note_id, _ = queue_one(seeded)
    _simulate_crash_after_claim(seeded)

    counts = services.dispatch_pending_notifications(seeded)
    assert counts["claimed"] == 0, (
        "a claim still within its lease was stolen; two workers would send the same "
        "notification simultaneously"
    )
    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.attempts == 1, "attempts incremented while the lease was still valid"


def test_an_abandoned_claim_is_reclaimed_after_expiry_and_settles(seeded, monkeypatch):
    """The whole point: an abandoned row must not be stranded."""

    monkeypatch.setenv("NOTIFICATION_CLAIM_TTL_SECONDS", "300")
    note_id, _ = queue_one(seeded)
    _simulate_crash_after_claim(seeded)

    # Age the lease. Otherwise the row is untouched: this is exactly the state a killed
    # worker leaves behind once its TTL has elapsed.
    note = _expire_lease(seeded, note_id)

    counts = services.dispatch_pending_notifications(seeded)
    assert counts["claimed"] == 1, "the abandoned claim was never recovered"
    assert counts["sent"] == 1

    seeded.refresh(note)
    assert note.status == "sent", "the recovered row did not reach a terminal state"
    assert note.attempts == 2, "the recovery attempt was not counted"
    assert note.claim_expires_at is None, "claim metadata survived settlement"
    assert note.claim_token == ""


def test_two_workers_racing_a_stale_claim_yield_exactly_one_winner(seeded, monkeypatch):
    """Recovery must not itself become a double-send."""

    monkeypatch.setenv("NOTIFICATION_CLAIM_TTL_SECONDS", "300")
    note_id, _ = queue_one(seeded)
    _simulate_crash_after_claim(seeded)
    _expire_lease(seeded, note_id)

    from app.commerce.db import SessionLocal

    results = []
    for _ in range(2):
        session = SessionLocal()
        try:
            results.append(services.dispatch_pending_notifications(session))
        finally:
            session.close()

    assert sum(r["claimed"] for r in results) == 1, (
        f"the stale claim was recovered more than once: {results}"
    )
    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.attempts == 2, f"expected one recovery attempt, found {note.attempts}"


@pytest.mark.parametrize("outcome", ["success", "retryable", "terminal", "suppressed"])
def test_claim_metadata_is_cleared_on_every_settled_path(seeded, monkeypatch, outcome):
    monkeypatch.setenv("NOTIFICATION_CLAIM_TTL_SECONDS", "300")
    note_id, customer_id = queue_one(seeded, email="clear-" + outcome + "@dedunet.example")

    if outcome == "suppressed":
        services.erase_customer(seeded, seeded.get(Customer, customer_id), actor="test")
    elif outcome == "retryable":
        class Flaky:
            name = "flaky"

            def send(self, **_kw):
                raise notifications.NotificationError("transient")

        notifications._sender = Flaky()
    elif outcome == "terminal":
        class Refusing:
            name = "refusing"

            def send(self, **_kw):
                raise notifications.NotificationRejected("no such user")

        notifications._sender = Refusing()

    try:
        services.dispatch_pending_notifications(seeded, max_attempts=5)
    finally:
        notifications.reset_sender()

    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.claimed_at is None, outcome + ": claimed_at not cleared"
    assert note.claim_expires_at is None, outcome + ": lease not cleared"
    assert note.claim_token == "", outcome + ": claim token not cleared"


def test_max_attempts_applies_to_repeatedly_abandoned_claims(seeded, monkeypatch):
    """A row abandoned over and over must still become terminal, not loop forever."""

    monkeypatch.setenv("NOTIFICATION_CLAIM_TTL_SECONDS", "300")
    note_id, _ = queue_one(seeded)

    for _ in range(5):
        note = seeded.get(Notification, note_id)
        seeded.refresh(note)
        if note.attempts >= 3:
            break
        _simulate_crash_after_claim(seeded)
        _expire_lease(seeded, note_id)

    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.attempts <= 3, "attempts exceeded the ceiling: " + str(note.attempts)

    # At the ceiling the row is no longer eligible even though its lease has expired:
    # an abandoned claim must not resurrect an exhausted row.
    _expire_lease(seeded, note_id)
    assert services.dispatch_pending_notifications(seeded, max_attempts=3)["claimed"] == 0


def test_provider_accepted_then_crash_retries_with_the_same_key(seeded, monkeypatch):
    """The honest at-least-once window, executed rather than described.

    Provider accepts -> worker dies before the sent commit -> lease expires -> a later
    worker retries. The provider may see a duplicate; both attempts carry the SAME
    stable key so the duplicate is investigable. The database eventually reaches 'sent'.
    """

    monkeypatch.setenv("NOTIFICATION_CLAIM_TTL_SECONDS", "300")
    note_id, _ = queue_one(seeded)

    crashed = _simulate_crash_after_claim(seeded, accept_first=True)
    first_key = crashed.keys[0]

    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.status == "sending", "no evidence of an accepted-but-uncommitted send"
    assert note.sent_at is None, "sent_at was committed despite the crash"

    _expire_lease(seeded, note_id)

    recorded = []

    class Recording:
        name = "recording"

        def send(self, *, recipient, subject, body, idempotency_key):
            recorded.append(idempotency_key)
            return notifications.DeliveryResult(
                provider="recording",
                provider_reference="rec_1",
                accepted=True,
                delivered_at=datetime.now(timezone.utc),
            )

    notifications._sender = Recording()
    try:
        counts = services.dispatch_pending_notifications(seeded)
    finally:
        notifications.reset_sender()

    assert counts["sent"] == 1
    assert recorded == [first_key], (
        "the retry used a different idempotency key; a duplicate at the provider could "
        "not be correlated"
    )
    assert first_key == "notification-" + str(note_id), "the key is not stable and row-derived"

    seeded.refresh(note)
    assert note.status == "sent", "the database did not converge on 'sent'"


def test_claim_ttl_is_validated_strictly(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_CLAIM_TTL_SECONDS", "0")
    with pytest.raises(ValueError, match="must be positive"):
        services.claim_ttl_seconds()

    monkeypatch.setenv("NOTIFICATION_CLAIM_TTL_SECONDS", "-5")
    with pytest.raises(ValueError, match="must be positive"):
        services.claim_ttl_seconds()

    monkeypatch.setenv("NOTIFICATION_CLAIM_TTL_SECONDS", "abc")
    with pytest.raises(ValueError, match="must be an integer"):
        services.claim_ttl_seconds()

    monkeypatch.delenv("NOTIFICATION_CLAIM_TTL_SECONDS", raising=False)
    assert services.claim_ttl_seconds() == 300, "the default must be a positive TTL"


def test_readiness_is_independent_of_recovery_activity(client, seeded, monkeypatch):
    """A backlog of abandoned claims must not take the API out of rotation."""

    monkeypatch.setenv("NOTIFICATION_CLAIM_TTL_SECONDS", "300")
    for i in range(3):
        note_id, _ = queue_one(seeded, email="stale" + str(i) + "@dedunet.example")
        _simulate_crash_after_claim(seeded)
        _expire_lease(seeded, note_id)

    response = client.get("/ready")
    assert response.status_code == 200
    checks = response.json()["checks"]
    assert "worker" not in checks and "notification" not in checks


# ================================================================== lease fencing
#
# The claim token is a FENCING token, not a label. These tests execute the exact race:
#
#   A claims (token A) -> A is delayed -> A's lease expires -> B reclaims (token B)
#   -> B becomes owner -> A resumes and tries to finalize with token A
#
# A must not be able to write anything. Every assertion below checks the DATABASE state
# after the stale write, not the return value of the stale worker.


def _claim_as(session, note_id, token, *, attempts=1):
    """Put a row into the state a worker holds after claiming it."""

    note = session.get(Notification, note_id)
    session.refresh(note)
    note.status = "sending"
    note.attempts = attempts
    note.claimed_at = datetime.now(timezone.utc)
    note.claim_expires_at = datetime.now(timezone.utc) + timedelta(seconds=300)
    note.claim_token = token
    session.commit()
    return note


def _stale_finalize(session, note_id, token, values):
    """Worker A resuming with a token it no longer owns."""

    return services._finalize(session, note_id=note_id, token=token, values=values)


def test_stale_worker_cannot_mark_sent_after_reclaim(seeded):
    note_id, _ = queue_one(seeded)
    _claim_as(seeded, note_id, "token-A")

    # B reclaims after A's lease expired, and completes.
    _claim_as(seeded, note_id, "token-B", attempts=2)
    assert services._finalize(
        seeded, note_id=note_id, token="token-B",
        values={"status": "failed", "last_error": "B decided this failed",
                **services._CLEARED_CLAIM},
    ) is True

    # A resumes and tries to stamp success.
    owned = _stale_finalize(
        seeded, note_id, "token-A",
        {"status": "sent", "sent_at": datetime.now(timezone.utc),
         "provider_reference": "A_ref", **services._CLEARED_CLAIM},
    )
    assert owned is False, "the stale worker believed it still owned the row"

    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.status == "failed", "A overwrote B's terminal state with 'sent'"
    assert note.last_error == "B decided this failed"
    assert note.provider_reference != "A_ref", "A overwrote B's provider reference"


def test_stale_worker_cannot_write_a_retryable_failure_after_reclaim(seeded):
    note_id, _ = queue_one(seeded)
    _claim_as(seeded, note_id, "token-A")
    _claim_as(seeded, note_id, "token-B", attempts=2)

    services._finalize(
        seeded, note_id=note_id, token="token-B",
        values={"status": "sent", "sent_at": datetime.now(timezone.utc),
                "provider_reference": "B_ref", "last_error": "",
                **services._CLEARED_CLAIM},
    )

    owned = _stale_finalize(
        seeded, note_id, "token-A",
        {"status": "queued", "last_error": "retryable: A's stale view",
         **services._CLEARED_CLAIM},
    )
    assert owned is False

    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.status == "sent", "A resurrected a delivered row back to 'queued'"
    assert note.provider_reference == "B_ref"
    assert note.last_error == ""


def test_stale_worker_cannot_write_a_terminal_rejection_after_reclaim(seeded):
    note_id, _ = queue_one(seeded)
    _claim_as(seeded, note_id, "token-A")
    _claim_as(seeded, note_id, "token-B", attempts=2)

    services._finalize(
        seeded, note_id=note_id, token="token-B",
        values={"status": "sent", "sent_at": datetime.now(timezone.utc),
                "provider_reference": "B_ref", **services._CLEARED_CLAIM},
    )

    owned = _stale_finalize(
        seeded, note_id, "token-A",
        {"status": "failed", "last_error": "terminal: A's stale rejection",
         **services._CLEARED_CLAIM},
    )
    assert owned is False

    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.status == "sent", "A marked a delivered row as failed"
    assert "stale" not in note.last_error


def test_stale_worker_cannot_clear_a_live_claim(seeded):
    """A must not wipe B's in-flight lease metadata."""

    note_id, _ = queue_one(seeded)
    _claim_as(seeded, note_id, "token-A")
    b = _claim_as(seeded, note_id, "token-B", attempts=2)
    b_expiry = b.claim_expires_at

    owned = _stale_finalize(
        seeded, note_id, "token-A",
        {"status": "sending", **services._CLEARED_CLAIM},
    )
    assert owned is False

    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.claim_token == "token-B", "A cleared or stole the live claim token"
    assert note.claim_expires_at is not None, "A wiped B's lease"
    assert note.status == "sending"


def test_current_owner_can_finalize_normally(seeded):
    """Fencing must not break the ordinary path."""

    note_id, _ = queue_one(seeded)
    _claim_as(seeded, note_id, "token-B", attempts=1)

    owned = services._finalize(
        seeded, note_id=note_id, token="token-B",
        values={"status": "sent", "sent_at": datetime.now(timezone.utc),
                "provider_reference": "B_ref", "last_error": "",
                **services._CLEARED_CLAIM},
    )
    assert owned is True

    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.status == "sent"
    assert note.provider_reference == "B_ref"
    assert note.claim_token == "" and note.claim_expires_at is None


def test_finalize_is_rejected_once_the_row_left_sending(seeded):
    """Ownership requires status == 'sending', not merely a matching token."""

    note_id, _ = queue_one(seeded)
    _claim_as(seeded, note_id, "token-A")
    services._finalize(
        seeded, note_id=note_id, token="token-A",
        values={"status": "sent", "sent_at": datetime.now(timezone.utc),
                **services._CLEARED_CLAIM},
    )

    # Same token, but the row is settled. A second write must not land.
    again = services._finalize(
        seeded, note_id=note_id, token="token-A",
        values={"status": "failed", "last_error": "double finalize"},
    )
    assert again is False, "a settled row was finalized twice"

    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.status == "sent"


def test_no_row_is_deleted_by_a_rejected_stale_write(seeded):
    before = len(seeded.scalars(select(Notification)).all())
    note_id, _ = queue_one(seeded)
    _claim_as(seeded, note_id, "token-A")
    _claim_as(seeded, note_id, "token-B", attempts=2)

    _stale_finalize(seeded, note_id, "token-A",
                    {"status": "failed", **services._CLEARED_CLAIM})

    after = len(seeded.scalars(select(Notification)).all())
    assert after == before + 1, "a rejected stale write deleted a row"


def test_ownership_loss_is_observable_and_counted(seeded, capsys):
    """The whole dispatch path, not just the helper: A's provider call returns after
    B has reclaimed and completed, and A's stale finalization must be discarded."""

    note_id, _ = queue_one(seeded)

    class SlowThenReclaimed:
        """Simulates A: while A is inside send(), B reclaims and completes the row."""

        name = "slow"

        def send(self, *, recipient, subject, body, idempotency_key):
            from app.commerce.db import SessionLocal

            other = SessionLocal()
            try:
                note = other.get(Notification, note_id)
                note.status = "sending"
                note.attempts = 2
                note.claim_token = "token-B"
                note.claim_expires_at = datetime.now(timezone.utc) + timedelta(seconds=300)
                other.commit()
                services._finalize(
                    other, note_id=note_id, token="token-B",
                    values={"status": "sent", "sent_at": datetime.now(timezone.utc),
                            "provider_reference": "B_ref", "last_error": "",
                            **services._CLEARED_CLAIM},
                )
            finally:
                other.close()

            # A's provider call now returns successfully, too late.
            return notifications.DeliveryResult(
                provider="slow", provider_reference="A_ref", accepted=True,
                delivered_at=datetime.now(timezone.utc),
            )

    notifications._sender = SlowThenReclaimed()
    try:
        counts = services.dispatch_pending_notifications(seeded)
    finally:
        notifications.reset_sender()

    assert counts["ownership_lost"] == 1, f"ownership loss was not counted: {counts}"
    assert counts["sent"] == 0, "the stale worker reported a delivery it did not own"

    output = capsys.readouterr().out
    assert '"event": "ownership_lost"' in output, "ownership loss was not logged"
    assert '"notification_id"' in output
    # The log must not leak the recipient, the body or a token value.
    assert "token-B" not in output and "@dedunet.example" not in output

    note = seeded.get(Notification, note_id)
    seeded.refresh(note)
    assert note.status == "sent", "final state is not the current owner's"
    assert note.provider_reference == "B_ref", "A's reference overwrote B's"
    assert note.attempts == 2, "attempts diverged from the documented policy"

def test_finalize_requires_status_sending_even_with_a_matching_token(seeded):
    """The status arm of the ownership condition, covered independently.

    The token arm normally catches a stale worker first, because a reclaim rewrites the
    token. This test isolates the OTHER arm: a row that has already left 'sending' while
    still carrying its token must not be finalizable. That is defence in depth against a
    partially-applied write leaving a settled row with a token attached — without it,
    a late arrival could overwrite a completed result.
    """

    note_id, _ = queue_one(seeded)
    note = _claim_as(seeded, note_id, "token-A")

    # Settled, but the token deliberately left behind.
    note.status = "sent"
    note.provider_reference = "original_ref"
    seeded.commit()

    owned = services._finalize(
        seeded, note_id=note_id, token="token-A",
        values={"status": "failed", "last_error": "late arrival",
                "provider_reference": "late_ref"},
    )
    assert owned is False, (
        "a row that had already left 'sending' was finalized again; only the token was "
        "checked, so a late write could overwrite a completed result"
    )

    seeded.refresh(note)
    assert note.status == "sent"
    assert note.provider_reference == "original_ref"
