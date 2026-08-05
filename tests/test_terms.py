from app.utils import terms
from app.utils import profile_config as pc


# ------------------------------------------------------------ 呼称の組み立て

def test_labels_have_no_prefix_when_term_unset():
    """呼称を設定していない会では「退任」「退任者」と表示する"""
    assert terms.member_term() == ""
    assert terms.retire_label() == "退任"
    assert terms.retired_label() == "退任者"
    assert terms.active_state_label() == "在任状態"


def test_labels_use_configured_term():
    terms.save_member_term("議員")

    assert terms.retire_label() == "議員退任"
    assert terms.retired_label() == "議員退任者"
    assert terms.active_state_label() == "議員状態"


def test_member_term_is_trimmed():
    terms.save_member_term("  議員  ")
    assert terms.member_term() == "議員"


def test_member_term_can_be_cleared():
    terms.save_member_term("議員")
    terms.save_member_term("")
    assert terms.retire_label() == "退任"


# ---------------------------------------------------------- 就任順の対象役職

def test_order_button_label_without_position():
    assert terms.order_position_name() == ""
    assert terms.order_button_label() == "就任順の設定"


def test_order_button_label_uses_configured_position():
    terms.save_order_position("副会長")
    assert terms.order_button_label() == "副会長の就任順"

    terms.save_order_position("副会頭")
    assert terms.order_button_label() == "副会頭の就任順"


def test_saving_one_term_keeps_the_other():
    terms.save_member_term("議員")
    terms.save_order_position("副会頭")

    assert terms.member_term() == "議員"
    assert terms.order_position_name() == "副会頭"

    terms.save_member_term("")
    assert terms.order_position_name() == "副会頭", "他の呼称を消さないこと"


def test_terms_survive_alongside_other_settings():
    """既存の設定（Microsoft 365など）を壊さないこと"""
    from app.utils.app_config import get_config, save_config
    save_config({"graph": {"client_id": "abc"}})

    terms.save_member_term("議員")

    assert get_config()["graph"]["client_id"] == "abc"


# ------------------------------------------------------------ 会ごとの独立性

def test_terms_are_independent_per_profile():
    josei = pc.add_profile("女性部")
    giin = pc.add_profile("議員")

    pc.set_active_profile_id(giin["id"])
    terms.save_member_term("議員")
    terms.save_order_position("副会頭")

    pc.set_active_profile_id(josei["id"])
    assert terms.retire_label() == "退任"
    terms.save_order_position("副会長")
    assert terms.order_button_label() == "副会長の就任順"

    pc.set_active_profile_id(giin["id"])
    assert terms.retire_label() == "議員退任"
    assert terms.order_button_label() == "副会頭の就任順"


def test_broken_terms_value_is_ignored():
    """設定ファイルが壊れていても既定の呼称で動作すること"""
    from app.utils.app_config import save_config
    save_config({"terms": "壊れた値"})

    assert terms.member_term() == ""
    assert terms.retire_label() == "退任"
