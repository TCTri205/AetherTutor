import { type ReactNode, useEffect, useState } from 'react';
import { useParams, Navigate, Link } from 'react-router-dom';
import { useDocumentStore } from '../../store/document';
import { usePolling } from '../../hooks/usePolling';
import { Loader2, AlertCircle, ArrowLeft, FileClock, FileX, Scan, KeyRound } from 'lucide-react';
import { ErrorCode } from '../../types/errors';

interface DocumentGuardProps {
  children: ReactNode;
}

export default function DocumentGuard({ children }: DocumentGuardProps) {
  const { documentId } = useParams<{ documentId: string }>();
  const { documents, isLoading: isStoreLoading } = useDocumentStore();
  const [isInitialLoading, setIsInitialLoading] = useState(true);

  // Use polling to keep document status updated
  usePolling(documentId);

  const doc = documents.find((d) => d.id === documentId);

  useEffect(() => {
    if (!isStoreLoading) {
      setIsInitialLoading(false);
    }
  }, [isStoreLoading]);

  if (!documentId) {
    return <Navigate to="/vault" replace />;
  }

  // Initial loading state while we fetch the document list the first time
  if (isInitialLoading && !doc) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
        <p className="text-muted-foreground animate-pulse">Đang kiểm tra tài liệu...</p>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-6 text-center max-w-md mx-auto">
        <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center">
            <AlertCircle className="w-8 h-8 text-destructive" />
        </div>
        <div className="space-y-2">
            <h3 className="text-xl font-bold text-white">Không tìm thấy tài liệu</h3>
            <p className="text-muted-foreground">Tài liệu bạn yêu cầu không tồn tại hoặc đã bị xóa khỏi hệ thống.</p>
        </div>
        <Link to="/vault" className="flex items-center gap-2 px-4 py-2 bg-secondary rounded-xl hover:bg-secondary/80 transition-colors">
            <ArrowLeft className="w-4 h-4" />
            Quay lại Vault
        </Link>
      </div>
    );
  }

  if (doc.status === 'FAILED') {
    // Determine error type from error_message
    const errorMessage = doc.error_message || '';
    let errorIcon = <AlertCircle className="w-8 h-8 text-destructive" />;
    let errorTitle = 'Xử lý thất bại';
    let errorDescription = 'Đã có lỗi xảy ra trong quá trình phân tích tài liệu này.';
    
    // S8.1b, S8.1c, S8.1d: Detect specific error types
    if (errorMessage.toLowerCase().includes('quá lớn') || errorMessage.toLowerCase().includes('file too large')) {
      // S8.1b: File too large
      errorIcon = <FileX className="w-8 h-8 text-destructive" />;
      errorTitle = 'File quá lớn';
      errorDescription = errorMessage || 'File vượt giới hạn 50MB. Vui lòng nén file hoặc chọn file nhỏ hơn.';
    } else if (errorMessage.toLowerCase().includes('scan') || errorMessage.toLowerCase().includes('no text')) {
      // S8.1c: Scanned PDF
      errorIcon = <Scan className="w-8 h-8 text-destructive" />;
      errorTitle = 'PDF không thể đọc';
      errorDescription = errorMessage || 'PDF này là ảnh scan — hệ thống không đọc được text. Hãy dùng file PDF có text layer.';
    } else if (errorMessage.toLowerCase().includes('api key') || errorMessage.toLowerCase().includes('unauthorized')) {
      // S8.1d: Invalid API Key
      errorIcon = <KeyRound className="w-8 h-8 text-destructive" />;
      errorTitle = 'API Key không hợp lệ';
      errorDescription = errorMessage || 'API Key không hợp lệ. Vui lòng kiểm tra cài đặt.';
    }
    
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-6 text-center max-w-md mx-auto">
        <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center">
            {errorIcon}
        </div>
        <div className="space-y-2">
            <h3 className="text-xl font-bold text-white">{errorTitle}</h3>
            <p className="text-muted-foreground">{errorDescription}</p>
            {doc.error_message && (
                <div className="mt-4 p-3 bg-destructive/5 border border-destructive/10 rounded-lg text-xs text-destructive text-left overflow-auto max-h-32">
                    {doc.error_message}
                </div>
            )}
        </div>
        <Link to="/vault" className="px-4 py-2 bg-primary text-primary-foreground rounded-xl font-bold">
            Thử lại với tài liệu khác
        </Link>
      </div>
    );
  }

  if (doc.status !== 'COMPLETED') {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-8 text-center max-w-lg mx-auto">
        <div className="relative">
            <div className="w-24 h-24 rounded-3xl bg-primary/10 flex items-center justify-center animate-pulse">
                <FileClock className="w-12 h-12 text-primary" />
            </div>
            <div className="absolute -bottom-2 -right-2 bg-background p-1 rounded-full border border-border">
                <Loader2 className="w-6 h-6 text-primary animate-spin" />
            </div>
        </div>
        
        <div className="space-y-4">
            <h3 className="text-2xl font-bold text-white tracking-tight">Đang phân tích tri thức...</h3>
            <p className="text-muted-foreground">Vui lòng đợi trong giây lát. Chúng tôi đang xây dựng đồ thị tri thức từ tài liệu của bạn.</p>
            
            <div className="mt-8 space-y-2">
                <div className="flex justify-between text-xs font-semibold uppercase tracking-widest text-primary">
                    <span>{doc.processing_step}</span>
                    <span>{doc.status}</span>
                </div>
                <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full bg-primary animate-progress-indeterminate" />
                </div>
            </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
