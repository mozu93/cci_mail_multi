from app.ui.send_tab import _SendWorker


class _FakeSession:
    def close(self):
        pass


class _FakeConnection:
    def __init__(self):
        self.quit_called = False

    def quit(self):
        self.quit_called = True


def test_gmail_provider_sends_via_send_mail_gmail_with_shared_connection(monkeypatch):
    received = []

    def fake_send_mail_gmail(gmail_config, to_addr, subject, body, attachments,
                             connection=None):
        received.append((to_addr, connection))

    def fail_send_mail(*a, **k):
        raise AssertionError("gmailプロバイダではsend_mail(Graph)を呼んではいけない")

    monkeypatch.setattr("app.ui.send_tab.send_mail_gmail", fake_send_mail_gmail)
    monkeypatch.setattr("app.ui.send_tab.send_mail", fail_send_mail)
    monkeypatch.setattr("app.ui.send_tab.add_log", lambda *a, **k: None)
    monkeypatch.setattr("app.ui.send_tab.get_session", lambda: _FakeSession())
    monkeypatch.setattr("app.ui.send_tab.time.sleep", lambda s: None)

    connection = _FakeConnection()
    targets = [{"to_address": "a@example.com", "subject": "s", "body": "b",
                "org_name": "org", "member_id": 1, "attachments": []}]
    worker = _SendWorker(targets, {"address": "sender@gmail.com"}, job_id=1,
                         provider="gmail", gmail_connection=connection)
    worker.run()

    assert received == [("a@example.com", connection)]
    assert connection.quit_called is True


def test_default_provider_still_uses_graph_send_mail(monkeypatch):
    received = {}

    def fake_send_mail(graph_config, to_addr, subject, body, attachments,
                       access_token=None):
        received["access_token"] = access_token

    def fail_send_mail_gmail(*a, **k):
        raise AssertionError("既定のプロバイダでGmail送信を呼んではいけない")

    monkeypatch.setattr("app.ui.send_tab.send_mail", fake_send_mail)
    monkeypatch.setattr("app.ui.send_tab.send_mail_gmail", fail_send_mail_gmail)
    monkeypatch.setattr("app.ui.send_tab.add_log", lambda *a, **k: None)
    monkeypatch.setattr("app.ui.send_tab.get_session", lambda: _FakeSession())
    monkeypatch.setattr("app.ui.send_tab.time.sleep", lambda s: None)

    targets = [{"to_address": "a@example.com", "subject": "s", "body": "b",
                "org_name": "org", "member_id": 1, "attachments": []}]
    worker = _SendWorker(targets, {}, job_id=1, access_token="token")
    worker.run()

    assert received["access_token"] == "token"
