import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User, EmailVerificationToken, PasswordResetToken
from ..services.email_service import send_verification_email, send_password_reset_email

auth_bp = Blueprint("auth", __name__)

TOKEN_TTL_HOURS = 24


def _as_aware_utc(dt):
    """SQLite等、DBから読み戻す際にtzinfoが失われる(naiveになる)環境向けの補正。
    保存時は必ずUTCで書き込んでいる前提のもと、tzinfoがNoneならUTCとして扱う。
    これが無いと、aware(datetime.now(timezone.utc))とnaiveな値の比較で
    `TypeError: can't compare offset-naive and offset-aware datetimes` になる。"""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@auth_bp.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or "@" not in email:
        return jsonify({"error": "有効なメールアドレスを入力してください"}), 400
    if len(password) < 8:
        return jsonify({"error": "パスワードは8文字以上にしてください"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "このメールアドレスは既に登録されています"}), 409

    user = User(email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    token = secrets.token_urlsafe(32)
    db.session.add(
        EmailVerificationToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
        )
    )
    db.session.commit()

    verify_url = f"{current_app.config.get('SITE_DOMAIN', '')}/verify?token={token}"
    send_verification_email(email, verify_url)

    return jsonify({"message": "確認メールを送信しました", "userId": user.id}), 201


@auth_bp.post("/verify-email")
def verify_email():
    token_value = (request.get_json(silent=True) or {}).get("token", "")
    record = EmailVerificationToken.query.filter_by(token=token_value, used=False).first()

    if not record or _as_aware_utc(record.expires_at) < datetime.now(timezone.utc):
        return jsonify({"error": "トークンが無効か、有効期限が切れています"}), 400

    user = User.query.get(record.user_id)
    user.email_verified = True
    record.used = True
    db.session.commit()

    return jsonify({"message": "メールアドレスを確認しました"})


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "メールアドレスまたはパスワードが正しくありません"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({"accessToken": access_token, "user": user.to_public_dict()})


@auth_bp.get("/me")
@jwt_required()
def me():
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({"error": "not found"}), 404
    return jsonify(user.to_public_dict())


@auth_bp.patch("/me")
@jwt_required()
def update_profile():
    """05-mypage.html の「プロフィールを編集」モーダルからの更新先。"""
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({"error": "not found"}), 404

    data = request.get_json(silent=True) or {}
    if "displayName" in data:
        user.display_name = data["displayName"]
    if "password" in data and data["password"]:
        if len(data["password"]) < 8:
            return jsonify({"error": "パスワードは8文字以上にしてください"}), 400
        user.password_hash = generate_password_hash(data["password"])
    # メールアドレス変更は再確認フローが必要になるためここでは未対応(要件次第で追加)

    db.session.commit()
    return jsonify(user.to_public_dict())


@auth_bp.post("/request-password-reset")
def request_password_reset():
    email = (request.get_json(silent=True) or {}).get("email", "").strip().lower()
    user = User.query.filter_by(email=email).first()

    # ユーザー列挙攻撃を避けるため、存在しない場合も同じレスポンスを返す
    if user:
        token = secrets.token_urlsafe(32)
        db.session.add(
            PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        db.session.commit()
        reset_url = f"{current_app.config.get('SITE_DOMAIN', '')}/reset-password?token={token}"
        send_password_reset_email(email, reset_url)

    return jsonify({"message": "パスワード再設定メールを送信しました(登録がある場合)"})


@auth_bp.post("/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    token_value = data.get("token", "")
    new_password = data.get("password", "")

    record = PasswordResetToken.query.filter_by(token=token_value, used=False).first()
    if not record or _as_aware_utc(record.expires_at) < datetime.now(timezone.utc):
        return jsonify({"error": "トークンが無効か、有効期限が切れています"}), 400
    if len(new_password) < 8:
        return jsonify({"error": "パスワードは8文字以上にしてください"}), 400

    user = User.query.get(record.user_id)
    user.password_hash = generate_password_hash(new_password)
    record.used = True
    db.session.commit()

    return jsonify({"message": "パスワードを再設定しました"})
