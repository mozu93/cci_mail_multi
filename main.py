import sys
import os
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt6.QtGui import QIcon
from app.ui.main_window import MainWindow
from app.ui.dialogs.login_dialog import LoginDialog
from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog
from app.ui.dialogs.profile_select_dialog import ProfileSelectDialog
from app.utils import profile_config as pc


_GLOBAL_STYLE = """
QPushButton {
    background-color: #F0F4F8;
    border: 1px solid #94A3B8;
    border-radius: 4px;
    padding: 4px 10px;
    color: #1E293B;
    min-height: 26px;
}
QPushButton:hover {
    background-color: #DBEAFE;
    border-color: #3B82F6;
    color: #1D4ED8;
}
QPushButton:pressed {
    background-color: #BFDBFE;
    border-color: #2563EB;
}
QPushButton:disabled {
    background-color: #F1F5F9;
    border-color: #CBD5E1;
    color: #94A3B8;
}
QLineEdit, QTextEdit, QComboBox {
    border: 1px solid #CBD5E1;
    border-radius: 3px;
    padding: 3px 6px;
    background-color: #FFFFFF;
    selection-background-color: #BFDBFE;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #3B82F6;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    margin-top: 6px;
    padding-top: 4px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}
"""


def _choose_profile(force_select: bool) -> dict | None:
    """起動する会を決める。前回の会を記憶しており、通常は選択画面を出さない。"""
    if not pc.list_profiles():
        dlg = ProfileEditDialog()
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        return dlg.profile()

    if not force_select and not pc.get_show_selector_on_startup():
        last = pc.get_last_profile()
        if last is not None:
            return last

    dlg = ProfileSelectDialog()
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    return dlg.profile()


def _connect_database(profile: dict) -> bool:
    """接続できるまで設定を促す。会の選択に戻る場合は False を返す。"""
    from app.database.connection import get_engine, reset_engine
    from app.utils.db_errors import format_connection_error
    while True:
        try:
            get_engine()
            return True
        except Exception as e:
            reset_engine()
            QMessageBox.critical(
                None, "DB接続エラー",
                f"「{profile.get('name', '')}」のデータベースに接続できませんでした。"
                f"\n\n{format_connection_error(e)}\n\n設定を確認してください。")
            dlg = ProfileEditDialog(profile_id=profile["id"])
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return False


def _cleanup_old_jobs():
    from app.database.connection import get_session
    from app.services.send_job_service import delete_old_jobs
    session = get_session()
    try:
        delete_old_jobs(session)
    except Exception:
        pass
    finally:
        session.close()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("cci-mail-multi")
    _font = app.font()
    _font.setPointSizeF(10.5)
    app.setFont(_font)
    app.setStyleSheet(_GLOBAL_STYLE)

    _base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    _icon_path = os.path.join(_base, "assets", "icon.png")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))

    from app.database.connection import reset_engine

    # 会の切り替え時は、この画面まで戻ってやり直す
    force_select = "--select-profile" in sys.argv
    while True:
        pc.set_active_profile_id("")
        reset_engine()

        profile = _choose_profile(force_select)
        if profile is None:
            sys.exit(0)

        pc.set_active_profile_id(profile["id"])
        pc.set_last_profile_id(profile["id"])

        if not _connect_database(profile):
            force_select = True
            continue

        dlg = LoginDialog()
        if dlg.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

        _cleanup_old_jobs()

        window = MainWindow(staff_name=dlg.staff_name(), readonly=dlg.readonly())
        window.show()
        app.exec()

        if not window.switch_profile_requested():
            sys.exit(0)
        window.deleteLater()
        del window
        force_select = True


if __name__ == "__main__":
    main()
