# Highlight Studio backend skeleton

`highlight-studio-productized.zip`(静的HTMLプロトタイプ)の HANDOFF.md
「6. バックエンド実装ロードマップ」に沿って作った、Flaskベースの叩き台。
**実際に決済・メール送信を行うコードは未実装**(該当箇所は501を返すか、
モックとしてログ出力するだけ)。次の担当者が各種APIキーを用意し、
コメントで示した本番実装例を有効化していく想定。

## 構成

```
backend/
  run.py                      # 開発サーバー起動
  app/
    __init__.py                # app factory、blueprint登録
    config.py                  # 環境変数ベースの設定(.env.example参照)
    extensions.py               # db, jwt のシングルトン
    models.py                   # User / ContactMessage 等
    routes/
      auth.py                   # signup/login/verify-email/password-reset/profile更新
      billing.py                 # Stripe Checkout・Webhook(スタブ、要実装)
      contact.py                 # 10-contact.html のフォーム送信先
    services/
      email_service.py           # メール送信の抽象化(SendGrid未設定時はログ出力のみ)
  requirements.txt
  .env.example
```

## フロントHTMLとの対応

| フロントのページ/機能 | 対応するAPI |
|---|---|
| `02-auth.html` 新規登録・メール確認 | `POST /api/auth/signup`, `POST /api/auth/verify-email` |
| `02-auth.html` ログイン | `POST /api/auth/login` |
| `04-reset-password.html` | `POST /api/auth/request-password-reset`, `POST /api/auth/reset-password` |
| `05-mypage.html` プロフィール編集 | `GET /api/auth/me`, `PATCH /api/auth/me` |
| `05-mypage.html` / `06-pricing.html` 課金 | `POST /api/billing/create-checkout-session`(要Stripe実装) |
| `10-contact.html` | `POST /api/contact` |

現状フロントは `localStorage` で完結しているため、これらのAPIに繋ぎ込む際は
各ページのJS内で `hs_userEmail` 等を直接読み書きしている箇所を
`fetch()` 呼び出しに置き換える作業が別途必要(このリポジトリには未着手)。

## セットアップ

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 値を埋める
python run.py
```

`load_dotenv()`を`app/config.py`の先頭で呼んでいるので、上記の通り`.env`を
用意するだけで値が読み込まれる(2026-09-08修正: 以前は`python-dotenv`が
requirements.txtに入っているだけで実際には呼ばれておらず、`.env`の中身が
すべて無視される不具合があった)。

**本番環境(`FLASK_ENV=production`)では、`SECRET_KEY` / `JWT_SECRET_KEY` を
`.env`で実際の値に変更していないと起動時に`RuntimeError`で止まる**(デフォルトの
プレースホルダー値のまま公開されるのを防ぐための安全装置。開発・テスト環境では
これまで通りプレースホルダーのままで起動できる)。

## テスト

```bash
pip install -r requirements.txt
pytest
```

`tests/` にauth・contact・billing・config(起動時の安全チェック)のpytestスイートを
用意した(インメモリSQLiteで動作、外部への通信は発生しない)。2026-09-08の検証パスで
実際に `pip install -r requirements.txt && pytest` を実行し、**19件全て合格**することを
確認済み(これ以前は環境のネットワーク制限で実行できず、構文チェックのみだった)。

## デバッグ用管理者アカウント

`.env` に `ADMIN_EMAIL` / `ADMIN_PASSWORD` を設定して起動すると、そのメールアドレスの
ユーザーを `is_admin=True` で自動作成する(既に存在する場合はフラグだけ立てる。
パスワードは上書きしないので、パスワードを変えたい場合は一度ユーザーを削除してから
再起動すること)。管理者ユーザーは `GET/PATCH /api/auth/me` や `POST /api/auth/login`
のレスポンスで `plan: "admin"` を返す(実際の課金プランである `plan` カラムは
Stripe連携用に "pro" のまま温存し、`is_admin` フラグとの合算値である `effective_plan`
プロパティ経由で上書きしている)。

フロント側(`highlight-studio-03-app.html` / `05-mypage.html`)は `plan: "admin"` を
「無料・無制限・課金導線非表示」として扱うようになっている(このAPIと未接続の
デモモードでも、`02-auth.html` のログイン画面にハードコードされた管理者アカウント
`admin@highlight-studio.local` / `debug-admin-2026` でログインすると同じ状態になる。
値は `highlight-studio-02-auth.html` 内の `ADMIN_CREDENTIALS` を参照/変更すること)。

**公開前に必ず**: デバッグが終わったら `ADMIN_EMAIL` / `ADMIN_PASSWORD` を空にするか
該当ユーザーを削除し、`02-auth.html` のハードコードされた `ADMIN_CREDENTIALS` も
削除または本番で使われない値に変更すること。

## 未実装・要判断のまま残している箇所

- **Stripe連携本体**(`app/routes/billing.py`): Checkout Session作成・Webhook処理を実装済み
  (`stripe`パッケージが無い/未設定の間は501を返すフォールバック)。ただし実キーでの動作確認は未実施。
- **SendGrid連携本体**(`app/services/email_service.py`): 同様に実装済み(未設定時はログ出力のみのモックにフォールバック)。実キーでの送信確認は未実施。
- **メールアドレス変更フロー**: マイページでの表示名・パスワード変更はAPI化したが、
  メールアドレス変更は再確認フローの設計が必要なため未着手。
- **動画解析パイプライン**: このリポジトリには含めていない。既存のFlask+ffmpeg/opencv
  プロトタイプ(`highlight_detector.py` / `exporter.py` / `app.py`)側の資産と想定。
- **特商法ページの実データ**: `.env.example` に `BUSINESS_NAME` 等の項目を用意した。
  値が揃ったら `.env` に設定し、`09-tokushoho.html` 側も同じ値に手動で差し替えること
  (現状09は静的HTMLのままなので自動反映はされない)。
- **マイグレーション管理**: 現状 `db.create_all()` のみ。スキーマ変更が発生する運用に
  乗せる前に Alembic 等へ切り替えること。
