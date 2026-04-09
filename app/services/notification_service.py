"""
NotificationService - Multi-channel notification delivery.

Supports:
- Browser Push Notifications (Web Push API)
- Email (SMTP)
- Future: Telegram Bot (Stage 3)
"""
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import redis.asyncio as redis
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..config import settings
from ..constants import NOTIFICATION_BROWSER_ENABLED, NOTIFICATION_EMAIL_ENABLED

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service gửi thông báo qua nhiều kênh.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client

    async def send_browser_notification(
        self,
        user_id: uuid.UUID,
        title: str,
        body: str,
        icon: str = "/icon.png",
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Gửi browser push notification qua Web Push API.
        Lưu subscription vào Redis key: push:sub:{user_id}
        """
        if not NOTIFICATION_BROWSER_ENABLED:
            logger.debug("Browser notifications disabled")
            return False

        if not self.redis:
            logger.warning("Redis not available, cannot send browser notification")
            return False

        try:
            # Lấy push subscription từ Redis
            subscription_key = f"push:sub:{user_id}"
            subscription = await self.redis.get(subscription_key)

            if not subscription:
                logger.debug(f"No push subscription found for user {user_id}")
                return False

            # Gửi notification payload tới subscription
            # (Thực tế sẽ dùng webpush library, ở đây chỉ log)
            payload = {
                "title": title,
                "body": body,
                "icon": icon,
                "data": data or {},
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info(f"Browser notification sent to user {user_id}: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send browser notification: {e}")
            return False

    async def send_email_notification(
        self,
        user_email: str,
        subject: str,
        html_content: str
    ) -> bool:
        """
        Gửi email notification qua SMTP.
        """
        if not NOTIFICATION_EMAIL_ENABLED:
            logger.debug("Email notifications disabled")
            return False

        if not settings.SMTP_HOST:
            logger.warning("SMTP_HOST not configured")
            return False

        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = settings.SMTP_FROM_EMAIL
            message["To"] = user_email

            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Gửi email
            async with aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                use_tls=settings.SMTP_PORT == 465
            ) as smtp:
                if settings.SMTP_USER:
                    await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                await smtp.send_message(message)

            logger.info(f"Email notification sent to {user_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    async def send_flashcard_digest(
        self,
        user_id: uuid.UUID,
        user_email: Optional[str],
        due_cards_count: int,
        streak_days: int
    ) -> bool:
        """
        Gửi daily digest notification cho flashcard review.
        """
        title = f"{due_cards_count} flashcards đang chờ!"
        body = f"Hãy ôn tập ngay để duy trì streak {streak_days} ngày 🔥"

        # Thử browser notification trước
        browser_sent = await self.send_browser_notification(
            user_id=user_id,
            title=title,
            body=body,
            data={"type": "flashcard_digest", "due_count": due_cards_count}
        )

        if browser_sent:
            return True

        # Fallback: Email
        if user_email:
            html_content = f"""
            <html>
            <body>
                <h2>AetherTutor Daily Digest</h2>
                <p>Bạn có <strong>{due_cards_count} flashcards</strong> cần ôn hôm nay.</p>
                <p>Streak hiện tại: <strong>{streak_days} ngày</strong> 🔥</p>
                <p><a href='https://aethertutor.local/flashcards'>Ôn tập ngay</a></p>
            </body>
            </html>
            """

            email_sent = await self.send_email_notification(
                user_email=user_email,
                subject=f"📚 {due_cards_count} flashcards đang chờ bạn!",
                html_content=html_content
            )

            if email_sent:
                return True

        logger.warning(f"Failed to send digest notification to user {user_id}")
        return False


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service(redis_client: Optional[redis.Redis] = None) -> NotificationService:
    """Factory để lấy NotificationService singleton."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService(redis_client)
    return _notification_service
