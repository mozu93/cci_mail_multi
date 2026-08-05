from app.utils import profile_config as pc


def _make_window(qtbot, **kwargs):
    from app.ui.main_window import MainWindow
    window = MainWindow(**kwargs)
    qtbot.addWidget(window)
    return window


def test_title_includes_active_profile_name(qtbot):
    profile = pc.add_profile("女性部")
    pc.set_active_profile_id(profile["id"])

    window = _make_window(qtbot)

    assert "商工会議所メール配信システム" in window.windowTitle()
    assert "［女性部］" in window.windowTitle()


def test_title_includes_profile_and_staff(qtbot, monkeypatch):
    monkeypatch.setattr("app.ui.main_window.get_staff_by_name",
                        lambda session, name: None)
    profile = pc.add_profile("青年部")
    pc.set_active_profile_id(profile["id"])

    window = _make_window(qtbot, staff_name="担当者A")

    assert "［青年部］" in window.windowTitle()
    assert "［担当者A］" in window.windowTitle()


def test_title_marks_readonly_with_profile(qtbot):
    profile = pc.add_profile("女性部")
    pc.set_active_profile_id(profile["id"])

    window = _make_window(qtbot, readonly=True)

    assert "［女性部］" in window.windowTitle()
    assert "【閲覧専用】" in window.windowTitle()


def test_file_menu_has_switch_profile_action(qtbot):
    window = _make_window(qtbot)
    menus = [action.text() for action in window.menuBar().actions()]
    assert "ファイル" in menus

    file_menu = next(action.menu() for action in window.menuBar().actions()
                     if action.text() == "ファイル")
    labels = [a.text() for a in file_menu.actions()]
    assert "会を切り替える…" in labels


def test_switch_profile_not_requested_by_default(qtbot):
    window = _make_window(qtbot)
    assert window.switch_profile_requested() is False


def test_switch_profile_request_closes_window(qtbot):
    window = _make_window(qtbot)
    window.show()

    window._request_switch_profile()

    assert window.switch_profile_requested() is True
    assert window.isVisible() is False
