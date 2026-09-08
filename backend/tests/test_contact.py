from app.models import ContactMessage


def test_contact_submission_is_stored(client, app):
    res = client.post(
        "/api/contact",
        json={
            "name": "配信太郎",
            "email": "streamer@example.com",
            "subject": "billing",
            "body": "料金プランについて質問があります。",
        },
    )
    assert res.status_code == 201

    with app.app_context():
        assert ContactMessage.query.count() == 1
        msg = ContactMessage.query.first()
        assert msg.email == "streamer@example.com"


def test_contact_requires_required_fields(client):
    res = client.post("/api/contact", json={"name": "", "email": "", "body": ""})
    assert res.status_code == 400
