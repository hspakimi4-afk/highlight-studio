from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import ContactMessage
from ..services.email_service import send_contact_autoreply, send_contact_notification_to_ops

contact_bp = Blueprint("contact", __name__)


@contact_bp.post("")
def submit_contact():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    body = (data.get("body") or "").strip()
    subject = (data.get("subject") or "").strip()

    if not name or not email or not body:
        return jsonify({"error": "お名前・メールアドレス・お問い合わせ内容は必須です"}), 400

    message = ContactMessage(name=name, email=email, subject=subject, body=body)
    db.session.add(message)
    db.session.commit()

    send_contact_autoreply(email)
    send_contact_notification_to_ops(name, email, subject, body)

    return jsonify({"message": "お問い合わせを受け付けました"}), 201
