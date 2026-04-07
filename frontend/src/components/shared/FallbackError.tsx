import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface FallbackErrorProps {
  error: Error | null;
  onRetry?: () => void;
  onGoHome?: () => void;
}

/**
 * Default fallback error UI when ErrorBoundary catches an error.
 * Displays error message with retry and go home actions.
 */
export const FallbackError: React.FC<FallbackErrorProps> = ({
  error,
  onRetry,
  onGoHome,
}) => {
  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    } else {
      window.location.reload();
    }
  };

  const handleGoHome = () => {
    if (onGoHome) {
      onGoHome();
    } else {
      window.location.href = '/dashboard';
    }
  };

  return (
    <div className="error-fallback">
      <div className="error-fallback-content">
        <div className="error-icon">
          <AlertTriangle size={48} />
        </div>
        
        <h2 className="error-title">Đã xảy ra lỗi</h2>
        
        <p className="error-message">
          Có lỗi không mong muốn xảy ra. Vui lòng thử lại hoặc quay về Dashboard.
        </p>
        
        {error && import.meta.env.DEV && (
          <details className="error-details">
            <summary>Chi tiết lỗi (Development)</summary>
            <pre className="error-stack">{error.message}</pre>
            {error.stack && <pre className="error-stack">{error.stack}</pre>}
          </details>
        )}
        
        <div className="error-actions">
          <button className="btn btn-primary btn-retry" onClick={handleRetry}>
            <RefreshCw size={16} />
            Thử lại
          </button>
          
          <button className="btn btn-secondary btn-home" onClick={handleGoHome}>
            <Home size={16} />
            Về Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};

export default FallbackError;
