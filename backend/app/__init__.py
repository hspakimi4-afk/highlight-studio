"""
Highlight Studio backend — app factory

このファイルはロードマップ項目「1. ユーザーデータ永続化・認証基盤」の土台。
フロントエンド(highlight-studio-productized.zip 内の静的HTML)から
fetch() でこのAPIを叩く前提の構成にしてある。
"""
from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from .config import ProductionConfig, get_config
from .extensions import db, jwt

_INSECURE_DEFAULT_SECRET = "change-me-in-.env"


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    _reject_insecure_production_secrets(app, config_class)

    # フロントは別オリジン(静的ホスティング)からAPIを叩く想定なのでCORSを許可
    CORS(app, resources={r"/api/*": {"origins": app.config["ALLOWED_ORIGINS"]}})

    db.init_app(app)
    jwt.init_app(app)

    from .routes.auth import auth_bp
    from .routes.billing import billing_bp
    from .routes.contact import contact_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(billing_bp, url_prefix="/api/billing")
    app.register_blueprint(contact_bp, url_prefix="/api/contact")

    with app.app_context():
        db.create_all()  # 初回起動用。本番はAlembicでマイグレーション管理に切り替えること。
        _ensure_admin_account(app)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


def _reject_insecure_production_secrets(app: Flask, config_class) -> None:
    """本番環境(FLASK_ENV=production)で、SECRET_KEY / JWT_SECRET_KEY が
    .env未設定時のデフォルト値("change-me-in-.env")のままだと、誰でも
    JWTを偽造できてしまう。開発・テスト環境ではこのデフォルト値のままで
    動かせて問題ないため、本番設定のときだけ起動時に検出して止める。
    """
    if config_class is not ProductionConfig:
        return

    unsafe_keys = [
        name
        for name in ("SECRET_KEY", "JWT_SECRET_KEY")
        if app.config.get(name) == _INSECURE_DEFAULT_SECRET
    ]
    if unsafe_keys:
        raise RuntimeError(
            "本番環境(FLASK_ENV=production)では "
            + " / ".join(unsafe_keys)
            + " にデフォルト値のままの秘密鍵を使用できません。"
            ".env で十分に長いランダムな値を設定してください。"
        )


def _ensure_admin_account(app: Flask) -> None:
    """ADMIN_EMAIL / ADMIN_PASSWORD が設定されている場合、デバッグ用に
    無制限・無料で使える管理者アカウントを起動時に用意する。

    - 未登録なら新規作成する
    - 既に登録済みなら is_admin フラグだけ立てる(パスワードは上書きしない。
      パスワードを変えたい場合は一度ユーザーを削除してから再起動すること)
    """
    from werkzeug.security import generate_password_hash

    from .models import User

    admin_email = (app.config.get("ADMIN_EMAIL") or "").strip().lower()
    admin_password = app.config.get("ADMIN_PASSWORD") or ""
    if not admin_email or not admin_password:
        return  # 未設定の場合は何もしない(本番のデフォルト状態)

    user = User.query.filter_by(email=admin_email).first()
    if user is None:
        user = User(
            email=admin_email,
            password_hash=generate_password_hash(admin_password),
            display_name="管理者(デバッグ用)",
            email_verified=True,
            plan="pro",
            is_admin=True,
        )
        db.session.add(user)
        db.session.commit()
    elif not user.is_admin:
        user.is_admin = True
        db.session.commit()
