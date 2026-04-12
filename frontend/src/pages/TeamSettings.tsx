/**
 * TeamSettings — Trang quản lý team (members, invites, shared resources).
 *
 * Features:
 * - Danh sách thành viên với role
 * - Invite by email
 * - Quản lý shared resources
 * - Rời team / Xóa team (owner)
 */
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { useNavigate, useParams } from "react-router-dom";

interface TeamMember {
  id: string;
  user_id: string;
  email: string;
  username?: string;
  full_name?: string;
  avatar_url?: string;
  role: "admin" | "editor" | "viewer";
  is_active: boolean;
  joined_at: string;
}

interface TeamDetails {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  max_members: number;
  my_role: string;
  created_at: string;
}

export function TeamSettings() {
  const { teamId } = useParams<{ teamId: string }>();
  const navigate = useNavigate();
  const [team, setTeam] = useState<TeamDetails | null>(null);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"viewer" | "editor" | "admin">("viewer");
  const [loading, setLoading] = useState(false);
  const token = localStorage.getItem("token") || "";

  useEffect(() => {
    if (teamId) {
      fetchTeam();
      fetchMembers();
    }
  }, [teamId]);

  const fetchTeam = async () => {
    try {
      const res = await fetch(`/api/v1/collaboration/teams/${teamId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch team");
      const data = await res.json();
      setTeam(data);
    } catch (err) {
      toast.error("Không thể tải thông tin team");
    }
  };

  const fetchMembers = async () => {
    try {
      const res = await fetch(`/api/v1/collaboration/teams/${teamId}/members`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch members");
      const data = await res.json();
      setMembers(data.members || []);
    } catch (err) {
      toast.error("Không thể tải danh sách thành viên");
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail) return;

    setLoading(true);
    try {
      const res = await fetch(`/api/v1/collaboration/teams/${teamId}/invite`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          email: inviteEmail,
          role: inviteRole,
        }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to invite");
      }

      const data = await res.json();
      toast.success(
        data.status === "added"
          ? "Đã thêm thành viên vào team"
          : `Đã gửi lời mời đến ${inviteEmail}`
      );
      setInviteEmail("");
      fetchMembers();
    } catch (err: any) {
      toast.error(err.message || "Lỗi khi gửi lời mời");
    } finally {
      setLoading(false);
    }
  };

  const handleLeaveTeam = async () => {
    if (!confirm("Bạn có chắc muốn rời team này?")) return;

    try {
      // TODO: Implement leave team endpoint
      toast.info("Chức năng đang phát triển");
    } catch (err: any) {
      toast.error(err.message || "Lỗi khi rời team");
    }
  };

  if (!team) {
    return <div className="flex items-center justify-center h-64">Đang tải...</div>;
  }

  const isOwner = team.owner_id === (localStorage.getItem("userId") || "");

  return (
    <motion.div
      className="max-w-4xl mx-auto space-y-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {/* Team header */}
      <div className="bg-bg-elevated rounded-lg p-6 border border-border-primary">
        <h1 className="text-2xl font-bold text-text-primary">{team.name}</h1>
        {team.description && (
          <p className="text-text-secondary mt-1">{team.description}</p>
        )}
        <div className="flex gap-4 mt-4 text-sm text-text-secondary">
          <span>👥 {members.length}/{team.max_members} thành viên</span>
          <span>👑 Quyền của bạn: <strong className="text-text-primary">{team.my_role}</strong></span>
        </div>
      </div>

      {/* Invite form */}
      <div className="bg-bg-elevated rounded-lg p-6 border border-border-primary">
        <h2 className="text-lg font-semibold text-text-primary mb-4">
          Mời thành viên mới
        </h2>
        <form onSubmit={handleInvite} className="space-y-4">
          <div className="flex gap-3">
            <input
              type="email"
              placeholder="Email người dùng"
              className="flex-1 px-3 py-2 rounded-lg bg-bg-secondary border border-border-primary text-text-primary"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
            />
            <select
              className="px-3 py-2 rounded-lg bg-bg-secondary border border-border-primary text-text-primary"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as any)}
            >
              <option value="viewer">👁️ Viewer</option>
              <option value="editor">✏️ Editor</option>
              <option value="admin">👑 Admin</option>
            </select>
            <button
              type="submit"
              className="px-6 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 disabled:opacity-50"
              disabled={loading || !inviteEmail}
            >
              {loading ? "Đang gửi..." : "Mời"}
            </button>
          </div>
        </form>
      </div>

      {/* Members list */}
      <div className="bg-bg-elevated rounded-lg p-6 border border-border-primary">
        <h2 className="text-lg font-semibold text-text-primary mb-4">
          Thành viên ({members.length})
        </h2>
        <div className="space-y-2">
          {members.map((member) => (
            <div
              key={member.id}
              className="flex items-center justify-between p-3 rounded-lg bg-bg-secondary"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center text-accent font-bold">
                  {member.full_name?.[0] || member.username?.[0] || member.email[0].toUpperCase()}
                </div>
                <div>
                  <div className="font-medium text-text-primary">
                    {member.full_name || member.username || member.email}
                  </div>
                  <div className="text-sm text-text-secondary">{member.email}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`px-2 py-1 rounded text-xs font-medium capitalize ${
                    member.role === "admin"
                      ? "bg-red-500/20 text-red-400"
                      : member.role === "editor"
                      ? "bg-blue-500/20 text-blue-400"
                      : "bg-green-500/20 text-green-400"
                  }`}
                >
                  {member.role}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Danger zone */}
      <div className="bg-bg-elevated rounded-lg p-6 border border-red-500/50">
        <h2 className="text-lg font-semibold text-red-400 mb-4">Vùng nguy hiểm</h2>
        <div className="flex gap-3">
          <button
            className="px-4 py-2 border border-red-500 text-red-400 rounded-lg hover:bg-red-500/10"
            onClick={handleLeaveTeam}
          >
            Rời team
          </button>
          {isOwner && (
            <button className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600">
              Xóa team
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
