import pytest

from app.utils import profile_config as pc


def test_no_profiles_initially():
    assert pc.list_profiles() == []
    assert pc.get_last_profile_id() == ""
    assert pc.get_last_profile() is None


def test_add_profile_creates_sqlite_path_from_name():
    profile = pc.add_profile("女性部")
    assert profile["name"] == "女性部"
    assert profile["db_type"] == "sqlite"
    assert profile["db_path"].endswith("女性部.db")
    assert [p["name"] for p in pc.list_profiles()] == ["女性部"]


def test_add_profile_rejects_duplicate_name():
    pc.add_profile("女性部")
    with pytest.raises(ValueError):
        pc.add_profile("女性部")


def test_add_profile_rejects_empty_name():
    with pytest.raises(ValueError):
        pc.add_profile("   ")


def test_add_profile_with_postgresql():
    profile = pc.add_profile(
        "青年部", db_type="postgresql",
        postgresql={"host": "db.example.local", "port": "5432",
                    "database": "cci_mail_seinen", "user": "postgres",
                    "password": "secret"})
    assert profile["db_type"] == "postgresql"
    assert profile["postgresql"]["database"] == "cci_mail_seinen"


def test_update_profile_renames_and_keeps_id():
    profile = pc.add_profile("女性部")
    updated = pc.update_profile(profile["id"], name="女性会")
    assert updated["id"] == profile["id"]
    assert updated["name"] == "女性会"


def test_update_profile_rejects_duplicate_name():
    pc.add_profile("女性部")
    other = pc.add_profile("青年部")
    with pytest.raises(ValueError):
        pc.update_profile(other["id"], name="女性部")


def test_delete_profile_clears_last_profile():
    profile = pc.add_profile("女性部")
    pc.set_last_profile_id(profile["id"])
    pc.delete_profile(profile["id"])
    assert pc.list_profiles() == []
    assert pc.get_last_profile_id() == ""


def test_last_profile_is_remembered():
    """前回起動した会を記憶し、次回はそのまま開けること"""
    josei = pc.add_profile("女性部")
    pc.add_profile("青年部")
    pc.set_last_profile_id(josei["id"])

    remembered = pc.get_last_profile()
    assert remembered is not None
    assert remembered["name"] == "女性部"


def test_last_profile_is_none_when_registration_removed():
    profile = pc.add_profile("女性部")
    pc.set_last_profile_id(profile["id"])
    pc.delete_profile(profile["id"])
    assert pc.get_last_profile() is None


def test_show_selector_on_startup_defaults_to_false():
    assert pc.get_show_selector_on_startup() is False
    pc.set_show_selector_on_startup(True)
    assert pc.get_show_selector_on_startup() is True


def test_active_profile_dir_is_separate_per_profile():
    josei = pc.add_profile("女性部")
    seinen = pc.add_profile("青年部")

    pc.set_active_profile_id(josei["id"])
    josei_dir = pc.active_profile_dir()
    pc.set_active_profile_id(seinen["id"])
    seinen_dir = pc.active_profile_dir()

    assert josei_dir != seinen_dir
    assert josei_dir.is_dir() and seinen_dir.is_dir()


def test_active_db_settings_follow_active_profile():
    josei = pc.add_profile("女性部", db_type="sqlite", db_path="C:/data/josei.db")
    seinen = pc.add_profile(
        "青年部", db_type="postgresql",
        postgresql={"host": "db.example.local", "database": "seinen"})

    pc.set_active_profile_id(josei["id"])
    assert pc.get_active_db_settings()["db_type"] == "sqlite"
    assert pc.get_active_db_settings()["db_path"] == "C:/data/josei.db"

    pc.set_active_profile_id(seinen["id"])
    settings = pc.get_active_db_settings()
    assert settings["db_type"] == "postgresql"
    assert settings["postgresql"]["database"] == "seinen"


def test_save_active_db_settings_only_touches_active_profile():
    josei = pc.add_profile("女性部", db_type="sqlite", db_path="C:/data/josei.db")
    seinen = pc.add_profile("青年部", db_type="sqlite", db_path="C:/data/seinen.db")

    pc.set_active_profile_id(josei["id"])
    pc.save_active_db_settings(db_type="sqlite", db_path="D:/new/josei.db")

    assert pc.get_profile(josei["id"])["db_path"] == "D:/new/josei.db"
    assert pc.get_profile(seinen["id"])["db_path"] == "C:/data/seinen.db"


def test_app_config_is_isolated_per_profile():
    """会ごとに設定ファイルが分かれ、他の会の設定を書き換えないこと"""
    from app.utils.app_config import get_config, save_config
    josei = pc.add_profile("女性部")
    seinen = pc.add_profile("青年部")

    pc.set_active_profile_id(josei["id"])
    save_config({"graph": {"from_address": "josei@example.com"}})

    pc.set_active_profile_id(seinen["id"])
    assert get_config() == {}
    save_config({"graph": {"from_address": "seinen@example.com"}})

    pc.set_active_profile_id(josei["id"])
    assert get_config()["graph"]["from_address"] == "josei@example.com"


def test_ui_settings_are_isolated_per_profile():
    from app.services.settings_service import get_last_staff, set_last_staff
    josei = pc.add_profile("女性部")
    seinen = pc.add_profile("青年部")

    pc.set_active_profile_id(josei["id"])
    set_last_staff("担当者A")

    pc.set_active_profile_id(seinen["id"])
    assert get_last_staff() == ""

    pc.set_active_profile_id(josei["id"])
    assert get_last_staff() == "担当者A"


def test_copy_settings_from_excludes_db_connection():
    from app.utils.app_config import get_config, save_config
    josei = pc.add_profile("女性部")
    pc.set_active_profile_id(josei["id"])
    save_config({
        "graph": {"client_id": "shared-client"},
        "db_type": "postgresql",
        "postgresql": {"database": "josei"},
        "html_export_path": "C:/share/josei.html",
    })

    seinen = pc.add_profile("青年部")
    pc.copy_settings_from(josei["id"], seinen["id"])

    pc.set_active_profile_id(seinen["id"])
    config = get_config()
    assert config["graph"]["client_id"] == "shared-client"
    assert "db_type" not in config
    assert "postgresql" not in config
    assert "html_export_path" not in config


def test_get_db_type_falls_back_when_no_profile_selected():
    """会が未選択でも既定値で動作すること"""
    assert pc.get_active_profile() is None
    from app.utils.app_config import get_db_type
    assert get_db_type() == "sqlite"
