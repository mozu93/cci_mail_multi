from app.ui.settings_tab import _GmailSettingsWidget


def test_test_mode_toggle_is_saved_immediately(qtbot, monkeypatch):
    config = {
        "gmail": {
            "address": "sender@gmail.com",
            "app_password": "abcd efgh ijkl mnop",
            "test_address": "tester@example.com",
            "test_mode": False,
        }
    }
    saved = []
    monkeypatch.setattr("app.ui.settings_tab.get_config", lambda: config)
    monkeypatch.setattr(
        "app.ui.settings_tab.save_config",
        lambda value: saved.append(value["gmail"].copy()),
    )

    widget = _GmailSettingsWidget()
    qtbot.addWidget(widget)
    widget._test_mode.setChecked(True)

    assert saved[-1]["test_mode"] is True
    assert saved[-1]["test_address"] == "tester@example.com"


def test_test_mode_cannot_enable_without_valid_test_address(qtbot, monkeypatch):
    config = {"gmail": {"address": "sender@gmail.com", "test_address": "",
                        "test_mode": False}}
    saved = []
    monkeypatch.setattr("app.ui.settings_tab.get_config", lambda: config)
    monkeypatch.setattr(
        "app.ui.settings_tab.save_config", lambda value: saved.append(value))
    monkeypatch.setattr(
        "app.ui.settings_tab.QMessageBox.warning", lambda *args: None)

    widget = _GmailSettingsWidget()
    qtbot.addWidget(widget)
    widget._test_mode.setChecked(True)

    assert widget._test_mode.isChecked() is False
    assert saved == []


def test_save_rejects_invalid_gmail_address(qtbot, monkeypatch):
    config = {"gmail": {}}
    saved = []
    monkeypatch.setattr("app.ui.settings_tab.get_config", lambda: config)
    monkeypatch.setattr(
        "app.ui.settings_tab.save_config", lambda value: saved.append(value))
    monkeypatch.setattr(
        "app.ui.settings_tab.QMessageBox.warning", lambda *args: None)

    widget = _GmailSettingsWidget()
    qtbot.addWidget(widget)
    widget._address.setText("not-an-email")

    assert widget._save() is False
    assert saved == []


def test_save_persists_address_and_app_password(qtbot, monkeypatch):
    config = {"gmail": {}}
    saved = []
    monkeypatch.setattr("app.ui.settings_tab.get_config", lambda: config)
    monkeypatch.setattr(
        "app.ui.settings_tab.save_config",
        lambda value: saved.append(value["gmail"].copy()),
    )

    widget = _GmailSettingsWidget()
    qtbot.addWidget(widget)
    widget._address.setText("sender@gmail.com")
    widget._app_password.setText("abcd efgh ijkl mnop")

    assert widget._save() is True
    assert saved[-1]["address"] == "sender@gmail.com"
    assert saved[-1]["app_password"] == "abcd efgh ijkl mnop"
