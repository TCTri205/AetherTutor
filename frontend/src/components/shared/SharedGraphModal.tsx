/**
 * SharedGraphModal — Modal để share graph với team và quản lý permissions.
 *
 * Features:
 * - Chọn team để share
 * - Set permission level (view/edit/admin)
 * - Danh sách "Shared with me"
 * - Revoke access
 */
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";

interface SharedGraphModalProps {
  isOpen: boolean;
  onClose: () => void;
  graphId: string;
  token: string;
}

interface Team {
  id: string;
  name: string;
  description?: string;
  my_role: string;
  member_count: number;
}

type Permission = "view" | "edit" | "admin";

export function SharedGraphModal({
  isOpen,
  onClose,
  graphId,
  token,
}: SharedGraphModalProps) {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<string>("");
  const [permission, setPermission] = useState<Permission>("view");
  const [activeTab, setActiveTab] = useState<"share" | "shared">("share");

  // Fetch user's teams
  useEffect(() => {
    if (isOpen && activeTab === "share") {
      fetchTeams();
    }
  }, [isOpen, activeTab]);

  const fetchTeams = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/collaboration/teams", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch teams");
      const data = await res.json();
      setTeams(data.teams || []);
    } catch (err) {
      console.error(err);
      toast.error("Không thể tải danh sách teams");
    } finally {
      setLoading(false);
    }
  };

  const handleShare = async () => {
    if (!selectedTeam) {
      toast.error("Vui lòng chọn team");
      return;
    }

    try {
      const res = await fetch(`/api/v1/collaboration/teams/${selectedTeam}/share`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          resource_type: "graph",
          resource_id: graphId,
          permission,
        }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to share");
      }

      toast.success("Đã chia sẻ graph với team");
      onClose();
    } catch (err: any) {
      toast.error(err.message || "Lỗi khi chia sẻ");
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-bg-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className="w-full max-w-2xl mx-4 bg-bg-elevated rounded-lg shadow-xl"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border-primary">
              <h2 className="text-xl font-semibold text-text-primary">
                Chia sẻ Graph
              </h2>
              <button
                onClick={onClose}
                className="text-text-secondary hover:text-text-primary transition-colors"
                aria-label="Đóng"
              >
                ✕
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-border-primary">
              <button
                className={`flex-1 py-2 px-4 text-sm font-medium transition-colors ${
                  activeTab === "share"
                    ? "text-accent border-b-2 border-accent"
                    : "text-text-secondary hover:text-text-primary"
                }`}
                onClick={() => setActiveTab("share")}
              >
                Chia sẻ với team
              </button>
              <button
                className={`flex-1 py-2 px-4 text-sm font-medium transition-colors ${
                  activeTab === "shared"
                    ? "text-accent border-b-2 border-accent"
                    : "text-text-secondary hover:text-text-primary"
                }`}
                onClick={() => setActiveTab("shared")}
              >
                Được chia sẻ với tôi
              </button>
            </div>

            {/* Content */}
            <div className="p-6 max-h-96 overflow-y-auto">
              {activeTab === "share" ? (
                <div className="space-y-4">
                  {/* Team selector */}
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-2">
                      Chọn team
                    </label>
                    {loading ? (
                      <div className="text-text-secondary">Đang tải...</div>
                    ) : teams.length === 0 ? (
                      <div className="text-text-secondary text-sm">
                        Bạn chưa tham gia team nào.{" "}
                        <button className="text-accent hover:underline">
                          Tạo team mới
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {teams.map((team) => (
                          <button
                            key={team.id}
                            className={`w-full p-3 rounded-lg border-2 transition-all text-left ${
                              selectedTeam === team.id
                                ? "border-accent bg-accent/10"
                                : "border-border-primary hover:border-accent/50"
                            }`}
                            onClick={() => setSelectedTeam(team.id)}
                          >
                            <div className="font-medium text-text-primary">
                              {team.name}
                            </div>
                            <div className="text-sm text-text-secondary">
                              {team.member_count} thành viên • Quyền: {team.my_role}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Permission selector */}
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-2">
                      Quyền hạn
                    </label>
                    <div className="flex gap-2">
                      {(["view", "edit", "admin"] as Permission[]).map((perm) => (
                        <button
                          key={perm}
                          className={`flex-1 py-2 px-4 rounded-lg border-2 transition-all capitalize ${
                            permission === perm
                              ? "border-accent bg-accent/10 text-accent"
                              : "border-border-primary text-text-secondary hover:border-accent/50"
                          }`}
                          onClick={() => setPermission(perm)}
                        >
                          {perm === "view" && "👁️ Xem"}
                          {perm === "edit" && "✏️ Sửa"}
                          {perm === "admin" && "👑 Admin"}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Share button */}
                  <button
                    className="w-full py-2 px-4 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={handleShare}
                    disabled={!selectedTeam || loading}
                  >
                    Chia sẻ
                  </button>
                </div>
              ) : (
                <div className="text-center py-8 text-text-secondary">
                  <div className="text-4xl mb-4">📂</div>
                  <p>Chức năng đang phát triển</p>
                  <p className="text-sm mt-2">
                    Danh sách graphs được chia sẻ với bạn sẽ hiển thị ở đây
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
