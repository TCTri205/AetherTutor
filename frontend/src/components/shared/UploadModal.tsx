import { useState, useRef } from 'react';
import {
  Upload,
  X,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '../ui/Dialog';
import { Button } from '../ui/Button';
import { documentService } from '../../services/documents';
import { useDocumentStore } from '../../store/document';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { ApiError } from '../../services/api';
import { ErrorCode, isNetworkError } from '../../types/errors';

interface UploadModalProps {
  open: boolean;
  setOpen: (open: boolean) => void;
}

// 50MB in bytes
const MAX_FILE_SIZE = 50 * 1024 * 1024;

export default function UploadModal({ open, setOpen }: UploadModalProps) {
  const { fetchDocuments } = useDocumentStore();
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      
      // Validate file type
      if (selectedFile.type !== 'application/pdf') {
        toast.error('Chỉ hỗ trợ tệp định dạng PDF');
        return;
      }
      
      // S8.1b: Validate file size (50MB limit)
      if (selectedFile.size > MAX_FILE_SIZE) {
        toast.error(
          `File quá lớn (${(selectedFile.size / 1024 / 1024).toFixed(1)}MB). Giới hạn tối đa 50MB.`,
          { duration: 5000 }
        );
        return;
      }
      
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    try {
      const response = await documentService.uploadDocument(file);

      if (response.status === 'COMPLETED') {
        toast.info('Tài liệu đã tồn tại và đã được xử lý xong.');
      } else {
        toast.success('Đã tải lên thành công. Quá trình phân tích tri thức đang bắt đầu.');
      }

      fetchDocuments();
      setFile(null);
      setOpen(false);
    } catch (err: any) {
      // S8.1b, S8.1c, S8.1d: Handle specific error types
      if (err instanceof ApiError) {
        switch (err.code) {
          case ErrorCode.FILE_TOO_LARGE:
            // S8.1b: File > 50MB
            toast.error(
              'File quá lớn (giới hạn 50MB). Hãy chọn file nhỏ hơn.',
              { duration: 5000 }
            );
            break;
            
          case ErrorCode.SCANNED_PDF:
            // S8.1c: Scanned PDF without text layer
            toast.error(
              'PDF này là ảnh scan — hệ thống không đọc được text. Hãy dùng file PDF có text layer.',
              { duration: 6000 }
            );
            break;
            
          case ErrorCode.INVALID_API_KEY:
            // S8.1d: Invalid API Key
            toast.error(
              'API Key không hợp lệ. Vui lòng kiểm tra cài đặt.',
              { duration: 5000 }
            );
            break;
            
          default:
            // Generic error
            toast.error(`Lỗi tải lên: ${err.message}`);
        }
      } else if (isNetworkError(err)) {
        // S8.1e: Network failure
        toast.error(
          'Mất kết nối mạng — kiểm tra lại và thử lại nhé',
          { duration: 5000 }
        );
      } else {
        // Unknown error
        toast.error(`Lỗi tải lên: ${err.message || 'Không xác định'}`);
      }
    } finally {
      setIsUploading(false);
    }
  };

  const clearSelection = () => {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold text-white tracking-tight">Tải lên tri thức</DialogTitle>
          <DialogDescription>
            Chúng tôi sẽ xây dựng đồ thị tri thức từ tài liệu PDF của bạn.
          </DialogDescription>
        </DialogHeader>

        <div 
          className={cn(
            "mt-4 border-2 border-dashed rounded-3xl p-10 transition-all flex flex-col items-center justify-center gap-4 text-center cursor-pointer group",
            file ? "border-primary/50 bg-primary/5" : "border-white/10 hover:border-primary/30 hover:bg-white/5"
          )}
          onClick={() => !file && fileInputRef.current?.click()}
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            className="hidden" 
            accept=".pdf" 
            onChange={handleFileChange} 
          />

          {file ? (
            <div className="flex flex-col items-center gap-4 w-full">
              <div className="w-16 h-16 rounded-2xl bg-primary/20 flex items-center justify-center relative">
                 <FileText className="w-8 h-8 text-primary" />
                 <button 
                  onClick={(e) => { e.stopPropagation(); clearSelection(); }}
                  className="absolute -top-2 -right-2 p-1 rounded-full bg-background border border-border text-muted-foreground hover:text-white"
                 >
                   <X className="w-3 h-3" />
                 </button>
              </div>
              <div className="flex flex-col gap-1 w-full overflow-hidden">
                <span className="font-bold text-white truncate px-4">{file.name}</span>
                <span className="text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
              </div>
            </div>
          ) : (
            <>
              <div className="w-16 h-16 rounded-3xl bg-white/5 flex items-center justify-center group-hover:bg-primary/20 transition-all duration-500 group-hover:scale-110">
                <Upload className="w-8 h-8 text-muted-foreground group-hover:text-primary transition-colors" />
              </div>
              <div className="space-y-1">
                <p className="font-bold text-white group-hover:text-primary transition-colors">Nhấp để chọn tệp PDF</p>
                <p className="text-xs text-muted-foreground">Giới hạn tệp tối đa 50MB</p>
              </div>
            </>
          )}
        </div>

        <DialogFooter className="mt-8">
           <Button variant="ghost" onClick={() => setOpen(false)} disabled={isUploading} className="rounded-xl">Hủy</Button>
           <Button 
            disabled={!file || isUploading} 
            onClick={handleUpload}
            className="rounded-xl px-8 min-w-[120px] shadow-lg shadow-primary/20"
           >
             {isUploading ? (
               <Loader2 className="w-4 h-4 animate-spin mr-2" />
             ) : (
               <ArrowRight className="w-4 h-4 mr-2" />
             )}
             {isUploading ? 'Đang tải lên...' : 'Bắt đầu xử lý'}
           </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
