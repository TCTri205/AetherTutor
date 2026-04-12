"""
Push Notification API — Web Push subscription management.

Endpoints:
- POST /push/subscription — Register push subscription
- GET  /push/subscription — Get current subscription
- DELETE /push/subscription — Unsubscribe
"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.api.dependencies import get_current_user_id
from app.services.notification_service import get_notification_service

router = APIRouter(prefix="/push", tags=["push-notifications"])


@router.post("/subscription", status_code=status.HTTP_201_CREATED)
async def register_push_subscription(
    subscription: dict,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Register a Web Push subscription for the current user.
    
    Request body should be the PushSubscription object from browser:
    {
        "endpoint": "https://...",
        "keys": {
            "p256dh": "...",
            "auth": "..."
        }
    }
    """
    notification_service = get_notification_service()
    success = await notification_service.subscribe_push(user_id, subscription)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store push subscription",
        )

    logger.info(f"Push subscription registered for user {user_id}")
    return {"status": "success", "message": "Push subscription registered"}


@router.get("/subscription")
async def get_push_subscription(
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get current push subscription status."""
    notification_service = get_notification_service()

    if not notification_service.redis:
        return {"subscribed": False, "reason": "Redis not available"}

    # Check if subscription exists
    key = f"push:vapid:{user_id}"
    sub = await notification_service.redis.get(key)

    return {
        "subscribed": sub is not None,
        "has_vapid_configured": bool(
            getattr(notification_service, 'VAPID_PRIVATE_KEY', None)
        ),
    }


@router.delete("/subscription", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_push_subscription(
    endpoint: str | None = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Unregister push subscription for the current user."""
    notification_service = get_notification_service()
    success = await notification_service.unsubscribe_push(
        user_id, endpoint or ""
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove push subscription",
        )

    logger.info(f"Push subscription removed for user {user_id}")
