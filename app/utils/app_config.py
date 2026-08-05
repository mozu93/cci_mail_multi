import json
from pathlib import Path


def _app_data_dir() -> Path:
    """起動中の会の設定保存ディレクトリ"""
    from app.utils.profile_config import active_profile_dir
    return active_profile_dir()


def _config_path() -> Path:
    return _app_data_dir() / "app_config.json"


def _db_default_path() -> Path:
    """接続先が未指定のときに使うSQLiteファイル（会ごとに独立）"""
    return _app_data_dir() / "cci_mail.db"


def get_config() -> dict:
    p = _config_path()
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    p = _config_path()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_db_path() -> str:
    """起動中の会のSQLiteファイルパス"""
    from app.utils.profile_config import get_active_db_settings
    db_path = get_active_db_settings().get("db_path", "")
    if db_path:
        return db_path
    return str(_db_default_path())


def get_graph_config() -> dict:
    return get_config().get("graph", {})


def get_db_type() -> str:
    """起動中の会のDB種別。'sqlite' または 'postgresql'（既定は 'sqlite'）"""
    from app.utils.profile_config import get_active_db_settings
    return get_active_db_settings().get("db_type", "sqlite")


def get_html_export_path() -> str:
    """HTML出力先ファイルパス（未設定時は空文字）

    PostgreSQLモード（複数台共有）ではDBに保存し、全端末で共有する。
    SQLiteモード（1台用）では従来通り端末ローカルのapp_config.jsonに保存する。
    """
    if get_db_type() == "postgresql":
        return _get_shared_setting("html_export_path", "")
    return get_config().get("html_export_path", "")


def save_html_export_path(path: str) -> None:
    """HTML出力先ファイルパスを保存する（DB種別に応じて保存先を切り替え）"""
    if get_db_type() == "postgresql":
        _set_shared_setting("html_export_path", path)
    else:
        config = get_config()
        config["html_export_path"] = path
        save_config(config)


def _get_shared_setting(key: str, default: str = "") -> str:
    """PostgreSQLモード時、複数端末で共有する設定値をDBから取得する"""
    try:
        from app.database.connection import get_session
        from app.database.models import AppSetting
        session = get_session()
        try:
            row = session.get(AppSetting, key)
            return row.value if row is not None and row.value is not None else default
        finally:
            session.close()
    except Exception:
        return default


def _set_shared_setting(key: str, value: str) -> None:
    """PostgreSQLモード時、複数端末で共有する設定値をDBに保存する"""
    from app.database.connection import get_session
    from app.database.models import AppSetting
    session = get_session()
    try:
        row = session.get(AppSetting, key)
        if row is None:
            session.add(AppSetting(key=key, value=value))
        else:
            row.value = value
        session.commit()
    finally:
        session.close()


def is_first_run() -> bool:
    """起動中の会の設定ファイルが一度も保存されていない状態かどうか"""
    return not _config_path().exists()


def get_pg_config() -> dict:
    """起動中の会のPostgreSQL接続設定を返す"""
    from app.utils.profile_config import get_active_db_settings
    defaults = {
        "host": "localhost",
        "port": "5432",
        "database": "cci_mail",
        "user": "",
        "password": "",
    }
    return {**defaults, **(get_active_db_settings().get("postgresql") or {})}


def get_voting_excluded_org() -> str:
    """議決権数の集計から除外する事業所名のキーワード（会ごとに設定）"""
    return get_config().get("voting_excluded_org", "")


def save_voting_excluded_org(keyword: str) -> None:
    config = get_config()
    config["voting_excluded_org"] = keyword
    save_config(config)


def get_attendance_mail_folder() -> str:
    return get_config().get("attendance_mail_folder", "")


def save_attendance_mail_folder(folder_name: str) -> None:
    config = get_config()
    config["attendance_mail_folder"] = folder_name
    save_config(config)


def get_attendance_mail_subject_filter() -> str:
    return get_config().get("attendance_mail_subject_filter", "")


def save_attendance_mail_subject_filter(subject_filter: str) -> None:
    config = get_config()
    config["attendance_mail_subject_filter"] = subject_filter
    save_config(config)
