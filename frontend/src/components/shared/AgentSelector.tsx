/**
 * AgentSelector — Modal chọn agent khi tạo conversation mới.
 *
 * Features:
 * - Fetch danh sách agents từ API
 * - Hiển thị icon, name, description, capabilities
 * - Filter by category/type
 * - Click để chọn agent
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';

interface AgentInfo {
  id: string;
  name: string;
  description: string;
  icon: string;
  capabilities: string[];
  enabled: boolean;
  metadata?: Record<string, any>;
}

interface AgentSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (agentId: string) => void;
}

const AGENT_ICONS: Record<string, string> = {
  language_agent: '🌍',
  math_agent: '📐',
  examiner_agent: '📝',
  visualizer_agent: '📊',
  default: '🤖',
};

export function AgentSelector({ isOpen, onClose, onSelect }: AgentSelectorProps) {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<string>('all');
  const token = localStorage.getItem('token') || '';

  useEffect(() => {
    if (isOpen) {
      fetchAgents();
    }
  }, [isOpen]);

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/agents?enabled_only=true', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to fetch agents');
      const data = await res.json();
      setAgents(data.agents || []);
    } catch (err) {
      console.error(err);
      toast.error('Không thể tải danh sách agents');
    } finally {
      setLoading(false);
    }
  };

  const filteredAgents = filter === 'all'
    ? agents
    : agents.filter(a => a.capabilities.includes(filter));

  const allCapabilities = [...new Set(agents.flatMap(a => a.capabilities))];

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
            className="w-full max-w-2xl mx-4 bg-bg-elevated rounded-lg shadow-xl border border-border-primary"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border-primary">
              <h2 className="text-xl font-semibold text-text-primary">
                Chọn AI Agent
              </h2>
              <button
                onClick={onClose}
                className="text-text-secondary hover:text-text-primary transition-colors"
                aria-label="Đóng"
              >
                ✕
              </button>
            </div>

            {/* Filter tabs */}
            <div className="flex gap-2 p-4 border-b border-border-primary overflow-x-auto">
              <button
                className={`px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  filter === 'all'
                    ? 'bg-accent/20 text-accent'
                    : 'bg-bg-secondary text-text-secondary hover:text-text-primary'
                }`}
                onClick={() => setFilter('all')}
              >
                Tất cả
              </button>
              {allCapabilities.slice(0, 6).map(cap => (
                <button
                  key={cap}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap capitalize transition-colors ${
                    filter === cap
                      ? 'bg-accent/20 text-accent'
                      : 'bg-bg-secondary text-text-secondary hover:text-text-primary'
                  }`}
                  onClick={() => setFilter(cap)}
                >
                  {cap.replace('_', ' ')}
                </button>
              ))}
            </div>

            {/* Agent grid */}
            <div className="p-4 max-h-96 overflow-y-auto">
              {loading ? (
                <div className="text-center py-8 text-text-secondary">Đang tải...</div>
              ) : filteredAgents.length === 0 ? (
                <div className="text-center py-8 text-text-secondary">
                  Không tìm thấy agent nào
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {filteredAgents.map(agent => {
                    const icon = AGENT_ICONS[agent.id] || AGENT_ICONS.default;
                    return (
                      <button
                        key={agent.id}
                        className="p-4 rounded-lg border-2 border-border-primary hover:border-accent/50 bg-bg-secondary hover:bg-bg-secondary/80 transition-all text-left group"
                        onClick={() => {
                          onSelect(agent.id);
                          onClose();
                        }}
                      >
                        <div className="flex items-start gap-3">
                          <div className="text-3xl flex-shrink-0">{icon}</div>
                          <div className="min-w-0">
                            <div className="font-semibold text-text-primary group-hover:text-accent transition-colors">
                              {agent.name}
                            </div>
                            <div className="text-sm text-text-secondary mt-1 line-clamp-2">
                              {agent.description}
                            </div>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {agent.capabilities.slice(0, 3).map(cap => (
                                <span
                                  key={cap}
                                  className="px-1.5 py-0.5 text-xs rounded bg-accent/10 text-accent capitalize"
                                >
                                  {cap.replace('_', ' ')}
                                </span>
                              ))}
                              {agent.capabilities.length > 3 && (
                                <span className="px-1.5 py-0.5 text-xs rounded bg-bg-tertiary text-text-secondary">
                                  +{agent.capabilities.length - 3}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
