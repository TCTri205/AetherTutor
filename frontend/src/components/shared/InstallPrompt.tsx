/**
 * InstallPrompt — Prompt người dùng cài đặt PWA.
 *
 * Features:
 * - Detect beforeinstallprompt event
 * - Show banner/modal "Install AetherTutor"
 * - Handle user choice (accept/dismiss)
 * - Auto-hide sau khi user chọn hoặc sau 7 ngày
 */
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);

  useEffect(() => {
    // Check if user dismissed install prompt recently
    const dismissedAt = localStorage.getItem("pwa-install-dismissed");
    if (dismissedAt) {
      const daysSinceDismissed = (Date.now() - parseInt(dismissedAt)) / (1000 * 60 * 60 * 24);
      if (daysSinceDismissed < 7) {
        return; // Don't show again for 7 days
      }
    }

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setShowPrompt(true);
    };

    window.addEventListener("beforeinstallprompt", handler);

    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;

    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;

    if (outcome === "accepted") {
      toast.success("Đã cài đặt AetherTutor! 🎉");
    } else {
      localStorage.setItem("pwa-install-dismissed", Date.now().toString());
      toast.info("Bạn có thể cài đặt sau từ thanh địa chỉ trình duyệt");
    }

    setDeferredPrompt(null);
    setShowPrompt(false);
  };

  const handleDismiss = () => {
    localStorage.setItem("pwa-install-dismissed", Date.now().toString());
    setShowPrompt(false);
  };

  return (
    <AnimatePresence>
      {showPrompt && (
        <motion.div
          className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:max-w-sm z-50"
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
        >
          <div className="bg-bg-elevated border border-border-primary rounded-lg shadow-xl p-4">
            <div className="flex items-start gap-3">
              {/* App icon */}
              <div className="w-12 h-12 rounded-lg bg-accent/20 flex items-center justify-center text-2xl flex-shrink-0">
                🎓
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-text-primary">
                  Cài đặt AetherTutor
                </h3>
                <p className="text-sm text-text-secondary mt-1">
                  Truy cập nhanh từ màn hình chính, hoạt động offline
                </p>

                {/* Actions */}
                <div className="flex gap-2 mt-3">
                  <button
                    className="flex-1 px-3 py-1.5 bg-accent text-white text-sm rounded-lg hover:bg-accent/90"
                    onClick={handleInstall}
                  >
                    Cài đặt
                  </button>
                  <button
                    className="px-3 py-1.5 text-text-secondary text-sm rounded-lg hover:bg-bg-secondary"
                    onClick={handleDismiss}
                  >
                    Sau
                  </button>
                </div>
              </div>

              {/* Close button */}
              <button
                className="text-text-secondary hover:text-text-primary"
                onClick={handleDismiss}
                aria-label="Đóng"
              >
                ✕
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
