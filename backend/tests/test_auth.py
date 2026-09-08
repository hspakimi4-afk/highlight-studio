from app.extensions import db
from app.models import EmailVerificationToken, PasswordResetToken, User


def _signup(client, email="user@example.com", password="password123"):
    return client.post("/api/auth/signup", json={"email": email, "password": password})


def test_signup_creates_unverified_user(client, app):
    res = _signup(client)
    assert res.status_code == 201
    with app.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        assert user is not None
        assert user.email_verified is False
        assert EmailVerificationToken.query.filter_by(user_id=user.id).count() == 1


def test_signup_rejects_short_password(client):
    res = _signup(client, password="short")
    assert res.status_code == 400


def test_signup_rejects_duplicate_email(client):
    _signup(client)
    res = _signup(client)
    assert res.status_code == 409


def test_login_requires_correct_password(client):
    _signup(client)
    ok = client.post("/api/auth/login", json={"email": "user@example.com", "password": "password123"})
    assert ok.status_code == 200
    assert "accessToken" in ok.get_json()

    bad = client.post("/api/auth/login", json={"email": "user@example.com", "password": "wrong"})
    assert bad.status_code == 401


def test_verify_email_with_valid_token(client, app):
    _signup(client)
    with app.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        token = EmailVerificationToken.query.filter_by(user_id=user.id).first().token

    res = client.post("/api/auth/verify-email", json={"token": token})
    assert res.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        assert user.email_verified is True


def test_verify_email_rejects_invalid_token(client):
    res = client.post("/api/auth/verify-email", json={"token": "does-not-exist"})
    assert res.status_code == 400


def _login(client, email="user@example.com", password="password123"):
    _signup(client, email, password)
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.get_json()["accessToken"]


def test_me_requires_auth(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_update_profile_changes_display_name(client):
    token = _login(client)
    res = client.patch(
        "/api/auth/me",
        json={"displayName": "配信太郎"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.get_json()["displayName"] == "配信太郎"


def test_password_reset_flow(client, app):
    _signup(client)
    client.post("/api/auth/request-password-reset", json={"email": "user@example.com"})

    with app.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        token = PasswordResetToken.query.filter_by(user_id=user.id).first().token

    res = client.post("/api/auth/reset-password", json={"token": token, "password": "newpassword123"})
    assert res.status_code == 200

    # 新パスワードでログインできる
    ok = client.post("/api/auth/login", json={"email": "user@example.com", "password": "newpassword123"})
    assert ok.status_code == 200

    # 使用済みトークンは再利用できない
    reused = client.post("/api/auth/reset-password", json={"token": token, "password": "anotherpassword"})
    assert reused.status_code == 400


def test_password_reset_request_does_not_leak_user_existence(client):
    """存在しないメールアドレスでも200を返し、ユーザー列挙を防ぐ。"""
    res = client.post("/api/auth/request-password-reset", json={"email": "nobody@example.com"})
    assert res.status_code == 200
