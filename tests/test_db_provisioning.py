import pytest
from PyQt6.QtWidgets import QMessageBox

from app.database import provisioning
from app.ui.widgets import db_provision


_PG = {"host": "192.168.10.222", "port": "5432", "database": "jyosei",
       "user": "postgres", "password": "secret"}


# ------------------------------------------------------- データベース名の検証

@pytest.mark.parametrize("name", ["cci_mail_josei", "jyosei", "女性部"])
def test_valid_database_names_are_accepted(name):
    assert provisioning.validate_database_name(name) == ""


def test_empty_database_name_is_rejected():
    assert "入力してください" in provisioning.validate_database_name("   ")


def test_database_name_with_double_quote_is_rejected():
    assert provisioning.validate_database_name('bad"name') != ""


def test_too_long_database_name_is_rejected():
    assert "長すぎます" in provisioning.validate_database_name("a" * 64)


def test_identifier_quoting_escapes_double_quotes():
    """引用符の二重化により、識別子経由のSQL注入を防ぐこと"""
    assert provisioning._quote_identifier('a"b') == '"a""b"'
    assert provisioning._quote_identifier("cci_mail") == '"cci_mail"'


# --------------------------------------------------- CREATE DATABASE の実行

class _FakeResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _FakeConn:
    def __init__(self, engine):
        self._engine = engine

    def execute(self, statement, params=None):
        sql = str(statement)
        self._engine.executed.append((sql, params))
        if "pg_database" in sql:
            name = params["name"]
            return _FakeResult((1,) if name in self._engine.existing else None)
        return _FakeResult(None)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _FakeEngine:
    def __init__(self, existing=()):
        self.existing = set(existing)
        self.executed = []
        self.disposed = False

    def connect(self):
        return _FakeConn(self)

    def dispose(self):
        self.disposed = True


def _patch_engine(monkeypatch, engine):
    monkeypatch.setattr(provisioning, "_maintenance_engine", lambda pg: engine)
    return engine


def test_create_database_issues_create_statement(monkeypatch):
    engine = _patch_engine(monkeypatch, _FakeEngine())

    provisioning.create_database(_PG, "jyosei")

    creates = [sql for sql, _ in engine.executed if sql.startswith("CREATE DATABASE")]
    assert creates == ['CREATE DATABASE "jyosei"']
    assert engine.disposed


def test_create_database_skips_when_already_present(monkeypatch):
    engine = _patch_engine(monkeypatch, _FakeEngine(existing=["jyosei"]))

    provisioning.create_database(_PG, "jyosei")

    assert not [sql for sql, _ in engine.executed if sql.startswith("CREATE DATABASE")]


def test_create_database_rejects_invalid_name(monkeypatch):
    engine = _patch_engine(monkeypatch, _FakeEngine())

    with pytest.raises(ValueError):
        provisioning.create_database(_PG, 'bad"name')

    assert engine.executed == []


def test_database_exists_reflects_server_state(monkeypatch):
    _patch_engine(monkeypatch, _FakeEngine(existing=["jyosei"]))
    assert provisioning.database_exists(_PG, "jyosei") is True

    _patch_engine(monkeypatch, _FakeEngine())
    assert provisioning.database_exists(_PG, "jyosei") is False


# --------------------------------------------------------------- UI 側の流れ

def _answers(monkeypatch, question=QMessageBox.StandardButton.Yes):
    shown = {"info": [], "warn": [], "error": []}
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: question))
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: shown["info"].append(a)))
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: shown["warn"].append(a)))
    monkeypatch.setattr(QMessageBox, "critical",
                        staticmethod(lambda *a, **k: shown["error"].append(a)))
    return shown


def test_interactive_create_asks_then_creates(monkeypatch):
    shown = _answers(monkeypatch)
    created = []
    monkeypatch.setattr(db_provision, "database_exists", lambda pg, db: False)
    monkeypatch.setattr(db_provision, "create_database",
                        lambda pg, db: created.append(db))

    assert db_provision.create_database_interactive(None, _PG) is True
    assert created == ["jyosei"]
    assert shown["info"], "作成完了を知らせること"


def test_interactive_create_aborts_when_declined(monkeypatch):
    _answers(monkeypatch, question=QMessageBox.StandardButton.No)
    created = []
    monkeypatch.setattr(db_provision, "database_exists", lambda pg, db: False)
    monkeypatch.setattr(db_provision, "create_database",
                        lambda pg, db: created.append(db))

    assert db_provision.create_database_interactive(None, _PG) is False
    assert created == []


def test_interactive_create_reports_existing_database(monkeypatch):
    shown = _answers(monkeypatch)
    created = []
    monkeypatch.setattr(db_provision, "database_exists", lambda pg, db: True)
    monkeypatch.setattr(db_provision, "create_database",
                        lambda pg, db: created.append(db))

    assert db_provision.create_database_interactive(None, _PG) is True
    assert created == [], "既存の場合は作成しないこと"


def test_interactive_create_validates_inputs_first(monkeypatch):
    shown = _answers(monkeypatch)
    monkeypatch.setattr(db_provision, "database_exists",
                        lambda pg, db: pytest.fail("接続を試みないこと"))

    bad = {**_PG, "database": "  "}
    assert db_provision.create_database_interactive(None, bad) is False
    assert shown["warn"]


def test_interactive_create_explains_permission_failure(monkeypatch):
    shown = _answers(monkeypatch)
    monkeypatch.setattr(db_provision, "database_exists", lambda pg, db: False)

    def _fail(pg, db):
        raise RuntimeError("permission denied to create database")

    monkeypatch.setattr(db_provision, "create_database", _fail)

    assert db_provision.create_database_interactive(None, _PG) is False
    assert shown["error"], "失敗を知らせること"


def test_offer_to_create_declined_does_not_create(monkeypatch):
    _answers(monkeypatch, question=QMessageBox.StandardButton.No)
    monkeypatch.setattr(db_provision, "database_exists",
                        lambda pg, db: pytest.fail("接続を試みないこと"))

    assert db_provision.offer_to_create_database(None, _PG) is False


# ------------------------------------------------- 会の登録ダイアログとの連携

def test_edit_dialog_hides_create_button_for_sqlite(qtbot):
    from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog
    dlg = ProfileEditDialog()
    qtbot.addWidget(dlg)
    dlg.show()

    dlg._db_type.setCurrentIndex(0)  # PostgreSQL
    assert dlg._btn_create_db.isVisibleTo(dlg)

    dlg._db_type.setCurrentIndex(1)  # SQLite
    assert not dlg._btn_create_db.isVisibleTo(dlg)


def test_edit_dialog_offers_creation_when_database_missing(qtbot, monkeypatch):
    """接続テストでDB未作成が判明したら、作成を促すこと"""
    from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog
    dlg = ProfileEditDialog()
    qtbot.addWidget(dlg)
    dlg._db_type.setCurrentIndex(0)
    dlg._name.setText("女性部")
    dlg._database.setText("jyosei")

    missing = RuntimeError('FATAL:  database "jyosei" does not exist')
    attempts = []

    def _connect():
        attempts.append(1)
        return False, "接続失敗", missing

    monkeypatch.setattr(dlg, "_try_connect", _connect)
    offered = []
    monkeypatch.setattr(
        "app.ui.widgets.db_provision.offer_to_create_database",
        lambda parent, pg: offered.append(pg) or False)

    dlg._test_connection()

    assert offered, "データベース作成を提案すること"
    assert offered[0]["database"] == "jyosei"


def test_edit_dialog_does_not_offer_creation_for_other_errors(qtbot, monkeypatch):
    from app.ui.dialogs.profile_edit_dialog import ProfileEditDialog
    shown = _answers(monkeypatch)
    dlg = ProfileEditDialog()
    qtbot.addWidget(dlg)
    dlg._db_type.setCurrentIndex(0)

    wrong_password = RuntimeError("FATAL:  password authentication failed")
    monkeypatch.setattr(
        dlg, "_try_connect", lambda: (False, "認証失敗", wrong_password))
    monkeypatch.setattr(
        "app.ui.widgets.db_provision.offer_to_create_database",
        lambda parent, pg: pytest.fail("作成を提案しないこと"))

    dlg._test_connection()

    assert shown["error"], "通常のエラーとして表示すること"
