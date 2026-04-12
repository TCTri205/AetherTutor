/**
 * PresenceIndicator — Hiển thị users đang online trong shared graph.
 *
 * Features:
 * - Avatar stack với online users
 * - Tooltip hiển thị tên user
 * - Pulse animation cho active users
 * - Responsive: thu gọn khi nhiều users
 */
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface WSUser {
  user_id: string;
  metadata?: {
    cursor?: { x: number; y: number };
    name?: string;
    avatar?: string;
  };
}

interface PresenceIndicatorProps {
  users: WSUser[];
  maxVisible?: number;
  className?: string;
}

// Color palette cho avatars
const AVATAR_COLORS = [
  "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
  "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16",
];

function getAvatarColor(userId: string): string {
  const index = userId.charCodeAt(0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[index];
}

function getInitials(name?: string): string {
  if (!name) return "?";
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export function PresenceIndicator({
  users,
  maxVisible = 5,
  className = "",
}: PresenceIndicatorProps) {
  const [showTooltip, setShowTooltip] = useState<string | null>(null);

  if (!users || users.length === 0) {
    return (
      <div className={`flex items-center gap-2 text-sm text-text-secondary ${className}`}>
        <div className="w-2 h-2 rounded-full bg-gray-400" />
        <span>Không có người dùng nào đang online</span>
      </div>
    );
  }

  const visibleUsers = users.slice(0, maxVisible);
  const remainingCount = users.length - maxVisible;

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Online count badge */}
      <div className="flex items-center gap-1.5">
        <motion.div
          className="w-2 h-2 rounded-full bg-green-500"
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        <span className="text-sm text-text-secondary">
          {users.length} đang online
        </span>
      </div>

      {/* Avatar stack */}
      <div className="flex -space-x-2">
        <AnimatePresence>
          {visibleUsers.map((user) => {
            const color = getAvatarColor(user.user_id);
            const initials = getInitials(user.metadata?.name);
            const userIdShort = user.user_id.slice(0, 8);

            return (
              <motion.div
                key={user.user_id}
                className="relative"
                initial={{ scale: 0, x: -20 }}
                animate={{ scale: 1, x: 0 }}
                exit={{ scale: 0, x: 20 }}
                transition={{ duration: 0.2 }}
                onMouseEnter={() => setShowTooltip(user.user_id)}
                onMouseLeave={() => setShowTooltip(null)}
              >
                <div
                  className="w-8 h-8 rounded-full border-2 border-bg-elevated flex items-center justify-center text-white text-xs font-bold cursor-pointer"
                  style={{ backgroundColor: color }}
                >
                  {initials}
                </div>

                {/* Active indicator */}
                <motion.div
                  className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-green-500 border-2 border-bg-elevated"
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />

                {/* Tooltip */}
                {showTooltip === user.user_id && (
                  <motion.div
                    className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-bg-overlay text-text-primary text-xs rounded whitespace-nowrap z-10"
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    {user.metadata?.name || userIdShort}
                    <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 w-2 h-2 bg-bg-overlay rotate-45" />
                  </motion.div>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Remaining count */}
        {remainingCount > 0 && (
          <div className="w-8 h-8 rounded-full border-2 border-bg-elevated bg-bg-secondary flex items-center justify-center text-text-secondary text-xs font-bold">
            +{remainingCount}
          </div>
        )}
      </div>
    </div>
  );
}
