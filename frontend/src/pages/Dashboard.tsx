import { useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Plus,
  FileText,
  Database,
  Network,
  MessageSquare,
  ArrowRight,
  Clock,
  AlertTriangle
} from 'lucide-react';
import { useDocumentStore } from '../store/document';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';
import { ApiError } from '../services/api';
import { isNetworkError } from '../types/errors';
import { toast } from 'sonner';

export default function Dashboard() {
  const navigate = useNavigate();
  const { documents, fetchDocuments, isLoading } = useDocumentStore();

  useEffect(() => {
    // S8.1e: Handle fetch errors gracefully
    fetchDocuments().catch((err) => {
      if (err instanceof ApiError) {
        toast.error(`Lỗi tải danh sách: ${err.message}`);
      } else if (isNetworkError(err)) {
        toast.error('Mất kết nối mạng — không thể tải danh sách tài liệu');
      } else {
        toast.error('Không thể tải danh sách tài liệu');
      }
    });
  }, [fetchDocuments]);

  const recentDocs = [...documents]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  const stats = {
    totalDocs: documents.length,
    totalEntities: documents.reduce((acc, doc) => acc + (doc.entity_count || 0), 0),
    totalRelations: documents.reduce((acc, doc) => acc + (doc.relation_count || 0), 0),
  };

  return (
    <div className="flex flex-col gap-10 max-w-7xl mx-auto">
      {/* Welcome Section */}
      <section className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="space-y-2">
          <h2 className="text-4xl font-bold text-white tracking-tight">Chào buổi sáng, Tutor</h2>
          <p className="text-muted-foreground text-lg">Hôm nay bạn muốn khám phá tri thức từ tài liệu nào?</p>
        </div>
        <Button size="lg" className="rounded-2xl shadow-xl shadow-primary/20 gap-2" onClick={() => navigate('/vault')}>
          <Plus className="w-5 h-5" />
          Thêm tài liệu mới
        </Button>
      </section>

      {/* Stats Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-gradient-to-br from-blue-500/10 to-transparent border-primary/10">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-widest text-primary">Tài liệu</CardTitle>
            <FileText className="w-4 h-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.totalDocs}</div>
            <p className="text-xs text-muted-foreground mt-1">Đã được tải lên hệ thống</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-emerald-500/10 to-transparent border-emerald-500/10">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-widest text-emerald-500">Thực thể</CardTitle>
            <Database className="w-4 h-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.totalEntities}</div>
            <p className="text-xs text-muted-foreground mt-1">Đã được định danh trong đồ thị</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-500/10 to-transparent border-purple-500/10">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-widest text-purple-500">Quan hệ</CardTitle>
            <Network className="w-4 h-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.totalRelations}</div>
            <p className="text-xs text-muted-foreground mt-1">Các kết nối tri thức được tìm thấy</p>
          </CardContent>
        </Card>
      </section>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        {/* Recent Documents */}
        <section className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-white/90 flex items-center gap-3">
              <Clock className="w-5 h-5 text-primary" />
              Tài liệu gần đây
            </h3>
            <Link to="/vault" className="text-sm font-semibold text-primary hover:underline flex items-center gap-1">
              Xem tất cả
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {recentDocs.length > 0 ? (
              recentDocs.map((doc) => (
                <Card key={doc.id} className="hover:border-primary/30 transition-all group cursor-pointer" onClick={() => navigate(`/chat/${doc.id}`)}>
                  <CardContent className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center group-hover:bg-primary/10 transition-colors">
                        <FileText className="w-6 h-6 text-muted-foreground group-hover:text-primary transition-colors" />
                      </div>
                      <div className="flex flex-col">
                        <span className="font-bold text-white/90 truncate max-w-[200px] md:max-w-md">{doc.filename}</span>
                        <span className="text-xs text-muted-foreground">
                          Thêm {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true, locale: vi })}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant={doc.status === 'COMPLETED' ? 'success' : doc.status === 'FAILED' ? 'destructive' : 'secondary'}>
                        {doc.status}
                      </Badge>
                      <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-all translate-x-[-10px] group-hover:translate-x-0" />
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-20 glass rounded-3xl border-dashed border-white/10 gap-4 text-center">
                <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center">
                  <FileText className="w-8 h-8 text-muted-foreground/50" />
                </div>
                <p className="text-muted-foreground">Chưa có tài liệu nào. Hãy bắt đầu bằng cách tải lên một tệp PDF.</p>
                <Button variant="outline" onClick={() => navigate('/vault')}>Đi tới Vault</Button>
              </div>
            )}
          </div>
        </section>

        {/* Quick Actions / Activity */}
        <section className="space-y-6">
          <h3 className="text-xl font-bold text-white/90 flex items-center gap-3">
             Hành động nhanh
          </h3>
          <div className="flex flex-col gap-4">
             <Button variant="secondary" className="justify-start h-auto p-4 rounded-2xl gap-4 bg-white/5 hover:bg-white/10 transition-all border border-white/5 overflow-hidden relative group" onClick={() => navigate('/chat')}>
                <div className="absolute right-[-10%] top-[-20%] w-24 h-24 bg-primary/20 blur-3xl rounded-full group-hover:bg-primary/30 transition-all" />
                <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
                  <MessageSquare className="w-5 h-5 text-primary" />
                </div>
                <div className="flex flex-col items-start">
                   <span className="font-bold text-white">Bắt đầu hội thoại</span>
                   <span className="text-xs text-muted-foreground">Đặt câu hỏi cho Socratic Tutor</span>
                </div>
             </Button>
             
             <Button variant="secondary" className="justify-start h-auto p-4 rounded-2xl gap-4 bg-white/5 hover:bg-white/10 transition-all border border-white/5 overflow-hidden relative group" onClick={() => navigate('/graph')}>
                <div className="absolute right-[-10%] top-[-20%] w-24 h-24 bg-emerald-500/20 blur-3xl rounded-full group-hover:bg-emerald-500/30 transition-all" />
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                  <Network className="w-5 h-5 text-emerald-500" />
                </div>
                <div className="flex flex-col items-start">
                   <span className="font-bold text-white">Khám phá đồ thị</span>
                   <span className="text-xs text-muted-foreground">Xem trực quan các kết nối tri thức</span>
                </div>
             </Button>
          </div>
        </section>
      </div>
    </div>
  );
}
