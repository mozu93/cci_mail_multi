# app/ui/dialogs/profile_select_dialog.py
"""起動する会（部会）を選ぶダイアログ

前回起動した会が既定で選択される。
通常の起動ではこの画面を出さずに前回の会をそのまま開き、
会を切り替えたいときだけ表示する。
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QCheckBox, QApplication,
)
from PyQt6.QtCore import Qt

from app.utils import profile_config as pc
from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog


class ProfileSelectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("会の選択")
        self.setMinimumSize(460, 380)
        self._profile: dict | None = None
        self._build()
        self._load()
        self._center_on_screen()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("担当する会を選択してください。"))

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(lambda _item: self._open())
        self._list.currentItemChanged.connect(self._update_buttons)
        layout.addWidget(self._list)

        self._empty_hint = QLabel(
            "会がまだ登録されていません。\n"
            "「会を追加」から、担当する会とデータベース接続先を登録してください。")
        self._empty_hint.setWordWrap(True)
        self._empty_hint.setStyleSheet("color: #c0392b;")
        layout.addWidget(self._empty_hint)

        edit_row = QHBoxLayout()
        self._btn_add = QPushButton("会を追加")
        self._btn_add.clicked.connect(self._add)
        self._btn_edit = QPushButton("設定を編集")
        self._btn_edit.clicked.connect(self._edit)
        self._btn_delete = QPushButton("登録を削除")
        self._btn_delete.clicked.connect(self._delete)
        edit_row.addWidget(self._btn_add)
        edit_row.addWidget(self._btn_edit)
        edit_row.addWidget(self._btn_delete)
        edit_row.addStretch()
        layout.addLayout(edit_row)

        self._chk_always = QCheckBox("起動時にこの画面を表示する")
        self._chk_always.setChecked(pc.get_show_selector_on_startup())
        self._chk_always.toggled.connect(pc.set_show_selector_on_startup)
        layout.addWidget(self._chk_always)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("終了")
        btn_cancel.clicked.connect(self.reject)
        self._btn_open = QPushButton("この会を開く")
        self._btn_open.setDefault(True)
        self._btn_open.clicked.connect(self._open)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self._btn_open)
        layout.addLayout(btn_row)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - self.width() // 2,
                  screen.center().y() - self.height() // 2)

    # ------------------------------------------------------------ 一覧表示

    @staticmethod
    def _describe(profile: dict) -> str:
        if profile.get("db_type") == "postgresql":
            pg = profile.get("postgresql") or {}
            host = pg.get("host", "")
            database = pg.get("database", "")
            return f"PostgreSQL：{host}/{database}"
        return f"SQLite：{profile.get('db_path', '')}"

    def _load(self, select_id: str = ""):
        profiles = pc.list_profiles()
        target_id = select_id or pc.get_last_profile_id()

        self._list.clear()
        selected_row = 0
        for i, profile in enumerate(profiles):
            item = QListWidgetItem(
                f"{profile.get('name', '')}\n    {self._describe(profile)}")
            item.setData(Qt.ItemDataRole.UserRole, profile.get("id", ""))
            self._list.addItem(item)
            if profile.get("id") == target_id:
                selected_row = i
        if profiles:
            self._list.setCurrentRow(selected_row)

        self._empty_hint.setVisible(not profiles)
        self._update_buttons()

    def _update_buttons(self, *_args):
        has_selection = self._selected_id() != ""
        self._btn_open.setEnabled(has_selection)
        self._btn_edit.setEnabled(has_selection)
        self._btn_delete.setEnabled(has_selection)

    def _selected_id(self) -> str:
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else ""

    # ------------------------------------------------------------ 操作

    def _add(self):
        dlg = ProfileEditDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        profile = dlg.profile()
        self._load(select_id=profile["id"] if profile else "")

    def _edit(self):
        profile_id = self._selected_id()
        if not profile_id:
            return
        dlg = ProfileEditDialog(self, profile_id=profile_id)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._load(select_id=profile_id)

    def _delete(self):
        profile_id = self._selected_id()
        profile = pc.get_profile(profile_id)
        if profile is None:
            return
        answer = QMessageBox.question(
            self, "登録の削除",
            f"「{profile.get('name', '')}」の登録を削除しますか？\n\n"
            "※ データベースの中身は削除されません。"
            "再度登録すれば同じデータを開けます。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        pc.delete_profile(profile_id)
        self._load()

    def _open(self):
        profile_id = self._selected_id()
        profile = pc.get_profile(profile_id)
        if profile is None:
            QMessageBox.warning(self, "未選択", "会を選択してください。")
            return
        self._profile = profile
        self.accept()

    def profile(self) -> dict | None:
        """選択された会（キャンセル時は None）"""
        return self._profile
