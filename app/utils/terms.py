# app/utils/terms.py
"""会ごとに変わる呼称を組み立てるユーティリティ。

議員の会では「議員退任」「議員退任者」「副会頭の就任順」と呼ぶが、
女性部では「退任」「退任者」「副会長の就任順」のように呼び方が変わる。
会ごとの設定（app_config.json の terms）から画面のラベルを組み立てる。

- member         : 会員の呼称（例：議員）。空欄なら接頭辞なしの「退任」になる
- order_position : 就任順を手動で並べ替える役職名（例：副会頭）
"""
from app.utils.app_config import get_config, save_config

_ACTIVE_STATE_FALLBACK = "在任状態"
_ORDER_BUTTON_FALLBACK = "就任順の設定"


def get_terms() -> dict:
    terms = get_config().get("terms")
    return terms if isinstance(terms, dict) else {}


def _term(key: str) -> str:
    value = get_terms().get(key, "")
    return value.strip() if isinstance(value, str) else ""


def save_member_term(member: str) -> None:
    """会員の呼称を保存する"""
    _save_term("member", member)


def save_order_position(position_name: str) -> None:
    """就任順を設定する役職名を保存する"""
    _save_term("order_position", position_name)


def _save_term(key: str, value: str) -> None:
    config = get_config()
    terms = config.get("terms")
    if not isinstance(terms, dict):
        terms = {}
    terms[key] = (value or "").strip()
    config["terms"] = terms
    save_config(config)


# ------------------------------------------------------------ 会員まわりの呼称

def member_term() -> str:
    """会員の呼称（例：議員）。未設定なら空文字。"""
    return _term("member")


def retire_label() -> str:
    """退任操作の呼称。「議員退任」／「退任」"""
    return f"{member_term()}退任"


def retired_label() -> str:
    """退任した人の呼称。「議員退任者」／「退任者」"""
    return f"{member_term()}退任者"


def active_state_label() -> str:
    """在任状態を表す項目名。「議員状態」／「在任状態」"""
    term = member_term()
    return f"{term}状態" if term else _ACTIVE_STATE_FALLBACK


# ------------------------------------------------------------ 就任順まわりの呼称

def order_position_name() -> str:
    """就任順を手動で並べ替える役職名（未設定なら空文字）"""
    return _term("order_position")


def order_button_label() -> str:
    """就任順設定を開くボタンの呼称。「副会頭の就任順」／「就任順の設定」"""
    name = order_position_name()
    return f"{name}の就任順" if name else _ORDER_BUTTON_FALLBACK
