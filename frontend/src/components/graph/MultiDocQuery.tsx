import { useState } from 'react';
import { 
  Search, 
  Layers, 
  ShieldAlert, 
  ShieldCheck, 
  FileText,
  MessageSquare,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Loader2,
  BookOpen
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { toast } from 'sonner';
import api from '../../services/api';
import { cn } from '../../lib/utils';

interface MultiDocResponse {
  query: string;
  response: string;
  context_used: any[];
  cross_verification?: {
    documents_analyzed: number;
    contradictions: any[];
    consensus: any[];
    claims: any[];
  };
  documents_involved: string[];
}

export default function MultiDocQuery() {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<MultiDocResponse | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    try {
      const response = await api.post('/graph/query-multi', {
        query,
        enable_cross_verification: true,
        scope: 'user_global'
      });
      setResult(response.data);
    } catch (err) {
      toast.error('Lỗi khi thực hiện truy vấn xuyên tài liệu');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Query Form */}
      <Card className="glass border-white/10 p-6 shadow-2xl overflow-hidden relative">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary/50 via-indigo-500/50 to-primary/50"></div>
        <form onSubmit={handleQuery} className="space-y-4">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
              <Layers className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-widest">Truy vấn Đa Tài Liệu</h3>
              <p className="text-[10px] text-muted-foreground uppercase tracking-tight font-bold">Tìm kiếm & Đối chiếu thông tin trên toàn bộ thư viện</p>
            </div>
          </div>
          
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ví dụ: 'So sánh các khái niệm X giữa tài liệu A và B' hoặc 'Có mâu thuẫn gì về Y không?'"
              className="w-full bg-white/5 border border-white/10 rounded-2xl px-6 py-4 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary/50 pr-24 transition-all"
            />
            <Button 
              type="submit" 
              className="absolute right-2 top-2 h-10 gap-2"
              disabled={isLoading || !query.trim()}
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              Hỏi AI
            </Button>
          </div>
        </form>
      </Card>

      {/* Results */}
      {result && !isLoading && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Answer */}
          <Card className="glass border-white/10 p-6 bg-primary/5 relative overflow-hidden">
             <div className="absolute top-4 right-4">
                <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 gap-1.5 px-3 py-1">
                  <ShieldCheck className="w-3.5 h-3.5" /> AI Sourced
                </Badge>
             </div>
             <div className="space-y-4">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <MessageSquare className="w-4 h-4" />
                  <span className="text-[10px] uppercase font-bold tracking-widest">Tổng hợp câu trả lời</span>
                </div>
                <div className="text-white text-sm leading-relaxed prose prose-invert max-w-none">
                  {result.response}
                </div>
             </div>
          </Card>

          {/* Cross-Verification & Sources */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Contradictions / Consensus */}
            <Card className="glass border-white/10 p-5 space-y-4">
              <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-2">
                <ShieldAlert className="w-3.5 h-3.5" /> Phân tích đối chiếu
              </h4>
              
              {result.cross_verification && (
                <div className="space-y-3">
                  {result.cross_verification.contradictions?.length > 0 ? (
                    <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl">
                      <p className="text-xs font-bold text-rose-400 mb-1">Cảnh báo mâu thuẫn ({result.cross_verification.contradictions.length})</p>
                      <ul className="space-y-1">
                        {result.cross_verification.contradictions.map((c, i) => (
                          <li key={i} className="text-[10px] text-rose-300/80">• {c.issue}</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center gap-3">
                      <ShieldCheck className="w-5 h-5 text-emerald-400" />
                      <div>
                        <p className="text-xs font-bold text-emerald-400">Độ đồng thuận cao</p>
                        <p className="text-[10px] text-emerald-300/60">Không phát hiện mâu thuẫn nghiêm trọng giữa các tài liệu.</p>
                      </div>
                    </div>
                  )}

                  <div className="pt-2">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2 font-bold opacity-50">Tài liệu tham chiếu</p>
                    <div className="flex flex-wrap gap-2">
                       {result.documents_involved.map(docId => (
                         <Badge key={docId} variant="secondary" className="bg-white/5 border-white/10 text-[9px] font-normal">
                           <BookOpen className="w-2.5 h-2.5 mr-1" />
                           Doc: {docId.slice(0, 8)}
                         </Badge>
                       ))}
                    </div>
                  </div>
                </div>
              )}
            </Card>

            {/* Context Snippets */}
            <Card className="glass border-white/10 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5" /> Dữ liệu nguồn
                </h4>
                <button 
                  onClick={() => setShowDetails(!showDetails)}
                  className="text-primary text-[10px] font-bold uppercase hover:underline flex items-center gap-1"
                >
                  {showDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  {showDetails ? 'Thu gọn' : 'Xem chi tiết'}
                </button>
              </div>

              <div className={cn(
                "space-y-2 overflow-hidden transition-all duration-300",
                showDetails ? "max-h-[500px] overflow-y-auto pr-2" : "max-h-24"
              )}>
                {result.context_used.map((ctx, idx) => (
                  <div key={idx} className="p-2 rounded bg-white/5 border border-white/5 text-[9px] text-muted-foreground leading-snug">
                    <span className="text-primary font-bold">[{ctx.type}]</span> {ctx.content}
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
