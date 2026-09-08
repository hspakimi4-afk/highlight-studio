import uuid
from datetime import datetime, timezone

from .extensions import db


def _uuid() -> str:
    return str(uuid.uuid4())


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), nullable=True)

    email_verified = db.Column(db.Boolean, default=False, nullable=False)

    plan = db.Column(db.String(20), default="free", nullable=False)  # free / standard / pro
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)

    # デバッグ用の管理者フラグ。true の場合、フロント側では課金プランに関わらず
    # 常に "admin" プラン(無制限・無料、フロントの highlight-studio-05-mypage.html /
    # highlight-studio-03-app.html の PLANS['admin'] に対応)として扱う。
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def effective_plan(self) -> str:
        """課金プランより管理者フラグを優先した、実際に適用されるプラン名。"""
        return "admin" if self.is_admin else self.plan

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "displayName": self.display_name,
            "emailVerified": self.email_verified,
            "plan": self.effective_plan,
            "isAdmin": self.is_admin,
        }


class EmailVerificationToken(db.Model):
    __tablename__ = "email_verification_tokens"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)


class ContactMessage(db.Model):
    """10-contact.html のフォーム送信先。"""

    __tablename__ = "contact_messages"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
