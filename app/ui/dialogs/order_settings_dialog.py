from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from sqlalchemy.orm import Session
from app.database.models import Position, Member
from app.utils.terms import order_position_name, save_order_position


class OrderSettingsDialog(QDialog):
    """特定の役職について、就任順（表示順）を手動で並べ替えるダイアログ

    対象の役職は会ごとに異なる（議員の会は「副会頭」、女性部は「副会長」など）ため、
    この画面で選択し、選んだ役職を会の設定として記憶する。

    役職そのものの表示順（sort_order）は設定タブの「役職・委員会管理」に統合済み。
    """

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self._session = session
        self.resize(500, 440)
        self._build()
        self._load_positions()

    # ------------------------------------------------------------ 画面構築

    def _build(self):
        layout = QVBoxLayout(self)

        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("対象の役職"))
        self._pos_combo = QComboBox()
        self._pos_combo.currentIndexChanged.connect(self._on_position_change)
        pos_row.addWidget(self._pos_combo, 1)
        layout.addLayout(pos_row)
        layout.addWidget(QLabel(
            "※ 選んだ役職は、この会の設定として記憶されます。"))

        layout.addWidget(QLabel(
            "就任が古い順（上）→新しい順（下）に並べ替えてください。\n"
            "（ドラッグまたは ↑↓ ボタンで操作）"))
        self._member_list = QListWidget()
        self._member_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        layout.addWidget(self._member_list)
        layout.addLayout(self._arrow_buttons(self._member_list))

        # 保存 / キャンセル
        btns = QHBoxLayout()
        btn_save   = QPushButton("保存")
        btn_cancel = QPushButton("キャンセル")
        btn_save.clicked.connect(self._save)
        btn_cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(btn_save)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

    def _arrow_buttons(self, list_widget: QListWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        btn_up   = QPushButton("↑ 上へ")
        btn_down = QPushButton("↓ 下へ")
        btn_up.clicked.connect(lambda: self._move(list_widget, -1))
        btn_down.clicked.connect(lambda: self._move(list_widget, +1))
        row.addStretch()
        row.addWidget(btn_up)
        row.addWidget(btn_down)
        return row

    @staticmethod
    def _move(lw: QListWidget, delta: int):
        row = lw.currentRow()
        if row < 0:
            return
        new_row = row + delta
        if new_row < 0 or new_row >= lw.count():
            return
        item = lw.takeItem(row)
        lw.insertItem(new_row, item)
        lw.setCurrentRow(new_row)

    # ------------------------------------------------------------ 読み込み

    def _load_positions(self):
        positions = (self._session.query(Position)
                     .order_by(Position.sort_order, Position.id)
                     .all())
        configured = order_position_name()

        self._pos_combo.blockSignals(True)
        self._pos_combo.clear()
        self._pos_combo.addItem("（役職を選択してください）", None)
        selected_index = 0
        for i, p in enumerate(positions, start=1):
            self._pos_combo.addItem(p.name, p.id)
            if p.name == configured:
                selected_index = i
        self._pos_combo.setCurrentIndex(selected_index)
        self._pos_combo.blockSignals(False)

        self._update_title()
        self._load_members()

    def _on_position_change(self, _index: int):
        self._update_title()
        self._load_members()

    def _update_title(self):
        name = self._selected_position_name()
        self.setWindowTitle(f"{name}の就任順設定" if name else "就任順設定")

    def _selected_position_id(self):
        return self._pos_combo.currentData()

    def _selected_position_name(self) -> str:
        return self._pos_combo.currentText() if self._selected_position_id() else ""

    def _load_members(self):
        self._member_list.clear()
        position_id = self._selected_position_id()
        if position_id is None:
            self._member_list.addItem("（対象の役職を選択してください）")
            return

        members = (self._session.query(Member)
                   .filter_by(position_id=position_id, is_active=True)
                   .order_by(Member.display_order.asc().nullslast(),
                             Member.organization_kana)
                   .all())
        if not members:
            self._member_list.addItem("（この役職の会員が登録されていません）")
            return
        for m in members:
            item = QListWidgetItem(f"{m.organization_name}　{m.name}")
            item.setData(Qt.ItemDataRole.UserRole, m.id)
            self._member_list.addItem(item)

    # ------------------------------------------------------------ 保存

    def _save(self):
        if self._selected_position_id() is None:
            QMessageBox.warning(self, "未選択", "対象の役職を選択してください。")
            return

        # 選んだ役職を、この会の設定として記憶する
        save_order_position(self._selected_position_name())

        for i in range(self._member_list.count()):
            item = self._member_list.item(i)
            member_id = item.data(Qt.ItemDataRole.UserRole)
            if member_id is None:
                continue
            m = self._session.get(Member, member_id)
            if m:
                m.display_order = i + 1

        self._session.commit()
        QMessageBox.information(self, "保存完了", "表示順を保存しました。")
        self.accept()
