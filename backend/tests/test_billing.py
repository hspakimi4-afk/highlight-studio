def _login(client, email="user@example.com", password="password123"):
    client.post("/api/auth/signup", json={"email": email, "password": password})
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.get_json()["accessToken"]


def test_checkout_session_requires_auth(client):
    res = client.post("/api/billing/create-checkout-session", json={"plan": "standard"})
    assert res.status_code == 401


def test_checkout_session_501_when_stripe_not_configured(client):
    token = _login(client)
    res = client.post(
        "/api/billing/create-checkout-session",
        json={"plan": "standard"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # テスト環境ではSTRIPE_SECRET_KEYを設定していないので501になるはず
    assert res.status_code == 501


def test_webhook_501_when_secret_not_configured(client):
    res = client.post("/api/billing/webhook", data=b"{}")
    assert res.status_code == 501
