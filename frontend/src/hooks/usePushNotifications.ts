/**
 * usePushNotifications — Hook cho Web Push Notifications.
 *
 * Features:
 * - Request permission
 * - Subscribe to push notifications
 * - Handle push events
 * - Badge count (tương lai)
 *
 * Backend integration:
 * - POST /api/v1/push/subscription — Register subscription
 * - GET /api/v1/push/subscription — Get current subscription
 */
import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";

// VAPID public key (lấy từ backend hoặc env)
const VAPID_PUBLIC_KEY = import.meta.env.VITE_VAPID_PUBLIC_KEY || "";

interface PushNotificationPayload {
  title: string;
  body?: string;
  icon?: string;
  badge?: string;
  data?: Record<string, any>;
  actions?: Array<{ action: string; title: string }>;
}

export function usePushNotifications() {
  const [permission, setPermission] = useState<NotificationPermission>(
    typeof Notification !== "undefined" ? Notification.permission : "default"
  );
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [pushSupported, setPushSupported] = useState(
    "serviceWorker" in navigator && "PushManager" in window
  );

  // Request permission
  const requestPermission = useCallback(async () => {
    if (!pushSupported) {
      toast.error("Trình duyệt không hỗ trợ push notifications");
      return false;
    }

    try {
      const result = await Notification.requestPermission();
      setPermission(result);

      if (result === "granted") {
        toast.success("Đã bật thông báo");
        return true;
      } else if (result === "denied") {
        toast.error("Bạn đã từ chối nhận thông báo");
        return false;
      }
      return false;
    } catch (err) {
      console.error("Failed to request notification permission:", err);
      return false;
    }
  }, [pushSupported]);

  // Subscribe to push
  const subscribePush = useCallback(async () => {
    if (!pushSupported || permission !== "granted") {
      return false;
    }

    try {
      const registration = await navigator.serviceWorker.ready;

      // Check for existing subscription
      let subscription = await registration.pushManager.getSubscription();

      if (!subscription) {
        // Convert VAPID key from base64 to Uint8Array
        const vapidKey = urlBase64ToUint8Array(VAPID_PUBLIC_KEY);

        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: vapidKey,
        });
      }

      // Send to backend
      const token = localStorage.getItem("token");
      const response = await fetch("/api/v1/push/subscription", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(subscription),
      });

      if (!response.ok) {
        throw new Error("Failed to register push subscription");
      }

      setIsSubscribed(true);
      toast.success("Đã đăng ký nhận thông báo");
      return true;
    } catch (err) {
      console.error("Failed to subscribe to push:", err);
      toast.error("Lỗi khi đăng ký push notifications");
      return false;
    }
  }, [pushSupported, permission]);

  // Unsubscribe
  const unsubscribePush = useCallback(async () => {
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();

      if (subscription) {
        await subscription.unsubscribe();

        // Notify backend
        const token = localStorage.getItem("token");
        await fetch("/api/v1/push/subscription", {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        });

        setIsSubscribed(false);
        toast.info("Đã hủy đăng ký thông báo");
      }
    } catch (err) {
      console.error("Failed to unsubscribe:", err);
    }
  }, []);

  // Setup push event listener
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    const handlePush = (event: any) => {
      const data = event.data?.json() as PushNotificationPayload | undefined;
      if (!data) return;

      event.waitUntil(
        self.registration.showNotification(data.title, {
          body: data.body,
          icon: data.icon,
          badge: data.badge,
          data: data.data,
          actions: data.actions,
        })
      );
    };

    // Note: This runs in service worker context, not main thread
    // We'll handle push in service-worker.ts instead
  }, []);

  // Check existing subscription
  useEffect(() => {
    const checkSubscription = async () => {
      if (!pushSupported) return;

      try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        setIsSubscribed(!!subscription);
      } catch (err) {
        console.error("Failed to check push subscription:", err);
      }
    };

    checkSubscription();
  }, [pushSupported]);

  return {
    permission,
    isSubscribed,
    pushSupported,
    requestPermission,
    subscribePush,
    unsubscribePush,
  };
}

// Helper: Convert base64 URL-safe string to Uint8Array
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }

  return outputArray;
}
