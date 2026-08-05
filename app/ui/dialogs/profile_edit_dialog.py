# app/ui/dialogs/profile_edit_dialog.py
"""会（部会）の登録・編集ダイアログ

会の名称と、その会が使うデータベースの接続先を設定する。
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QSpinBox, QMessageBox, QFormLayout, QGroupBox, QFileDialog,
)

from app.utils import profile_config as pc

_TYPE_PG = 0
_TYPE_SQLITE = 1


class ProfileEditDialog(QDialog):
    """profile_id を渡すと編集、渡さないと新規登録として動作する。"""

    def __init__(self, parent=None, profile_id: str = ""):
        super().__init__(parent)
        self._profile_id = profile_id
        self._is_new = not profile_id
        self._profile: dict | None = None
        self._db_path_touched = False
        self.setWindowTitle("会の登録" if self._is_new else "会の設定")
        self.setMinimumWidth(520)
        self._build()
        self._load()

    # ------------------------------------------------------------ 画面構築

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel(
            "会（女性部・青年部・議員など）ごとにデータベースを分けて管理します。"))

        name_form = QFormLayout()
        self._name = QLineEdit()
        self._name.setPlaceholderText("例：女性部")
        self._name.textChanged.connect(self._on_name_changed)
        name_form.addRow("会の名称", self._name)

        self._db_type = QComboBox()
        self._db_type.addItems(
            ["PostgreSQL（複数人で共有）", "SQLite（この端末だけで使用）"])
        self._db_type.currentIndexChanged.connect(self._on_type_change)
        name_form.addRow("データベース種別", self._db_type)
        layout.addLayout(name_form)

        # PostgreSQL 接続設定
        self._pg_grp = QGroupBox("PostgreSQL接続設定")
        pg_form = QFormLayout(self._pg_grp)
        self._host = QLineEdit("localhost")
        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(5432)
        self._database = QLineEdit()
        self._database.setPlaceholderText("例：cci_mail_josei")
        self._user = QLineEdit("postgres")
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        pg_form.addRow("ホスト名 / IPアドレス", self._host)
        pg_form.addRow("ポート番号", self._port)
        pg_form.addRow("データベース名", self._database)
        pg_form.addRow("ユーザー名", self._user)
        pg_form.addRow("パスワード", self._password)
        layout.addWidget(self._pg_grp)

        # SQLite 設定
        self._sqlite_grp = QGroupBox("SQLite設定")
        sqlite_layout = QVBoxLayout(self._sqlite_grp)
        path_row = QHBoxLayout()
        self._db_path = QLineEdit()
        self._db_path.textEdited.connect(lambda: self._mark_path_touched())
        btn_browse = QPushButton("参照…")
        btn_browse.clicked.connect(self._browse_db_path)
        path_row.addWidget(QLabel("ファイル"))
        path_row.addWidget(self._db_path)
        path_row.addWidget(btn_browse)
        sqlite_layout.addLayout(path_row)
        sqlite_layout.addWidget(QLabel(
            "※ ファイルが存在しない場合は起動時に新規作成されます。"))
        layout.addWidget(self._sqlite_grp)

        # 設定の引き継ぎ（新規登録時のみ）
        self._inherit = QComboBox()
        if self._is_new:
            others = pc.list_profiles()
            if others:
                inherit_form = QFormLayout()
                self._inherit.addItem("引き継がない", "")
                for p in others:
                    self._inherit.addItem(p.get("name", ""), p.get("id", ""))
                inherit_form.addRow("設定の引き継ぎ元", self._inherit)
                layout.addLayout(inherit_form)
                layout.addWidget(QLabel(
                    "※ Microsoft 365の接続情報などを他の会から引き継ぎます"
                    "（データベースの中身は引き継ぎません）。"))

        btn_row = QHBoxLayout()
        btn_test = QPushButton("接続テスト")
        btn_test.clicked.connect(self._test_connection)
        self._btn_create_db = QPushButton("データベースを作成")
        self._btn_create_db.setToolTip(
            "サーバーにこの会用のデータベースをまだ作成していない場合にクリックします")
        self._btn_create_db.clicked.connect(self._create_database)
        btn_cancel = QPushButton("キャンセル")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("登録" if self._is_new else "保存")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._save)
        btn_row.addWidget(btn_test)
        btn_row.addWidget(self._btn_create_db)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------ 読み込み

    def _load(self):
        if self._is_new:
            self._db_type.setCurrentIndex(_TYPE_PG)
            self._on_type_change(_TYPE_PG)
            return

        profile = pc.get_profile(self._profile_id) or {}
        self._profile = profile
        self._name.setText(profile.get("name", ""))
        self._db_path_touched = True
        self._db_path.setText(profile.get("db_path", ""))

        pg = profile.get("postgresql") or {}
        self._host.setText(pg.get("host", "localhost"))
        self._port.setValue(int(pg.get("port") or 5432))
        self._database.setText(pg.get("database", ""))
        self._user.setText(pg.get("user", "postgres"))
        self._password.setText(pg.get("password", ""))

        index = _TYPE_PG if profile.get("db_type") == "postgresql" else _TYPE_SQLITE
        self._db_type.setCurrentIndex(index)
        self._on_type_change(index)

    def _on_type_change(self, index: int):
        self._pg_grp.setVisible(index == _TYPE_PG)
        self._sqlite_grp.setVisible(index == _TYPE_SQLITE)
        # SQLiteはファイルが自動生成されるため、作成ボタンは不要
        self._btn_create_db.setVisible(index == _TYPE_PG)
        self._sync_default_db_path()
        self.adjustSize()

    def _on_name_changed(self, _text: str):
        self._sync_default_db_path()

    def _mark_path_touched(self):
        self._db_path_touched = True

    def _sync_default_db_path(self):
        """会名からSQLiteファイルの既定パスを自動で埋める（手入力後は触らない）"""
        if self._db_path_touched:
            return
        name = self._name.text().strip()
        self._db_path.setText(pc.default_sqlite_path(name) if name else "")

    def _browse_db_path(self):
        current = self._db_path.text().strip()
        path, _ = QFileDialog.getSaveFileName(
            self, "データベースファイルを選択", current,
            "SQLiteデータベース (*.db);;すべてのファイル (*.*)")
        if path:
            self._db_path.setText(path)
            self._db_path_touched = True

    # ------------------------------------------------------------ 入力内容

    def _pg_values(self) -> dict:
        return {
            "host": self._host.text().strip(),
            "port": str(self._port.value()),
            "database": self._database.text().strip(),
            "user": self._user.text().strip(),
            "password": self._password.text(),
        }

    def _selected_db_type(self) -> str:
        return "postgresql" if self._db_type.currentIndex() == _TYPE_PG else "sqlite"

    def _try_connect(self) -> tuple[bool, str, Exception | None]:
        """PostgreSQLへ接続できるか確認する。SQLiteは常に成功扱い。"""
        if self._selected_db_type() == "sqlite":
            return True, "", None
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.engine import URL as SaURL
            pg = self._pg_values()
            url = SaURL.create(
                "postgresql+psycopg2",
                username=pg["user"], password=pg["password"],
                host=pg["host"], port=int(pg["port"] or 5432),
                database=pg["database"],
            )
            engine = create_engine(url, connect_args={"connect_timeout": 5})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return True, "", None
        except Exception as e:
            from app.utils.db_errors import format_connection_error
            return False, format_connection_error(e), e

    def _test_connection(self):
        if self._selected_db_type() == "sqlite":
            QMessageBox.information(
                self, "接続テスト",
                "SQLiteはローカルファイルのため接続テストは不要です。")
            return
        ok, message, error = self._try_connect()
        if ok:
            QMessageBox.information(self, "接続テスト成功",
                                    "PostgreSQLへの接続に成功しました。")
            return
        # データベース未作成が原因なら、その場で作成できるようにする
        from app.utils.db_errors import is_missing_database_error
        if error is not None and is_missing_database_error(error):
            from app.ui.widgets.db_provision import offer_to_create_database
            if offer_to_create_database(self, self._pg_values()):
                self._test_connection()
            return
        QMessageBox.critical(self, "接続テスト失敗", message)

    def _create_database(self):
        """サーバーにこの会用のデータベースを作成する"""
        from app.ui.widgets.db_provision import create_database_interactive
        create_database_interactive(self, self._pg_values())

    # ------------------------------------------------------------ 保存

    def _validate(self) -> str:
        if not self._name.text().strip():
            return "会の名称を入力してください。"
        if self._selected_db_type() == "postgresql":
            if not self._database.text().strip():
                return "データベース名を入力してください。"
            if not self._host.text().strip():
                return "ホスト名 / IPアドレスを入力してください。"
        elif not self._db_path.text().strip():
            return "データベースファイルのパスを入力してください。"
        return ""

    def _save(self):
        error = self._validate()
        if error:
            QMessageBox.warning(self, "入力エラー", error)
            return

        ok, message, error = self._try_connect()
        if not ok and error is not None:
            # データベース未作成なら、作成を促してから接続をやり直す
            from app.utils.db_errors import is_missing_database_error
            if is_missing_database_error(error):
                from app.ui.widgets.db_provision import offer_to_create_database
                if offer_to_create_database(self, self._pg_values()):
                    ok, message, error = self._try_connect()
        if not ok:
            answer = QMessageBox.question(
                self, "接続できません",
                f"データベースに接続できませんでした。\n\n{message}\n\n"
                "このまま設定を保存しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return

        db_type = self._selected_db_type()
        db_path = self._db_path.text().strip() if db_type == "sqlite" else ""
        try:
            if self._is_new:
                profile = pc.add_profile(
                    self._name.text(), db_type=db_type, db_path=db_path,
                    postgresql=self._pg_values())
                src_id = self._inherit.currentData()
                if src_id:
                    pc.copy_settings_from(src_id, profile["id"])
            else:
                profile = pc.update_profile(
                    self._profile_id, name=self._name.text().strip(),
                    db_type=db_type, db_path=db_path,
                    postgresql=self._pg_values())
        except ValueError as e:
            QMessageBox.warning(self, "登録エラー", str(e))
            return

        self._profile = profile
        self.accept()

    def profile(self) -> dict | None:
        """登録・保存された会（キャンセル時は None）"""
        return self._profile
