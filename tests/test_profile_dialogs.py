from PyQt6.QtWidgets import QDialog, QMessageBox

from app.utils import profile_config as pc


def _silence_message_boxes(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "critical",
                        staticmethod(lambda *a, **k: None))


# ------------------------------------------------------- ProfileEditDialog

def test_edit_dialog_defaults_to_postgresql(qtbot):
    from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog
    dlg = ProfileEditDialog()
    qtbot.addWidget(dlg)
    assert dlg._db_type.currentIndex() == 0


def test_edit_dialog_fills_sqlite_path_from_name(qtbot):
    from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog
    dlg = ProfileEditDialog()
    qtbot.addWidget(dlg)
    dlg._db_type.setCurrentIndex(1)  # SQLite
    dlg._name.setText("女性部")
    assert dlg._db_path.text().endswith("女性部.db")


def test_edit_dialog_registers_new_profile(qtbot, monkeypatch):
    _silence_message_boxes(monkeypatch)
    from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog
    dlg = ProfileEditDialog()
    qtbot.addWidget(dlg)
    dlg._db_type.setCurrentIndex(1)  # SQLite（接続不要）
    dlg._name.setText("女性部")

    dlg._save()

    assert dlg.result() == QDialog.DialogCode.Accepted
    assert [p["name"] for p in pc.list_profiles()] == ["女性部"]
    assert dlg.profile()["db_type"] == "sqlite"


def test_edit_dialog_requires_name(qtbot, monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: warnings.append(a)))
    from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog
    dlg = ProfileEditDialog()
    qtbot.addWidget(dlg)
    dlg._db_type.setCurrentIndex(1)

    dlg._save()

    assert warnings, "会の名称が未入力なら警告すること"
    assert pc.list_profiles() == []


def test_edit_dialog_rejects_duplicate_name(qtbot, monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: warnings.append(a)))
    pc.add_profile("女性部")

    from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog
    dlg = ProfileEditDialog()
    qtbot.addWidget(dlg)
    dlg._db_type.setCurrentIndex(1)
    dlg._name.setText("女性部")

    dlg._save()

    assert warnings
    assert len(pc.list_profiles()) == 1


def test_edit_dialog_loads_existing_profile(qtbot):
    profile = pc.add_profile("女性部", db_type="sqlite", db_path="C:/data/josei.db")
    from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog
    dlg = ProfileEditDialog(profile_id=profile["id"])
    qtbot.addWidget(dlg)

    assert dlg._name.text() == "女性部"
    assert dlg._db_type.currentIndex() == 1  # SQLite
    assert dlg._db_path.text() == "C:/data/josei.db"


def test_edit_dialog_updates_existing_profile(qtbot, monkeypatch):
    _silence_message_boxes(monkeypatch)
    profile = pc.add_profile("女性部", db_type="sqlite", db_path="C:/data/josei.db")

    from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog
    dlg = ProfileEditDialog(profile_id=profile["id"])
    qtbot.addWidget(dlg)
    dlg._name.setText("女性会")
    dlg._db_path.setText("D:/data/josei.db")

    dlg._save()

    stored = pc.get_profile(profile["id"])
    assert stored["name"] == "女性会"
    assert stored["db_path"] == "D:/data/josei.db"
    assert len(pc.list_profiles()) == 1


def test_edit_dialog_can_inherit_settings_from_other_profile(qtbot, monkeypatch):
    _silence_message_boxes(monkeypatch)
    from app.utils.app_config import get_config, save_config
    josei = pc.add_profile("女性部")
    pc.set_active_profile_id(josei["id"])
    save_config({"graph": {"client_id": "shared-client"}})
    pc.set_active_profile_id("")

    from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog
    dlg = ProfileEditDialog()
    qtbot.addWidget(dlg)
    dlg._db_type.setCurrentIndex(1)
    dlg._name.setText("青年部")
    dlg._inherit.setCurrentIndex(dlg._inherit.findData(josei["id"]))

    dlg._save()

    pc.set_active_profile_id(dlg.profile()["id"])
    assert get_config()["graph"]["client_id"] == "shared-client"


# ----------------------------------------------------- ProfileSelectDialog

def test_select_dialog_lists_registered_profiles(qtbot):
    pc.add_profile("女性部")
    pc.add_profile("青年部")

    from app.ui.dialogs.profile_select_dialog import ProfileSelectDialog
    dlg = ProfileSelectDialog()
    qtbot.addWidget(dlg)

    labels = [dlg._list.item(i).text() for i in range(dlg._list.count())]
    assert any("女性部" in text for text in labels)
    assert any("青年部" in text for text in labels)


def test_select_dialog_preselects_last_profile(qtbot):
    pc.add_profile("女性部")
    seinen = pc.add_profile("青年部")
    pc.set_last_profile_id(seinen["id"])

    from app.ui.dialogs.profile_select_dialog import ProfileSelectDialog
    dlg = ProfileSelectDialog()
    qtbot.addWidget(dlg)

    assert dlg._selected_id() == seinen["id"]


def test_select_dialog_open_returns_selected_profile(qtbot):
    josei = pc.add_profile("女性部")
    pc.set_last_profile_id(josei["id"])

    from app.ui.dialogs.profile_select_dialog import ProfileSelectDialog
    dlg = ProfileSelectDialog()
    qtbot.addWidget(dlg)
    dlg._open()

    assert dlg.result() == QDialog.DialogCode.Accepted
    assert dlg.profile()["id"] == josei["id"]


def test_select_dialog_shows_hint_when_no_profiles(qtbot):
    from app.ui.dialogs.profile_select_dialog import ProfileSelectDialog
    dlg = ProfileSelectDialog()
    qtbot.addWidget(dlg)

    assert dlg._empty_hint.isVisibleTo(dlg)
    assert dlg._btn_open.isEnabled() is False


def test_select_dialog_delete_removes_registration(qtbot, monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    josei = pc.add_profile("女性部")
    pc.add_profile("青年部")

    from app.ui.dialogs.profile_select_dialog import ProfileSelectDialog
    dlg = ProfileSelectDialog()
    qtbot.addWidget(dlg)
    dlg._load(select_id=josei["id"])
    dlg._delete()

    assert [p["name"] for p in pc.list_profiles()] == ["青年部"]


def test_select_dialog_startup_checkbox_persists(qtbot):
    pc.add_profile("女性部")
    from app.ui.dialogs.profile_select_dialog import ProfileSelectDialog
    dlg = ProfileSelectDialog()
    qtbot.addWidget(dlg)

    assert dlg._chk_always.isChecked() is False
    dlg._chk_always.setChecked(True)
    assert pc.get_show_selector_on_startup() is True
