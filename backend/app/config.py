import os

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

# README/HANDOFFの手順は「.env.exampleを.envにコピーして値を埋める」だが、
# python-dotenvはrequirements.txtに入っているだけで、これまでどこからも
# load_dotenv()が呼ばれていなかった。そのため`python run.py`(README記載の
# 起動方法)で実行すると、.envに書いた値(SECRET_KEY/JWT_SECRET_KEY/Stripe・
# SendGridキー/事業者情報/管理者アカウント等すべて)が一切読み込まれず、
# 各項目がデフォルト値(空文字列や"change-me-in-.env")のまま動いてしまう
# 不具合があった。configモジュールがos.environを読む前に呼ぶ必要があるため、
# このファイルの先頭(BaseConfigクラス定義より前)で呼び出す。
# すでにOS環境変数が設定されている場合(本番のコンテナ/PaaS環境など)は
# override=Falseなのでそちらが優先され、.envの値で上書きされることはない。
load_dotenv()


class BaseConfig:
    # `.env.example`は各キーを"KEY="の形(値は空文字列)で列挙している。
    # os.environ.get(key, default)は「キー自体が存在しない」場合しかdefaultを
    # 使わないため、load_dotenv()で.envを読み込むと、まだ値を埋めていない
    # (=空文字列の).envキーがdefaultを潰して空文字列のまま採用されてしまう。
    # 「未設定なら意味のあるデフォルト値を使う」という意図の項目は、
    # `os.environ.get(key) or default`(空文字列もFalsyとして扱う)にする。
    SECRET_KEY = os.environ.get("SECRET_KEY") or "change-me-in-.env"
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL") or "sqlite:///highlight_studio.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or "change-me-in-.env"
    JWT_ACCESS_TOKEN_EXPIRES_MIN = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MIN") or "60")

    ALLOWED_ORIGINS = (os.environ.get("ALLOWED_ORIGINS") or "http://localhost:5500").split(",")

    # --- 決済(Stripe) ---
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_ID_STANDARD = os.environ.get("STRIPE_PRICE_ID_STANDARD", "")
    STRIPE_PRICE_ID_PRO = os.environ.get("STRIPE_PRICE_ID_PRO", "")

    # --- メール送信 ---
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
    MAIL_FROM_ADDRESS = os.environ.get("MAIL_FROM_ADDRESS") or "support@example.com"

    # --- 特定商取引法に基づく表記(highlight-studio-09-tokushoho.html と同じ値を
    #     ここでも環境変数化しておく。将来09ページをテンプレート化して差し込む際、
    #     または問い合わせ自動返信の署名に使う際にハードコードを避けられる) ---
    BUSINESS_NAME = os.environ.get("BUSINESS_NAME", "")
    BUSINESS_REP_NAME = os.environ.get("BUSINESS_REP_NAME", "")
    BUSINESS_CONTACT_EMAIL = os.environ.get("BUSINESS_CONTACT_EMAIL", "")
    SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "")  # 例: https://highlight-studio.jp

    # --- デバッグ用管理者アカウント ---
    # 設定されている場合、アプリ起動時にこのメールアドレスのユーザーを
    # is_admin=True で自動作成(既に存在する場合はis_adminフラグのみ付与)する。
    # 本番公開後は、デバッグが終わり次第これらの環境変数を削除し、
    # 発行済みの管理者アカウントも無効化・削除すること。
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Flask-SQLAlchemyでは:memory:DBはデフォルトだと接続ごとに別DBになってしまうため、
    # StaticPoolで単一コネクションを使い回してテスト間でテーブルが共有されるようにする。
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }


_CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name: str | None):
    name = name or os.environ.get("FLASK_ENV", "development")
    return _CONFIGS.get(name, DevelopmentConfig)
