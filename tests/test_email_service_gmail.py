import smtplib
import pytest
from app.services.email_service import (
    build_gmail_message, send_mail_gmail, send_test_mail_gmail,
    open_gmail_connection, sanitize_smtp_error,
)


class _FakeSMTP:
    def __init__(self):
        self.logged_in = None
        self.sent_messages = []
        self.quit_called = False

    def login(self, address, password):
        self.logged_in = (address, password)

    def send_message(self, msg):
        self.sent_messages.append(msg)

    def quit(self):
        self.quit_called = True


def test_build_gmail_message_sets_headers_and_body():
    msg = build_gmail_message(
        "sender@gmail.com", "to@example.com", "件名", "本文", [])
    assert msg["To"] == "to@example.com"
    assert msg["Subject"] == "件名"
    assert "sender@gmail.com" in msg["From"]
    assert msg.get_content().strip() == "本文"


def test_build_gmail_message_sets_cc_and_bcc():
    msg = build_gmail_message(
        "sender@gmail.com", "to@example.com", "件名", "本文", [],
        cc_addresses=["cc@example.com"], bcc_addresses=["bcc@example.com"])
    assert msg["Cc"] == "cc@example.com"
    assert msg["Bcc"] == "bcc@example.com"


def test_build_gmail_message_missing_attachment_raises(tmp_path):
    missing = str(tmp_path / "missing.pdf")
    with pytest.raises(FileNotFoundError):
        build_gmail_message("sender@gmail.com", "to@example.com", "件名",
                            "本文", [missing])


def test_build_gmail_message_with_attachment(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello", encoding="utf-8")
    msg = build_gmail_message(
        "sender@gmail.com", "to@example.com", "件名", "本文", [str(f)])
    attachments = list(msg.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "test.txt"


def test_send_mail_gmail_uses_provided_connection_without_login(monkeypatch):
    fake = _FakeSMTP()

    def fail_open(gmail_config):
        raise AssertionError("connection指定時は新規接続してはいけない")

    monkeypatch.setattr("app.services.email_service.open_gmail_connection", fail_open)

    send_mail_gmail({"address": "sender@gmail.com"}, "to@example.com",
                    "件名", "本文", connection=fake)

    assert len(fake.sent_messages) == 1
    assert fake.quit_called is False


def test_send_mail_gmail_opens_and_closes_connection_when_not_provided(monkeypatch):
    fake = _FakeSMTP()
    monkeypatch.setattr(
        "app.services.email_service.open_gmail_connection", lambda cfg: fake)

    send_mail_gmail({"address": "sender@gmail.com"}, "to@example.com",
                    "件名", "本文")

    assert len(fake.sent_messages) == 1
    assert fake.quit_called is True


def test_send_mail_gmail_wraps_smtp_exception(monkeypatch):
    class _RaisingSMTP(_FakeSMTP):
        def send_message(self, msg):
            raise smtplib.SMTPRecipientsRefused({"to@example.com": (550, b"no")})

    fake = _RaisingSMTP()
    monkeypatch.setattr(
        "app.services.email_service.open_gmail_connection", lambda cfg: fake)

    with pytest.raises(RuntimeError):
        send_mail_gmail({"address": "sender@gmail.com"}, "to@example.com",
                        "件名", "本文")
    assert fake.quit_called is True


def test_send_test_mail_gmail_requires_test_address():
    with pytest.raises(ValueError, match="テスト送信先"):
        send_test_mail_gmail({"address": "sender@gmail.com"}, "件名", "本文")


def test_open_gmail_connection_requires_address_and_password():
    with pytest.raises(ValueError):
        open_gmail_connection({})
    with pytest.raises(ValueError):
        open_gmail_connection({"address": "sender@gmail.com"})


def test_sanitize_smtp_error_does_not_expose_credentials():
    error = smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
    result = sanitize_smtp_error(error)
    assert "5.7.8" not in result
    assert "Gmail" in result
