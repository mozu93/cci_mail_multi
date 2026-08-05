"""DB接続エラーをユーザー向けの文字列に整形するユーティリティ。

日本語Windows環境のPostgreSQLは既定でサーバーメッセージがCP932(Shift-JIS)で
返ってくることがあり、UTF-8前提のpsycopg2がそれを取り込む際に
UnicodeDecodeErrorを送出してしまい、本来のエラー内容が握りつぶされることがある。
その場合は生バイト列をCP932としてデコードし直し、実際のメッセージを救出する。

救出に成功したときは元のメッセージがそのまま読めるため、
「文字コードが不正で表示できない」という断り書きは付けない。
"""

_UNREADABLE_NOTICE = (
    "サーバーからのエラーメッセージの文字コードが不正なため、"
    "詳細を正しく表示できません。\n"
    "（PostgreSQLサーバーのロケール設定が原因の可能性があります）"
)

# 原因ごとの対処ヒント。上から順に判定するため、より限定的なものを先に置く。
_HINTS = [
    (
        ("role", "ロール", "user", "ユーザ"),
        ("does not exist", "存在しません"),
        "指定したユーザー名がサーバーに登録されていません。\n"
        "ユーザー名を確認するか、PostgreSQL側でユーザーを作成してください。",
    ),
    (
        ("database", "データベース"),
        ("does not exist", "存在しません"),
        "指定した名前のデータベースがサーバーにまだ作成されていません。\n"
        "pgAdmin等でデータベースを作成してから、もう一度お試しください。\n"
        "（会ごとに別のデータベースを作成して使用します）",
    ),
    (
        (),
        ("password authentication failed", "パスワード認証に失敗"),
        "ユーザー名またはパスワードが違います。\n入力内容を確認してください。",
    ),
    (
        (),
        ("could not connect", "connection refused", "接続を拒否",
         "timeout expired", "could not translate host name"),
        "サーバーに接続できませんでした。\n"
        "サーバーPCが起動しているか、ホスト名/IPアドレス・ポート番号が正しいか、\n"
        "サーバー側のファイアウォールで通信が許可されているかを確認してください。",
    ),
    (
        (),
        ("no pg_hba.conf entry", "pg_hba.conf"),
        "サーバーがこのPCからの接続を許可していません。\n"
        "サーバーの pg_hba.conf に接続元の設定を追加してください。",
    ),
]


def _decode_detail(e: Exception) -> tuple[str, bool]:
    """エラー詳細と、文字化けせず読める状態かどうかを返す。"""
    if not isinstance(e, UnicodeDecodeError):
        return str(e), True
    try:
        detail = e.object.decode("cp932", errors="replace")
    except Exception:
        return str(e), False
    # 置換文字が残っていれば、読めない部分があるということ
    return detail, "�" not in detail


def _hint_for(detail: str) -> str:
    lowered = detail.lower()
    for subjects, symptoms, hint in _HINTS:
        if not any(s in lowered for s in symptoms):
            continue
        if subjects and not any(s in lowered for s in subjects):
            continue
        return hint
    return ""


def format_connection_error(e: Exception) -> str:
    detail, readable = _decode_detail(e)
    parts = []
    if not readable:
        parts.append(_UNREADABLE_NOTICE)
    parts.append(detail.strip())
    hint = _hint_for(detail)
    if hint:
        parts.append(f"【対処】\n{hint}")
    return "\n\n".join(parts)


def is_missing_database_error(e: Exception) -> bool:
    """接続先のデータベースがまだ作成されていないことが原因かどうか"""
    detail, _ = _decode_detail(e)
    lowered = detail.lower()
    if not any(s in lowered for s in ("does not exist", "存在しません")):
        return False
    if any(s in lowered for s in ("role", "ロール")):
        return False
    return any(s in lowered for s in ("database", "データベース"))
