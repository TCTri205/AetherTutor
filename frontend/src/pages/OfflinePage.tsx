/**
 * OfflinePage — Hiển thị khi không có mạng.
 *
 * Features:
 * - Thông báo offline
 * - Retry button
 * - Danh sách cached documents (tương lai)
 */
import { useState, useEffect } from "react";
import { motion } from "framer-motion";

export function OfflinePage() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (isOnline) {
    return null;
  }

  return (
    <motion.div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-bg-primary"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div className="text-center max-w-md mx-4 p-8 bg-bg-elevated rounded-lg border border-border-primary">
        {/* Offline icon */}
        <motion.div
          className="text-6xl mb-6"
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          📡
        </motion.div>

        <h1 className="text-2xl font-bold text-text-primary mb-2">
          Bạn đang offline
        </h1>
        <p className="text-text-secondary mb-6">
          Kiểm tra kết nối mạng của bạn. Một số tính năng vẫn hoạt động offline.
        </p>

        {/* Retry button */}
        <button
          className="px-6 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
          onClick={() => window.location.reload()}
        >
          Thử lại
        </button>

        {/* Cached content info */}
        <div className="mt-6 pt-6 border-t border-border-primary text-sm text-text-secondary">
          <p>💡 Mẹo:</p>
          <p>Flashcards và Notes đã xem gần đây vẫn khả dụng offline</p>
        </div>
      </div>
    </motion.div>
  );
}
