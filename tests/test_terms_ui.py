from PyQt6.QtWidgets import QMessageBox

from app.utils import terms
from app.services.position_service import create_position
from app.services.member_service import create_member


# ------------------------------------------------------------ 名簿タブの表示

def _member_tab(qtbot, monkeypatch, db_session):
    monkeypatch.setattr("app.ui.member_tab.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    from app.ui.member_tab import MemberTab
    tab = MemberTab()
    qtbot.addWidget(tab)
    return tab


def test_member_tab_labels_without_term(qtbot, monkeypatch, db_session):
    tab = _member_tab(qtbot, monkeypatch, db_session)

    assert tab._btn_retire.text() == "退任"
    assert tab._show_inactive.text() == "退任者を含む"
    assert tab._btn_order.text() == "就任順の設定"


def test_member_tab_labels_use_configured_terms(qtbot, monkeypatch, db_session):
    terms.save_member_term("議員")
    terms.save_order_position("副会頭")

    tab = _member_tab(qtbot, monkeypatch, db_session)

    assert tab._btn_retire.text() == "議員退任"
    assert tab._show_inactive.text() == "議員退任者を含む"
    assert tab._btn_order.text() == "副会頭の就任順"


def test_member_tab_labels_refresh_after_setting_change(
        qtbot, monkeypatch, db_session):
    """設定変更後、名簿タブへ切り替えるとラベルが更新されること"""
    tab = _member_tab(qtbot, monkeypatch, db_session)
    assert tab._btn_retire.text() == "退任"

    terms.save_member_term("部員")
    terms.save_order_position("副会長")
    tab.refresh()

    assert tab._btn_retire.text() == "部員退任"
    assert tab._show_inactive.text() == "部員退任者を含む"
    assert tab._btn_order.text() == "副会長の就任順"


# -------------------------------------------------- 変更履歴ダイアログの表示

def test_history_field_label_follows_term():
    from app.ui.dialogs.member_history_dialog import _field_label

    assert _field_label("is_active") == "在任状態"
    assert _field_label("member_number") == "会員番号"

    terms.save_member_term("議員")
    assert _field_label("is_active") == "議員状態"


# -------------------------------------------------- 就任順設定ダイアログ

def _order_dialog(qtbot, db_session):
    from app.ui.dialogs.order_settings_dialog import OrderSettingsDialog
    dlg = OrderSettingsDialog(db_session)
    qtbot.addWidget(dlg)
    return dlg


def test_order_dialog_lists_all_positions(qtbot, db_session):
    create_position(db_session, "会長", 1)
    create_position(db_session, "副会長", 2)

    dlg = _order_dialog(qtbot, db_session)

    labels = [dlg._pos_combo.itemText(i) for i in range(dlg._pos_combo.count())]
    assert "会長" in labels
    assert "副会長" in labels


def test_order_dialog_preselects_configured_position(qtbot, db_session):
    create_position(db_session, "会長", 1)
    create_position(db_session, "副会長", 2)
    terms.save_order_position("副会長")

    dlg = _order_dialog(qtbot, db_session)

    assert dlg._selected_position_name() == "副会長"
    assert dlg.windowTitle() == "副会長の就任順設定"


def test_order_dialog_lists_members_of_selected_position(qtbot, db_session):
    vice = create_position(db_session, "副会長", 1)
    create_member(db_session, "A-001", "○○商事", "一番太郎",
                  position_id=vice.id, organization_kana="アアショウジ")
    create_member(db_session, "A-002", "△△産業", "二番次郎",
                  position_id=vice.id, organization_kana="イイサンギョウ")
    terms.save_order_position("副会長")

    dlg = _order_dialog(qtbot, db_session)

    listed = [dlg._member_list.item(i).text()
              for i in range(dlg._member_list.count())]
    assert any("一番太郎" in text for text in listed)
    assert any("二番次郎" in text for text in listed)


def test_order_dialog_saves_selected_position_as_setting(
        qtbot, monkeypatch, db_session):
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: None))
    vice = create_position(db_session, "副会長", 1)
    create_member(db_session, "A-001", "○○商事", "一番太郎", position_id=vice.id)

    dlg = _order_dialog(qtbot, db_session)
    dlg._pos_combo.setCurrentIndex(dlg._pos_combo.findText("副会長"))
    dlg._save()

    assert terms.order_position_name() == "副会長"
    assert terms.order_button_label() == "副会長の就任順"


def test_order_dialog_saves_display_order(qtbot, monkeypatch, db_session):
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: None))
    vice = create_position(db_session, "副会長", 1)
    first = create_member(db_session, "A-001", "○○商事", "一番太郎",
                          position_id=vice.id, organization_kana="アア")
    second = create_member(db_session, "A-002", "△△産業", "二番次郎",
                           position_id=vice.id, organization_kana="イイ")
    terms.save_order_position("副会長")

    dlg = _order_dialog(qtbot, db_session)
    dlg._member_list.setCurrentRow(1)
    dlg._move(dlg._member_list, -1)  # 2人目を先頭へ
    dlg._save()

    assert second.display_order == 1
    assert first.display_order == 2


def test_order_dialog_requires_position_selection(qtbot, monkeypatch, db_session):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: warnings.append(a)))
    create_position(db_session, "副会長", 1)

    dlg = _order_dialog(qtbot, db_session)
    dlg._pos_combo.setCurrentIndex(0)  # 「（役職を選択してください）」
    dlg._save()

    assert warnings
    assert terms.order_position_name() == ""


# ------------------------------------------------------------ 会の設定タブ

def _profile_settings(qtbot, monkeypatch):
    from app.ui.settings_tab import _ProfileSettingsWidget
    widget = _ProfileSettingsWidget()
    qtbot.addWidget(widget)
    return widget


def test_profile_settings_saves_member_term(qtbot, monkeypatch):
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: None))
    widget = _profile_settings(qtbot, monkeypatch)

    widget._member_term.setText("議員")
    widget._save()

    assert terms.retire_label() == "議員退任"


def test_profile_settings_preview_reflects_input(qtbot, monkeypatch):
    widget = _profile_settings(qtbot, monkeypatch)

    widget._member_term.setText("部員")

    assert "部員退任" in widget._term_preview.text()
    assert "部員退任者を含む" in widget._term_preview.text()


def test_profile_settings_loads_existing_term(qtbot, monkeypatch):
    terms.save_member_term("議員")

    widget = _profile_settings(qtbot, monkeypatch)

    assert widget._member_term.text() == "議員"
