import { useState, useEffect } from 'react';
import { 
  Users, 
  Plus, 
  Trash2, 
  Check, 
  X, 
  Lightbulb, 
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { toast } from 'sonner';
import { graphService } from '../../services/graph';
import api from '../../services/api';
import { cn } from '../../lib/utils';

interface Alias {
  alias_name: string;
  canonical_name: string;
  confidence: number;
  source: string;
  created_at: string;
}

interface Suggestion {
  alias_name: string;
  suggested_canonical: string;
  reason: string;
}

export default function AliasManager() {
  const [aliases, setAliases] = useState<Alias[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'current' | 'suggestions'>('current');
  
  // Form state
  const [newAlias, setNewAlias] = useState('');
  const [newCanonical, setNewCanonical] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  const fetchAliases = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/graph/entities/aliases');
      setAliases(response.data.aliases);
    } catch (err) {
      toast.error('Không thể tải danh sách bí danh');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchSuggestions = async () => {
    setIsLoading(true);
    try {
      const response = await api.post('/graph/entities/suggest-aliases');
      setSuggestions(response.data.suggestions);
    } catch (err) {
      toast.error('Không thể tải đề xuất');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'current') fetchAliases();
    else fetchSuggestions();
  }, [activeTab]);

  const handleCreateAlias = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAlias || !newCanonical) return;
    
    setIsAdding(true);
    try {
      await api.post('/graph/entities/create-alias', {
        alias_name: newAlias,
        canonical_name: newCanonical,
        source: 'manual'
      });
      toast.success(`Đã tạo bí danh: ${newAlias} -> ${newCanonical}`);
      setNewAlias('');
      setNewCanonical('');
      fetchAliases();
    } catch (err: any) {
      toast.error(`Lỗi: ${err.response?.data?.detail || 'Không thể tạo bí danh'}`);
    } finally {
      setIsAdding(false);
    }
  };

  const handleAcceptSuggestion = async (suggestion: Suggestion) => {
    try {
      await api.post('/graph/entities/create-alias', {
        alias_name: suggestion.alias_name,
        canonical_name: suggestion.suggested_canonical,
        source: 'ai_suggested'
      });
      toast.success('Đã chấp nhận đề xuất');
      fetchSuggestions();
    } catch (err) {
      toast.error('Lỗi khi chấp nhận đề xuất');
    }
  };

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex p-1 bg-white/5 rounded-xl border border-white/10 max-w-fit">
        <button
          onClick={() => setActiveTab('current')}
          className={cn(
            "px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-2",
            activeTab === 'current' ? "bg-primary text-white shadow-lg" : "text-muted-foreground hover:text-white"
          )}
        >
          <ShieldCheck className="w-4 h-4" />
          Bí danh hiện tại
        </button>
        <button
          onClick={() => setActiveTab('suggestions')}
          className={cn(
            "px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-2",
            activeTab === 'suggestions' ? "bg-primary text-white shadow-lg" : "text-muted-foreground hover:text-white"
          )}
        >
          <Lightbulb className="w-4 h-4" />
          Đề xuất từ AI
          {suggestions.length > 0 && (
            <span className="bg-white/20 px-1.5 py-0.5 rounded text-[10px]">{suggestions.length}</span>
          )}
        </button>
      </div>

      {activeTab === 'current' ? (
        <div className="space-y-4">
          {/* Manual Entry */}
          <Card className="glass border-white/10 p-4">
            <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-4 flex items-center gap-2">
              <Plus className="w-4 h-4 text-primary" />
              Thêm bí danh mới
            </h4>
            <form onSubmit={handleCreateAlias} className="flex gap-3">
              <input
                type="text"
                placeholder="Tên bí danh (ví dụ: AI)"
                value={newAlias}
                onChange={(e) => setNewAlias(e.target.value)}
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <ArrowRight className="w-5 h-5 text-muted-foreground self-center" />
              <input
                type="text"
                placeholder="Thực thể chuẩn (ví dụ: Artificial Intelligence)"
                value={newCanonical}
                onChange={(e) => setNewCanonical(e.target.value)}
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <Button type="submit" disabled={isAdding || !newAlias || !newCanonical}>
                {isAdding ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Thêm'}
              </Button>
            </form>
          </Card>

          {/* List */}
          <div className="space-y-2">
            {isLoading ? (
              <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
            ) : aliases.length > 0 ? (
              aliases.map((alias, idx) => (
                <Card key={idx} className="glass border-white/5 hover:border-white/20 p-4 transition-all flex items-center justify-between group">
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm font-bold text-white">{alias.alias_name}</p>
                      <Badge variant="outline" className="text-[9px] uppercase tracking-tighter opacity-50">Alias</Badge>
                    </div>
                    <ArrowRight className="w-4 h-4 text-primary" />
                    <div>
                      <p className="text-sm font-bold text-primary">{alias.canonical_name}</p>
                      <Badge variant="outline" className="text-[9px] uppercase tracking-tighter text-primary/70">Canonical</Badge>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right hidden sm:block">
                      <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Nguồn: {alias.source}</p>
                      <p className="text-[10px] text-muted-foreground">{new Date(alias.created_at).toLocaleDateString()}</p>
                    </div>
                    <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-rose-400 group-hover:opacity-100 opacity-0 transition-opacity">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </Card>
              ))
            ) : (
              <div className="text-center p-12 glass rounded-3xl border border-dashed border-white/10">
                <Users className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
                <p className="text-muted-foreground">Chưa có bí danh nào được thiết lập.</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="p-4 bg-primary/10 border border-primary/20 rounded-2xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <p className="text-xs text-primary/90 leading-relaxed">
              Dưới đây là các thực thể có tên tương tự nhau mà AI phát hiện được. 
              Gộp chúng lại giúp đồ thị tri thức của bạn sạch sẽ và chính xác hơn.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {isLoading ? (
              <div className="col-span-2 flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
            ) : suggestions.length > 0 ? (
              suggestions.map((suggestion, idx) => (
                <Card key={idx} className="glass border-white/10 p-5 hover:border-primary/30 transition-all flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                       <span className="text-sm font-bold text-white">{suggestion.alias_name}</span>
                       <ArrowRight className="w-3.5 h-3.5 text-primary" />
                       <span className="text-sm font-bold text-primary">{suggestion.suggested_canonical}</span>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground italic leading-relaxed">
                    "{suggestion.reason || 'AI phát hiện hai thực thể này thực chất là một khái niệm.'}"
                  </p>
                  <div className="flex gap-2 pt-2">
                    <Button 
                      variant="default" 
                      className="flex-1 gap-2"
                      onClick={() => handleAcceptSuggestion(suggestion)}
                    >
                      <Check className="w-4 h-4" /> Chấp nhận
                    </Button>
                    <Button variant="ghost" className="flex-1 gap-2 border border-white/10">
                      <X className="w-4 h-4" /> Từ chối
                    </Button>
                  </div>
                </Card>
              ))
            ) : (
              <div className="col-span-2 text-center p-12 glass rounded-3xl border border-dashed border-white/10">
                <Lightbulb className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
                <p className="text-muted-foreground">Hiện không có đề xuất mới nào.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
