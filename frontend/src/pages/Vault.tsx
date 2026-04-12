import '../styles/tokens.css';
import { useEffect, useState, useMemo } from 'react';
import {
  Search,
  Filter,
  Trash2,
  ExternalLink,
  RefreshCcw,
  FileIcon,
  CheckCircle2,
  AlertCircle,
  Clock,
  MoreVertical,
  Plus,
  MessageSquare,
  Share2,
  Database
} from 'lucide-react';
import { useDocumentStore } from '../store/document';
import { documentService } from '../services/documents';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent } from '../components/ui/Card';
import { Skeleton } from '../components/ui/Skeleton';
import { cn } from '../lib/utils';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';
import { useNavigate } from 'react-router-dom';
import UploadModal from '../components/shared/UploadModal';
import { ApiError } from '../services/api';
import { isNetworkError } from '../types/errors';

export default function Vault() {
  const navigate = useNavigate();
  const { documents, fetchDocuments, removeDocument, isLoading } = useDocumentStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'COMPLETED' | 'PROCESSING' | 'FAILED'>('ALL');
  const [isUploadOpen, setIsUploadOpen] = useState(false);

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

  const filteredDocs = useMemo(() => {
    return documents.filter((doc) => {
      const matchesSearch = doc.filename.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'ALL' || doc.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [documents, searchTerm, statusFilter]);

  const handleDelete = async (id: string) => {
    if (!confirm('Bạn có chắc chắn muốn xóa tài liệu này? Mọi dữ liệu tri thức liên quan sẽ bị xóa vĩnh viễn.')) return;

    try {
      await documentService.deleteDocument(id);
      removeDocument(id);
      toast.success('Đã xóa tài liệu thành công');
    } catch (err: any) {
      // S8.1e: Handle delete errors
      if (err instanceof ApiError) {
        toast.error(`Lỗi khi xóa: ${err.message}`);
      } else if (isNetworkError(err)) {
        toast.error('Mất kết nối mạng — không thể xóa tài liệu');
      } else {
        toast.error(`Lỗi khi xóa: ${err.message}`);
      }
    }
  };

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto pb-20">
      <section className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="space-y-2">
          <h2 className="text-3xl font-bold text-primary tracking-tight">Kho Tri Thức (Vault)</h2>
          <p className="text-secondary">Quản lý và theo dõi quá trình xử lý tài liệu của bạn.</p>
        </div>
        <Button size="lg" className="rounded-2xl gap-2" onClick={() => setIsUploadOpen(true)}>
          <Plus className="w-5 h-5" />
          Tải tài liệu mới
        </Button>
      </section>

      {/* Upload Modal integration */}
      <UploadModal open={isUploadOpen} setOpen={setIsUploadOpen} />

      {/* Filters & Actions */}
      <div className="flex flex-col md:flex-row gap-4 bg-secondary p-4 rounded-2xl border border-border-primary glass">
        <div className="relative flex-1 group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary group-focus-within:text-primary transition-colors" />
          <input
            type="text"
            placeholder="Tìm kiếm tài liệu..."
            className="w-full bg-background border border-border rounded-xl px-10 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        
        <div className="flex items-center gap-2 overflow-x-auto pb-2 md:pb-0 scrollbar-hide">
          <Badge 
            variant={statusFilter === 'ALL' ? 'default' : 'outline'} 
            className="cursor-pointer px-4 py-1.5 rounded-full"
            onClick={() => setStatusFilter('ALL')}
          >
            Tất cả ({documents.length})
          </Badge>
          <Badge 
            variant={statusFilter === 'COMPLETED' ? 'success' : 'outline'} 
            className="cursor-pointer px-4 py-1.5 rounded-full"
            onClick={() => setStatusFilter('COMPLETED')}
          >
            Hoàn tất
          </Badge>
          <Badge 
            variant={statusFilter === 'PROCESSING' ? 'secondary' : 'outline'} 
            className="cursor-pointer px-4 py-1.5 rounded-full"
            onClick={() => setStatusFilter('PROCESSING')}
          >
            Đang xử lý
          </Badge>
          <Badge 
            variant={statusFilter === 'FAILED' ? 'destructive' : 'outline'} 
            className="cursor-pointer px-4 py-1.5 rounded-full"
            onClick={() => setStatusFilter('FAILED')}
          >
            Lỗi
          </Badge>
        </div>

        <Button variant="ghost" size="icon" onClick={() => fetchDocuments()} disabled={isLoading} className="rounded-xl">
           <RefreshCcw className={cn("w-4 h-4", isLoading && "animate-spin")} />
        </Button>
      </div>

      {/* Document Grid/List */}
      <div className="grid grid-cols-1 gap-4">
        {isLoading && documents.length === 0 ? (
          Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-2xl" />
          ))
        ) : filteredDocs.length > 0 ? (
          filteredDocs.map((doc) => (
            <Card key={doc.id} className="hover:border-primary/20 transition-all group overflow-hidden border-border-primary">
              <CardContent className="p-0">
                <div className="flex flex-col md:flex-row items-center gap-6 p-5">
                   <div className="w-14 h-14 rounded-2xl bg-primary/5 border border-primary/10 flex items-center justify-center shrink-0 group-hover:bg-primary/10 transition-colors">
                      <FileIcon className="w-7 h-7 text-secondary group-hover:text-primary transition-all" />
                   </div>

                   <div className="flex-1 min-w-0 space-y-1 text-center md:text-left w-full">
                      <h4 className="font-bold text-primary leading-tight truncate">{doc.filename}</h4>
                      <div className="flex flex-wrap items-center justify-center md:justify-start gap-4 text-xs text-secondary font-semibold uppercase tracking-wider">
                         <span className="flex items-center gap-1.5">
                            <Clock className="w-3.5 h-3.5" />
                            {formatDistanceToNow(new Date(doc.created_at), { locale: vi })}
                         </span>
                         {doc.entity_count > 0 && (
                           <span className="flex items-center gap-1.5">
                              <Database className="w-3.5 h-3.5 text-emerald-500" />
                              {doc.entity_count} Thực thể
                           </span>
                         )}
                         {doc.file_size && (
                            <span>{(doc.file_size / 1024 / 1024).toFixed(2)} MB</span>
                         )}
                      </div>
                   </div>

                   <div className="flex items-center gap-3 shrink-0">
                      <div className="flex flex-col items-end gap-1.5 mr-2 hidden md:flex">
                         <Badge variant={doc.status === 'COMPLETED' ? 'success' : doc.status === 'FAILED' ? 'destructive' : 'secondary'} className="rounded-md">
                            {doc.status}
                         </Badge>
                         {doc.status === 'PROCESSING' && (
                           <span className="text-[10px] font-bold text-primary animate-pulse">{doc.processing_step}</span>
                         )}
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Button 
                          variant="secondary" 
                          size="icon" 
                          className="rounded-xl h-10 w-10 hover:bg-primary/20 hover:text-primary transition-all"
                          disabled={doc.status !== 'COMPLETED'}
                          onClick={() => navigate(`/chat/${doc.id}`)}
                        >
                          <MessageSquare className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="secondary" 
                          size="icon" 
                          className="rounded-xl h-10 w-10 hover:bg-emerald-500/20 hover:text-emerald-500 transition-all"
                          disabled={doc.status !== 'COMPLETED'}
                          onClick={() => navigate(`/graph/${doc.id}`)}
                        >
                          <Share2 className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="rounded-xl h-10 w-10 text-destructive/70 hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => handleDelete(doc.id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                   </div>
                </div>
                {/* Visual Progress bar for processing docs */}
                {doc.status === 'PROCESSING' && (
                   <div className="w-full h-1 bg-secondary overflow-hidden">
                      <div className="h-full bg-primary animate-progress-indeterminate rounded-full" />
                   </div>
                )}
              </CardContent>
            </Card>
          ))
        ) : (
          <div className="flex flex-col items-center justify-center py-20 bg-secondary border-2 border-dashed border-border-primary rounded-3xl gap-6">
             <div className="w-20 h-20 rounded-full bg-tertiary flex items-center justify-center border border-border-primary">
                <Search className="w-10 h-10 text-tertiary opacity-30" />
             </div>
             <div className="text-center space-y-2">
                <p className="text-primary font-bold text-lg">Không tìm thấy tài liệu phù hợp</p>
                <p className="text-secondary">Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm của bạn.</p>
             </div>
             <Button variant="outline" onClick={() => {setSearchTerm(''); setStatusFilter('ALL')}}>Xóa bộ lọc</Button>
          </div>
        )}
      </div>
    </div>
  );
}
