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


def queue_one(session, *, email="notify@meret.example", subject="Your order FC-TEST"):
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
    assert second == {"sent": 0, "failed": 0, "retried": 0, "suppressed": 0, "claimed": 0}

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
    monkeypatch.setenv("SMTP_FROM", "noreply@meret.example")
    monkeypatch.setenv("SMTP_USE_TLS", "0")   # the fake server speaks plain SMTP
    notifications.reset_sender()

    note_id, _ = queue_one(seeded, email="smtp-target@meret.example")
    counts = services.dispatch_pending_notifications(seeded)

    assert counts["sent"] == 1, "SMTP send did not succeed against the fake server"

    # The client genuinely connected and completed an exchange.
    assert fake_smtp.mail_from, "no MAIL FROM was received; no real connection was made"
    assert "noreply@meret.example" in fake_smtp.mail_from[0]
    assert fake_smtp.rcpt_to, "no RCPT TO was received"
    assert "smtp-target@meret.example" in fake_smtp.rcpt_to[0]

    assert len(fake_smtp.messages) == 1
    message = fake_smtp.messages[0]
    assert "Subject: Your order FC-TEST" in message
    assert "To: smtp-target@meret.example" in message
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
    monkeypatch.setenv("SMTP_FROM", "noreply@meret.example")
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
    monkeypatch.setenv("SMTP_FROM", "noreply@meret.example")
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
    monkeypatch.setenv("SMTP_FROM", "noreply@meret.example")
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
        queue_one(seeded, email=f"keep{i}@meret.example", subject=f"s{i}")
    before = seeded.scalar(select(Notification).order_by(Notification.id))
    total_before = len(seeded.scalars(select(Notification)).all())

    services.dispatch_pending_notifications(seeded)          # console: all sent

    monkeypatch.setenv("NOTIFICATION_CHANNEL", "smtp")
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", str(rejecting_smtp.port))
    monkeypatch.setenv("SMTP_FROM", "noreply@meret.example")
    monkeypatch.setenv("SMTP_USE_TLS", "0")
    notifications.reset_sender()
    queue_one(seeded, email="rejected@meret.example")
    services.dispatch_pending_notifications(seeded)          # terminal rejection

    total_after = len(seeded.scalars(select(Notification)).all())
    assert total_after == total_before + 1, "a notification row was deleted"
    assert before is not None


# --------------------------------------------------------------- erasure protection


def test_erased_customer_is_never_emailed(seeded):
    """Erasure must not be undone by a queued notification."""

    note_id, customer_id = queue_one(seeded, email="tobe-erased@meret.example")

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
        queue_one(seeded, email=f"race{i}@meret.example", subject=f"race-{i}")

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
