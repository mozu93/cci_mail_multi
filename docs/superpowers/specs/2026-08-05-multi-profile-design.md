# 会（部会）プロファイル対応 設計書

**作成日：** 2026-08-05
**対象：** cci-mail-multi v1.0.0

## 1. 背景と目的

議員向けに作られた既存アプリ（`cci_giin_mail`）を、女性部・青年部など**他の会でも使える汎用アプリ**として
独立させる。担当する会を選んで起動でき、会ごとにデータが完全に分離されることを目標とする。

### 要件

1. 起動時に担当する会（女性部・青年部・議員など）を選べる
2. **前回起動した会を記憶し、通常は選び直さずに起動できる**
3. 会ごとにデータベースが分かれ、他の会のデータは見えない
4. 既存の議員向けアプリとは別アプリとして並行導入できる

## 2. データ分離の方式

**会ごとに別データベース**を採用した。単一DBに「会」列を持たせる案と比較して、

| 観点 | 会ごとに別DB（採用） | 単一DB＋会列 |
|---|---|---|
| データ漏れのリスク | 構造的にゼロ | フィルタ漏れで他会のデータが見える |
| バックアップ・移行 | 会ごとに独立して可能 | 全会まとめてのみ |
| 会ごとの権限分離 | DB権限で分離可能 | アプリ層でしか分離できない |
| 既存コードへの影響 | 接続先の切り替えのみ | 全クエリに条件追加が必要 |

既存の全サービス層コードを変更せずに済む点が決め手。

## 3. 保存先の構造

```
%APPDATA%\cci-mail-multi\
  profiles.json                  会の一覧・前回起動した会・起動時オプション
  data\
    女性部.db                     SQLite利用時の既定のデータファイル（会ごと）
    青年部.db
  profiles\
    <会ID>\
      app_config.json            Microsoft 365接続情報・議決権除外設定など
      ui_settings.json           文字サイズ・列表示・最終ログイン担当者
    _default\                    会が未選択のとき（テスト等）に使う退避先
```

`profiles.json` の構造：

```json
{
  "profiles": [
    {
      "id": "32桁の16進文字列",
      "name": "女性部",
      "db_type": "sqlite | postgresql",
      "db_path": "SQLite利用時のファイルパス",
      "postgresql": { "host": "", "port": "", "database": "", "user": "", "password": "" }
    }
  ],
  "last_profile_id": "前回起動した会のID",
  "show_selector_on_startup": false
}
```

会の名称を変更しても `id` は変わらないため、設定ディレクトリとデータファイルの対応は維持される。

## 4. モジュール構成

| モジュール | 役割 |
|---|---|
| `app/utils/profile_config.py` | 会の一覧管理、前回起動した会の記憶、起動中の会の保持 |
| `app/utils/app_config.py` | 起動中の会の `app_config.json` を読み書き。DB接続設定は `profile_config` へ委譲 |
| `app/services/settings_service.py` | 起動中の会の `ui_settings.json` を読み書き |
| `app/ui/dialogs/profile_select_dialog.py` | 会の選択・追加・編集・削除 |
| `app/ui/dialogs/profile_edit_dialog.py` | 会1件の登録・編集（名称＋DB接続先） |

「起動中の会」は `profile_config._active_profile_id` にプロセス内グローバルとして保持する。
`app_config` と `settings_service` はこれを参照して保存先を決めるため、**既存の呼び出し側は変更不要**。

会が未選択のとき（テスト実行時や、会の登録前）は `_default` ディレクトリへフォールバックし、
DB種別は `sqlite` を既定とする。これにより既存のサービス層テストがそのまま通る。

## 5. 起動フロー

```
main()
 └─ ループ（会の切り替えでここへ戻る）
     ① 起動中の会をクリア・DBエンジンをリセット
     ② _choose_profile()
          ├─ 会が未登録            → ProfileEditDialog（会の登録）
          ├─ 切り替え要求 or
          │  「起動時に表示」ON     → ProfileSelectDialog（会の選択）
          └─ それ以外              → 前回の会をそのまま採用（画面を出さない）
     ③ 起動中の会として設定し、last_profile_id に記録
     ④ _connect_database()：接続できるまで ProfileEditDialog で設定を促す
     ⑤ LoginDialog（担当者選択）
     ⑥ MainWindow を表示し app.exec()
     ⑦ 「会を切り替える」要求がなければ終了。あればループ先頭へ
```

`--select-profile` を付けて起動すると、①の時点で選択画面を強制表示する。

会の切り替えは、`MainWindow` にフラグを立ててウィンドウを閉じ、`app.exec()` の戻りを
`main()` のループで受けて再度起動処理を行う方式とした。プロセスを再起動しないため、
Qt の初期化コストとちらつきを避けられる。

## 6. 汎用化した箇所

### 議決権数の除外事業所

議員総会向けにハードコードされていた「四日市商工会議所」を、会ごとの設定
（`app_config.json` の `voting_excluded_org`）へ移した。空欄の場合は事業所による除外を行わず、
Excel出力の注記文もそれに合わせて変化する。議決権数を扱わない会（女性部・青年部など）は
空欄のまま利用する。

「監事」の除外と「専務理事」の例外は、会をまたいで共通の運用のため定数のまま残した。

## 7. 既存アプリとの共存

| 項目 | 議員向け（既存） | 部会版（本アプリ） |
|---|---|---|
| 実行ファイル | `CCIMail.exe` | `CCIMailMulti.exe` |
| インストール先 | `%LOCALAPPDATA%\CCIMail` | `%LOCALAPPDATA%\CCIMailMulti` |
| 設定・データ | `%APPDATA%\cci-mail` | `%APPDATA%\cci-mail-multi` |
| 認証キャッシュ | `%USERPROFILE%\.cci-mail` | `%USERPROFILE%\.cci-mail-multi` |
| 更新配布元 | `mozu93/cci_giin_mail` | `mozu93/cci_mail_multi` |

保存先が完全に分かれているため、両方を同時にインストールしても干渉しない。
既存の議員データは移行せず、必要になった時点でExcelインポートで移す。

## 8. テスト

| テストファイル | 対象 |
|---|---|
| `tests/test_profile_config.py` | 会の登録・更新・削除、前回起動した会の記憶、会ごとの設定分離 |
| `tests/test_profile_dialogs.py` | 会の登録・編集・選択ダイアログの挙動 |
| `tests/test_startup_profile_selection.py` | 起動時にどの画面を出すかの判定 |
| `tests/test_main_window_profile.py` | タイトル表示、会の切り替えメニュー |
| `tests/test_meeting_service.py` | 議決権除外事業所の設定あり／なしの集計 |

`tests/conftest.py` の `isolate_user_data` で `APPDATA` を一時ディレクトリへ差し替え、
`_active_profile_id` をテストごとにリセットして、状態がテスト間で持ち越されないようにしている。
