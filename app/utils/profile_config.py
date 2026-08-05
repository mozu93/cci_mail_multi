# app/utils/profile_config.py
"""会（部会）プロファイル管理

女性部・青年部・議員など「会」ごとにデータベースを分けて運用するための仕組み。

- 会の一覧と前回起動した会 : %APPDATA%/cci-mail-multi/profiles.json
- 会ごとの設定（Microsoft 365接続情報・UI設定・最終担当者）
                             : %APPDATA%/cci-mail-multi/profiles/<会ID>/

起動中の会は set_active_profile_id() でプロセス内に保持し、
app_config / settings_service はこの「起動中の会」を見て保存先を切り替える。
"""
import json
import os
import re
import sys
import uuid
from pathlib import Path

APP_DIR_NAME = "cci-mail-multi"

_active_profile_id: str = ""


def app_root_dir() -> Path:
    """アプリ全体のデータ保存ルート（%APPDATA%/cci-mail-multi）"""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or Path.home()
    else:
        base = Path.home()
    d = Path(base) / APP_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def profiles_file() -> Path:
    return app_root_dir() / "profiles.json"


def _load() -> dict:
    p = profiles_file()
    data = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("profiles", [])
    data.setdefault("last_profile_id", "")
    data.setdefault("show_selector_on_startup", False)
    return data


def _save(data: dict) -> None:
    profiles_file().write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- 会の一覧

def list_profiles() -> list[dict]:
    """登録済みの会を登録順に返す"""
    return _load()["profiles"]


def get_profile(profile_id: str) -> dict | None:
    for p in list_profiles():
        if p.get("id") == profile_id:
            return p
    return None


def get_profile_by_name(name: str) -> dict | None:
    for p in list_profiles():
        if p.get("name") == name:
            return p
    return None


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", name).strip().strip(".")
    return cleaned or "profile"


def default_sqlite_path(name: str) -> str:
    """会名から既定のSQLiteファイルパスを組み立てる"""
    d = app_root_dir() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return str(d / f"{_sanitize_filename(name)}.db")


def add_profile(name: str, db_type: str = "sqlite", db_path: str = "",
                postgresql: dict | None = None) -> dict:
    """会を新規登録して、登録したプロファイルを返す"""
    name = (name or "").strip()
    if not name:
        raise ValueError("会の名称を入力してください。")
    data = _load()
    if any(p.get("name") == name for p in data["profiles"]):
        raise ValueError(f"「{name}」は既に登録されています。")
    if db_type == "sqlite" and not db_path:
        db_path = default_sqlite_path(name)
    profile = {
        "id": uuid.uuid4().hex,
        "name": name,
        "db_type": db_type,
        "db_path": db_path,
        "postgresql": postgresql or {},
    }
    data["profiles"].append(profile)
    _save(data)
    return profile


def update_profile(profile_id: str, **fields) -> dict:
    """会の登録内容を更新して、更新後のプロファイルを返す"""
    data = _load()
    if "name" in fields:
        name = (fields["name"] or "").strip()
        if not name:
            raise ValueError("会の名称を入力してください。")
        if any(p.get("name") == name and p.get("id") != profile_id
               for p in data["profiles"]):
            raise ValueError(f"「{name}」は既に登録されています。")
        fields["name"] = name
    for p in data["profiles"]:
        if p.get("id") == profile_id:
            p.update(fields)
            _save(data)
            return p
    raise KeyError(profile_id)


def delete_profile(profile_id: str) -> None:
    """会の登録を削除する（データベース本体のファイルは削除しない）"""
    global _active_profile_id
    data = _load()
    data["profiles"] = [p for p in data["profiles"] if p.get("id") != profile_id]
    if data.get("last_profile_id") == profile_id:
        data["last_profile_id"] = ""
    _save(data)
    if _active_profile_id == profile_id:
        _active_profile_id = ""


# ------------------------------------------------------ 前回起動した会の記憶

def get_last_profile_id() -> str:
    """前回起動した会のID（未記録なら空文字）"""
    return _load().get("last_profile_id", "")


def set_last_profile_id(profile_id: str) -> None:
    data = _load()
    data["last_profile_id"] = profile_id
    _save(data)


def get_last_profile() -> dict | None:
    """前回起動した会（登録が消えている場合は None）"""
    return get_profile(get_last_profile_id())


def get_show_selector_on_startup() -> bool:
    """起動時に必ず会の選択画面を表示するかどうか"""
    return bool(_load().get("show_selector_on_startup", False))


def set_show_selector_on_startup(value: bool) -> None:
    data = _load()
    data["show_selector_on_startup"] = bool(value)
    _save(data)


# -------------------------------------------------------------- 起動中の会

def set_active_profile_id(profile_id: str) -> None:
    global _active_profile_id
    _active_profile_id = profile_id or ""


def get_active_profile_id() -> str:
    return _active_profile_id


def get_active_profile() -> dict | None:
    if not _active_profile_id:
        return None
    return get_profile(_active_profile_id)


def get_active_profile_name() -> str:
    profile = get_active_profile()
    return profile.get("name", "") if profile else ""


def profile_dir(profile_id: str) -> Path:
    """会ごとの設定保存ディレクトリ（会が未選択なら共通の _default）"""
    d = app_root_dir() / "profiles" / (profile_id or "_default")
    d.mkdir(parents=True, exist_ok=True)
    return d


def active_profile_dir() -> Path:
    return profile_dir(_active_profile_id)


def copy_settings_from(src_profile_id: str, dest_profile_id: str) -> None:
    """他の会の設定（Microsoft 365接続情報など）を引き継ぐ。

    接続先データベースと出力先パスは会ごとに異なるため引き継がない。
    """
    src = profile_dir(src_profile_id) / "app_config.json"
    if not src.exists():
        return
    try:
        config = json.loads(src.read_text(encoding="utf-8"))
    except Exception:
        return
    for key in ("db_type", "db_path", "postgresql", "html_export_path"):
        config.pop(key, None)
    dest = profile_dir(dest_profile_id) / "app_config.json"
    dest.write_text(json.dumps(config, ensure_ascii=False, indent=2),
                    encoding="utf-8")


# ------------------------------------------------- 起動中の会の接続先設定

def get_active_db_settings() -> dict:
    """起動中の会の接続先設定。会が未選択の場合は app_config.json を見る。"""
    profile = get_active_profile()
    if profile is not None:
        return {
            "db_type": profile.get("db_type", "sqlite"),
            "db_path": profile.get("db_path", ""),
            "postgresql": profile.get("postgresql", {}),
        }
    from app.utils.app_config import get_config
    config = get_config()
    return {
        "db_type": config.get("db_type", "sqlite"),
        "db_path": config.get("db_path", ""),
        "postgresql": config.get("postgresql", {}),
    }


def save_active_db_settings(db_type: str, db_path: str = "",
                            postgresql: dict | None = None) -> None:
    """起動中の会の接続先設定を保存する"""
    profile = get_active_profile()
    if profile is not None:
        update_profile(profile["id"], db_type=db_type, db_path=db_path,
                       postgresql=postgresql or {})
        return
    from app.utils.app_config import get_config, save_config
    config = get_config()
    config["db_type"] = db_type
    config["db_path"] = db_path
    config["postgresql"] = postgresql or {}
    save_config(config)
