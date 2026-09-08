"""
メール送信サービス。

SENDGRID_API_KEY が未設定の間は実送信せず、送信内容をログに出すだけの
モックとして動作する(02-auth.html / 10-contact.html の
「送信されません」という既存注記と挙動を合わせてある)。
SENDGRID_API_KEY が設定されている場合は実際にSendGrid経由で送信する。
"""
import logging
from flask import current_app

logger = logging.getLogger("highlight_studio.email")


def send_email(to: str, subject: str, body: str) -> bool:
    api_key = current_app.config.get("SENDGRID_API_KEY")

    if not api_key:
        logger.info("[MOCK EMAIL] to=%s subject=%s\n%s", to, subject, body)
        return True

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
    except ImportError:
        logger.error(
            "SENDGRID_API_KEY is set but the 'sendgrid' package is not installed "
            "(pip install sendgrid). Falling back to mock/log output."
        )
        logger.info("[MOCK EMAIL] to=%s subject=%s\n%s", to, subject, body)
        return False

    message = Mail(
        from_email=current_app.config.get("MAIL_FROM_ADDRESS", "support@example.com"),
        to_emails=to,
        subject=subject,
        plain_text_content=body,
    )
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        return response.status_code < 300
    except Exception:
        logger.exception("SendGrid send failed (to=%s subject=%s)", to, subject)
        return False


def send_verification_email(to: str, verify_url: str) -> bool:
    return send_email(
        to=to,
        subject="【Highlight Studio】メールアドレスの確認",
        body=f"以下のリンクからメールアドレスの確認を完了してください。\n{verify_url}",
    )


def send_password_reset_email(to: str, reset_url: str) -> bool:
    return send_email(
        to=to,
        subject="【Highlight Studio】パスワード再設定",
        body=f"以下のリンクからパスワードを再設定してください(有効期限あり)。\n{reset_url}",
    )


def send_contact_autoreply(to: str) -> bool:
    return send_email(
        to=to,
        subject="【Highlight Studio】お問い合わせを受け付けました",
        body="お問い合わせありがとうございます。内容を確認のうえ、担当者よりご連絡いたします。",
    )


def send_contact_notification_to_ops(name: str, email: str, subject: str, body: str) -> bool:
    """運営宛の通知(BUSINESS_CONTACT_EMAIL 宛)。値が未設定の間は何もしない。"""
    ops_email = current_app.config.get("BUSINESS_CONTACT_EMAIL")
    if not ops_email:
        logger.info("BUSINESS_CONTACT_EMAIL is not set; skipping ops notification.")
        return False
    return send_email(
        to=ops_email,
        subject=f"【お問い合わせ】{subject or '(種別未指定)'} - {name}",
        body=f"差出人: {name} <{email}>\n\n{body}",
    )
