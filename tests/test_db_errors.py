from app.utils.db_errors import format_connection_error


def _cp932_decode_error(message: str) -> UnicodeDecodeError:
    """psycopg2がCP932のサーバーメッセージをUTF-8として読んだ状況を再現する"""
    raw = message.encode("cp932")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as e:
        return e
    raise AssertionError("UTF-8として復号できてしまい、状況を再現できていない")


def test_recovered_message_is_shown_without_unreadable_notice():
    """CP932から復元できたときは「表示できません」と断らないこと"""
    error = _cp932_decode_error(
        'connection to server at "192.168.10.222", port 5432 failed: '
        'FATAL:  データベース"jyosei"は存在しません')

    message = format_connection_error(error)

    assert "詳細を正しく表示できません" not in message
    assert 'データベース"jyosei"は存在しません' in message


def test_missing_database_gets_creation_hint():
    error = _cp932_decode_error('FATAL:  データベース"jyosei"は存在しません')

    message = format_connection_error(error)

    assert "【対処】" in message
    assert "データベースがサーバーにまだ作成されていません" in message


def test_missing_database_hint_in_english_locale():
    error = RuntimeError('FATAL:  database "jyosei" does not exist')

    message = format_connection_error(error)

    assert "データベースがサーバーにまだ作成されていません" in message


def test_missing_role_gets_user_hint_not_database_hint():
    error = RuntimeError('FATAL:  role "postgres" does not exist')

    message = format_connection_error(error)

    assert "ユーザー名がサーバーに登録されていません" in message
    assert "データベースがサーバーにまだ作成されていません" not in message


def test_bad_password_gets_credentials_hint():
    error = RuntimeError(
        'FATAL:  password authentication failed for user "postgres"')

    message = format_connection_error(error)

    assert "ユーザー名またはパスワードが違います" in message


def test_unreachable_server_gets_network_hint():
    error = RuntimeError(
        'could not connect to server: Connection refused (0x0000274D/10061)')

    message = format_connection_error(error)

    assert "サーバーPCが起動しているか" in message


def test_pg_hba_gets_permission_hint():
    error = RuntimeError(
        'FATAL:  no pg_hba.conf entry for host "192.168.10.10"')

    message = format_connection_error(error)

    assert "pg_hba.conf" in message
    assert "接続を許可していません" in message


def test_unrecognized_error_is_passed_through_unchanged():
    message = format_connection_error(RuntimeError("何らかの想定外エラー"))

    assert message == "何らかの想定外エラー"
    assert "【対処】" not in message


def test_undecodable_message_keeps_unreadable_notice():
    """CP932でも読めない場合は、従来どおり断り書きを表示する"""
    error = UnicodeDecodeError("utf-8", b"\x81\x00\xff\xfe", 0, 1, "invalid")

    message = format_connection_error(error)

    assert "詳細を正しく表示できません" in message
