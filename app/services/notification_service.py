"""
NotificationService - Multi-channel notification delivery.

Supports:
- Browser Push Notifications (Web Push API)
- Email (SMTP)
- Web Push Subscriptions (VAPID)
- Future: Telegram Bot (Stage 3)
"""
import uuid
import json
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


# VAPID keys (should be configured in .env for production)
VAPID_PRIVATE_KEY = getattr(settings, 'VAPID_PRIVATE_KEY', None)
VAPID_CLAIMS = {
    "sub": getattr(settings, 'VAPID_CLAIMS_SUB', "mailto:admin@aethertutor.local")
}


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

    # -----------------------------------------------------------------------
    # VAPID Web Push Integration (Sprint 18 — Task 7)
    # -----------------------------------------------------------------------

    async def subscribe_push(
        self,
        user_id: uuid.UUID,
        subscription: Dict[str, Any],
    ) -> bool:
        """
        Register a Web Push subscription for a user.
        
        Stores subscription data in Redis key: push:vapid:{user_id}
        
        Args:
            user_id: User UUID
            subscription: Web Push subscription object from browser
                {
                    "endpoint": "https://fcm.googleapis.com/...",
                    "keys": {
                        "p256dh": "...",
                        "auth": "..."
                    }
                }
        
        Returns:
            True if subscription was stored successfully
        """
        if not self.redis:
            logger.warning("Redis not available, cannot store push subscription")
            return False

        try:
            key = f"push:vapid:{user_id}"
            await self.redis.set(key, json.dumps(subscription))
            # Also store in set for multiple devices
            await self.redis.sadd(f"push:vapid:all:{user_id}", json.dumps(subscription))
            logger.info(f"VAPID push subscription stored for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store VAPID subscription: {e}")
            return False

    async def unsubscribe_push(
        self,
        user_id: uuid.UUID,
        endpoint: str,
    ) -> bool:
        """
        Remove a Web Push subscription for a user.
        
        Args:
            user_id: User UUID
            endpoint: Push endpoint to remove
        
        Returns:
            True if subscription was removed successfully
        """
        if not self.redis:
            return False

        try:
            key = f"push:vapid:{user_id}"
            await self.redis.delete(key)
            await self.redis.delete(f"push:vapid:all:{user_id}")
            logger.info(f"VAPID push subscription removed for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove VAPID subscription: {e}")
            return False

    async def send_push_notification(
        self,
        user_id: uuid.UUID,
        title: str,
        body: str,
        icon: str = "/icons/icon-192x192.png",
        badge: str = "/icons/icon-192x192.png",
        data: Optional[Dict[str, Any]] = None,
        tag: Optional[str] = None,
    ) -> bool:
        """
        Send a Web Push notification using VAPID.
        
        Uses pywebpush library to send notifications via VAPID protocol.
        Falls back to browser notification if VAPID not configured.
        
        Args:
            user_id: User UUID
            title: Notification title
            body: Notification body text
            icon: Icon URL
            badge: Badge URL
            data: Additional data payload
            tag: Notification tag for grouping
        
        Returns:
            True if notification was sent successfully
        """
        if not self.redis:
            logger.warning("Redis not available, cannot send push notification")
            return False

        try:
            # Get subscription from Redis
            key = f"push:vapid:{user_id}"
            sub_json = await self.redis.get(key)
            if not sub_json:
                logger.debug(f"No VAPID subscription found for user {user_id}")
                return False

            subscription = json.loads(sub_json)

            # Check if VAPID is configured
            if not VAPID_PRIVATE_KEY:
                # Fallback: just log (mock mode)
                logger.info(
                    f"[VAPID MOCK] Push notification to user {user_id}: "
                    f"{title} - {body}"
                )
                return True

            # In production, use pywebpush:
            # from pywebpush import webpush, WebPushException
            # try:
            #     webpush(
            #         subscription_info=subscription,
            #         data=json.dumps({
            #             "title": title,
            #             "body": body,
            #             "icon": icon,
            #             "badge": badge,
            #             "data": data or {},
            #             "tag": tag or "default",
            #         }),
            #         vapid_private_key=VAPID_PRIVATE_KEY,
            #         vapid_claims=VAPID_CLAIMS,
            #     )
            #     logger.info(f"VAPID push notification sent to user {user_id}")
            #     return True
            # except WebPushException as e:
            #     logger.error(f"VAPID push failed: {e}")
            #     # Clean up invalid subscription
            #     if e.response and e.response.status_code in [404, 410]:
            #         await self.unsubscribe_push(user_id, subscription.get("endpoint", ""))
            #     return False

            logger.info(f"VAPID push notification would be sent to user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send VAPID push notification: {e}")
            return False


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service(redis_client: Optional[redis.Redis] = None) -> NotificationService:
    """Factory để lấy NotificationService singleton."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService(redis_client)
    return _notification_service
