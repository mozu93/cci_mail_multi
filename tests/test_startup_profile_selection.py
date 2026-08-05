"""起動時にどの会を開くかの判定（main._choose_profile）のテスト"""
from PyQt6.QtWidgets import QDialog

import main
from app.utils import profile_config as pc


class _FakeDialog:
    """exec() で指定の結果を返すダイアログの代役"""
    instances = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        type(self).instances.append(self)

    def exec(self):
        return self.result_code

    def profile(self):
        return self.returned_profile


def _fake_dialog_class(result_code=QDialog.DialogCode.Accepted, profile=None):
    return type("_Fake", (_FakeDialog,), {
        "instances": [],
        "result_code": result_code,
        "returned_profile": profile,
    })


def _forbid(name):
    def _raise(*args, **kwargs):
        raise AssertionError(f"{name} を表示しないこと")
    return _raise


def test_uses_last_profile_without_showing_selector(monkeypatch):
    """前回の会を記憶しており、通常起動では選択画面を出さない"""
    josei = pc.add_profile("女性部")
    pc.add_profile("青年部")
    pc.set_last_profile_id(josei["id"])
    monkeypatch.setattr(main, "ProfileSelectDialog", _forbid("会の選択画面"))
    monkeypatch.setattr(main, "ProfileEditDialog", _forbid("会の登録画面"))

    profile = main._choose_profile(force_select=False)

    assert profile["id"] == josei["id"]


def test_shows_selector_when_switching(monkeypatch):
    josei = pc.add_profile("女性部")
    seinen = pc.add_profile("青年部")
    pc.set_last_profile_id(josei["id"])
    fake = _fake_dialog_class(profile=seinen)
    monkeypatch.setattr(main, "ProfileSelectDialog", fake)

    profile = main._choose_profile(force_select=True)

    assert profile["id"] == seinen["id"]
    assert len(fake.instances) == 1


def test_shows_selector_when_option_enabled(monkeypatch):
    """「起動時にこの画面を表示する」を有効にした場合は毎回選択画面を出す"""
    josei = pc.add_profile("女性部")
    pc.set_last_profile_id(josei["id"])
    pc.set_show_selector_on_startup(True)
    fake = _fake_dialog_class(profile=josei)
    monkeypatch.setattr(main, "ProfileSelectDialog", fake)

    main._choose_profile(force_select=False)

    assert len(fake.instances) == 1


def test_shows_selector_when_last_profile_was_deleted(monkeypatch):
    josei = pc.add_profile("女性部")
    seinen = pc.add_profile("青年部")
    pc.set_last_profile_id(josei["id"])
    pc.delete_profile(josei["id"])
    fake = _fake_dialog_class(profile=seinen)
    monkeypatch.setattr(main, "ProfileSelectDialog", fake)

    profile = main._choose_profile(force_select=False)

    assert profile["id"] == seinen["id"]


def test_prompts_registration_when_no_profiles(monkeypatch):
    """会が未登録なら、まず会の登録画面を出す"""
    created = {"id": "new", "name": "女性部"}
    fake = _fake_dialog_class(profile=created)
    monkeypatch.setattr(main, "ProfileEditDialog", fake)
    monkeypatch.setattr(main, "ProfileSelectDialog", _forbid("会の選択画面"))

    profile = main._choose_profile(force_select=False)

    assert profile == created


def test_returns_none_when_registration_cancelled(monkeypatch):
    fake = _fake_dialog_class(result_code=QDialog.DialogCode.Rejected)
    monkeypatch.setattr(main, "ProfileEditDialog", fake)

    assert main._choose_profile(force_select=False) is None


def test_returns_none_when_selection_cancelled(monkeypatch):
    pc.add_profile("女性部")
    fake = _fake_dialog_class(result_code=QDialog.DialogCode.Rejected)
    monkeypatch.setattr(main, "ProfileSelectDialog", fake)

    assert main._choose_profile(force_select=True) is None
