# app/database/provisioning.py
"""PostgreSQLのデータベースを作成するユーティリティ。

会を追加するたびに、その会用のデータベースをサーバー側で作成する必要がある。
pgAdminを開かずにアプリから作成できるよう、管理用データベース（postgres）へ
接続して CREATE DATABASE を実行する。

エンコーディングやロケールは指定せず、サーバーの既定（template1）に従う。
pgAdminの「Create Database」を既定設定で実行した場合と同じ結果になる。
"""
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL as SaURL

# 対象のデータベースがまだ無い状態で接続するための、既定で存在するデータベース
_MAINTENANCE_DATABASES = ("postgres", "template1")

_MAX_IDENTIFIER_BYTES = 63


def validate_database_name(name: str) -> str:
    """データベース名として使えない場合に、その理由を返す（問題なければ空文字）"""
    name = (name or "").strip()
    if not name:
        return "データベース名を入力してください。"
    if '"' in name or "\x00" in name:
        return 'データベース名に " や制御文字は使用できません。'
    if len(name.encode("utf-8")) > _MAX_IDENTIFIER_BYTES:
        return f"データベース名が長すぎます（UTF-8で{_MAX_IDENTIFIER_BYTES}バイトまで）。"
    return ""


def _quote_identifier(name: str) -> str:
    """識別子を安全に引用符で囲む（CREATE DATABASE はパラメータ化できないため）"""
    return '"' + name.replace('"', '""') + '"'


def _maintenance_url(pg: dict, database: str) -> SaURL:
    return SaURL.create(
        "postgresql+psycopg2",
        username=pg.get("user", ""),
        password=pg.get("password", ""),
        host=pg.get("host", ""),
        port=int(pg.get("port") or 5432),
        database=database,
    )


def _maintenance_engine(pg: dict):
    """管理用データベースへ接続したエンジンを返す。

    CREATE DATABASE はトランザクション内で実行できないため AUTOCOMMIT にする。
    """
    last_error: Exception | None = None
    for database in _MAINTENANCE_DATABASES:
        engine = create_engine(
            _maintenance_url(pg, database),
            isolation_level="AUTOCOMMIT",
            connect_args={"connect_timeout": 5},
        )
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception as e:
            engine.dispose()
            last_error = e
    raise last_error if last_error else RuntimeError("接続先が特定できません")


def database_exists(pg: dict, database: str) -> bool:
    """指定のデータベースがサーバー上に存在するか確認する"""
    engine = _maintenance_engine(pg)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database},
            ).first()
        return row is not None
    finally:
        engine.dispose()


def create_database(pg: dict, database: str) -> None:
    """データベースを新規作成する（既に存在する場合は何もしない）"""
    error = validate_database_name(database)
    if error:
        raise ValueError(error)
    database = database.strip()

    engine = _maintenance_engine(pg)
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database},
            ).first()
            if exists is not None:
                return
            conn.execute(text(f"CREATE DATABASE {_quote_identifier(database)}"))
    finally:
        engine.dispose()
