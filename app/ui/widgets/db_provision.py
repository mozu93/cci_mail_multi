# app/ui/widgets/db_provision.py
"""PostgreSQLデータベースをアプリから作成するための共通UI処理。

「会の登録・編集」ダイアログと「設定」タブのデータベース接続画面の
どちらからも同じ手順で作成できるようにする。
"""
from PyQt6.QtWidgets import QMessageBox

from app.database.provisioning import (
    create_database, database_exists, validate_database_name,
)
from app.utils.db_errors import format_connection_error


def _validate_connection_inputs(pg: dict) -> str:
    if not pg.get("host", "").strip():
        return "ホスト名 / IPアドレスを入力してください。"
    if not pg.get("user", "").strip():
        return "ユーザー名を入力してください。"
    return validate_database_name(pg.get("database", ""))


def create_database_interactive(parent, pg: dict) -> bool:
    """確認のうえデータベースを作成する。作成済み・作成成功なら True。"""
    error = _validate_connection_inputs(pg)
    if error:
        QMessageBox.warning(parent, "入力エラー", error)
        return False

    database = pg["database"].strip()
    try:
        if database_exists(pg, database):
            QMessageBox.information(
                parent, "作成済み",
                f"データベース「{database}」はすでに存在します。\n"
                "そのまま接続テストを行ってください。")
            return True
    except Exception as e:
        QMessageBox.critical(
            parent, "サーバーに接続できません",
            "データベースの作成に必要なサーバー接続ができませんでした。\n\n"
            f"{format_connection_error(e)}")
        return False

    answer = QMessageBox.question(
        parent, "データベースの作成",
        f"サーバー「{pg['host']}」に、データベース「{database}」を新しく作成します。\n\n"
        "よろしいですか？",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes)
    if answer != QMessageBox.StandardButton.Yes:
        return False

    try:
        create_database(pg, database)
    except Exception as e:
        QMessageBox.critical(
            parent, "作成に失敗しました",
            f"データベース「{database}」を作成できませんでした。\n\n"
            f"{format_connection_error(e)}\n\n"
            "接続ユーザーにデータベースの作成権限がない可能性があります。\n"
            "権限のあるユーザーで実行するか、pgAdmin等で作成してください。")
        return False

    QMessageBox.information(
        parent, "作成完了",
        f"データベース「{database}」を作成しました。")
    return True


def offer_to_create_database(parent, pg: dict) -> bool:
    """接続失敗がDB未作成によるものだったときに、作成を促す。作成したら True。"""
    database = pg.get("database", "").strip()
    answer = QMessageBox.question(
        parent, "データベースがありません",
        f"データベース「{database}」はサーバー上にまだ作成されていません。\n\n"
        "いま作成しますか？",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes)
    if answer != QMessageBox.StandardButton.Yes:
        return False
    return create_database_interactive(parent, pg)
