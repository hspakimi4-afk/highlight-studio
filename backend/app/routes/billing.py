import logging

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..extensions import db
from ..models import User

billing_bp = Blueprint("billing", __name__)
logger = logging.getLogger("highlight_studio.billing")

PLAN_PRICE_ENV_KEYS = {
    "standard": "STRIPE_PRICE_ID_STANDARD",
    "pro": "STRIPE_PRICE_ID_PRO",
}

# プラン変更につながるStripe subscriptionのステータス。
_ACTIVE_STATUSES = {"active", "trialing"}


@billing_bp.post("/create-checkout-session")
@jwt_required()
def create_checkout_session():
    """
    06-pricing.html の「このプランで始める」ボタン → ここを叩く →
    Stripe Checkoutの決済ページURLを返してリダイレクトさせる、という流れを想定。

    カード情報は一切自前で扱わず、Stripeのホスト型決済ページに委譲する。
    """
    if not current_app.config.get("STRIPE_SECRET_KEY"):
        return jsonify({"error": "決済プロバイダが未設定です(STRIPE_SECRET_KEY)"}), 501

    plan = (request.get_json(silent=True) or {}).get("plan")
    price_env_key = PLAN_PRICE_ENV_KEYS.get(plan)
    price_id = current_app.config.get(price_env_key) if price_env_key else None
    if not price_id:
        return jsonify({"error": "不明なプラン、または価格IDが未設定です"}), 400

    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({"error": "ユーザーが見つかりません"}), 404

    try:
        import stripe
    except ImportError:
        return jsonify({"error": "stripeパッケージが未インストールです(pip install stripe)"}), 501

    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
    site_domain = current_app.config.get("SITE_DOMAIN", "")

    try:
        session_kwargs = dict(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{site_domain}/mypage.html?checkout=success",
            cancel_url=f"{site_domain}/pricing.html?checkout=cancelled",
            client_reference_id=user.id,
        )
        # 既にStripe顧客がいればそれを使い、いなければメールで新規作成させる
        if user.stripe_customer_id:
            session_kwargs["customer"] = user.stripe_customer_id
        else:
            session_kwargs["customer_email"] = user.email

        session = stripe.checkout.Session.create(**session_kwargs)
    except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
        logger.exception("Stripe checkout session creation failed")
        return jsonify({"error": f"決済セッションの作成に失敗しました: {exc.user_message or str(exc)}"}), 502

    return jsonify({"checkoutUrl": session.url})


@billing_bp.post("/webhook")
def stripe_webhook():
    """
    Stripeからのイベント受信先(決済完了・サブスク更新/解約など)。
    署名検証には STRIPE_WEBHOOK_SECRET を使う。
    """
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        return jsonify({"error": "Webhookシークレットが未設定です"}), 501

    try:
        import stripe
    except ImportError:
        return jsonify({"error": "stripeパッケージが未インストールです(pip install stripe)"}), 501

    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):  # type: ignore[attr-defined]
        return jsonify({"error": "不正なWebhookリクエストです"}), 400

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data_object)
    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        _handle_subscription_change(data_object, cancelled=(event_type == "customer.subscription.deleted"))
    else:
        logger.info("Unhandled Stripe event type: %s", event_type)

    return jsonify({"received": True})


def _plan_from_price_id(price_id: str) -> str:
    if price_id and price_id == current_app.config.get("STRIPE_PRICE_ID_PRO"):
        return "pro"
    if price_id and price_id == current_app.config.get("STRIPE_PRICE_ID_STANDARD"):
        return "standard"
    return "free"


def _handle_checkout_completed(session_obj: dict) -> None:
    user_id = session_obj.get("client_reference_id")
    customer_id = session_obj.get("customer")
    subscription_id = session_obj.get("subscription")

    user = User.query.get(user_id) if user_id else None
    if not user and customer_id:
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        logger.warning("checkout.session.completed: user not found (client_reference_id=%s)", user_id)
        return

    user.stripe_customer_id = customer_id or user.stripe_customer_id
    user.stripe_subscription_id = subscription_id or user.stripe_subscription_id
    # プラン名の確定はサブスクの価格IDに基づく方が正確だが、ここではCheckout完了時点で
    # 暫定的にstandard扱いにし、後続のsubscription.updatedイベントで正しいプランに補正する。
    if user.plan == "free":
        user.plan = "standard"
    db.session.commit()


def _handle_subscription_change(subscription_obj: dict, cancelled: bool) -> None:
    customer_id = subscription_obj.get("customer")
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        logger.warning("subscription event: user not found (customer=%s)", customer_id)
        return

    if cancelled or subscription_obj.get("status") not in _ACTIVE_STATUSES:
        user.plan = "free"
    else:
        items = subscription_obj.get("items", {}).get("data", [])
        price_id = items[0]["price"]["id"] if items else None
        user.plan = _plan_from_price_id(price_id)

    db.session.commit()
