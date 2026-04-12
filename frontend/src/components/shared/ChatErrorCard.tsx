import '../../styles/tokens.css';
import React from 'react';
import { AlertTriangle, RefreshCw, Settings, WifiOff, Clock } from 'lucide-react';
import { Button } from '../ui/Button';
import { ErrorCode, isRetryable } from '../../types/errors';
import type { ChatErrorState, ErrorAction } from '../../types/errors';
import { cn } from '../../lib/utils';

interface ChatErrorCardProps {
  error: ChatErrorState;
  onRetry?: () => void;
  onGoToSettings?: () => void;
  onSwitchToLocalMode?: () => void;
  className?: string;
}

/**
 * Chat Error Card - Hiển thị lỗi trong chat với actions phù hợp.
 * Supports: S8.1a (LLM Timeout), S8.1d (Invalid API Key),
 *           S8.1e (Network Failure), S8.1f (AI No Response)
 */
export const ChatErrorCard: React.FC<ChatErrorCardProps> = ({
  error,
  onRetry,
  onGoToSettings,
  onSwitchToLocalMode,
  className,
}) => {
  if (!error.hasError || !error.errorCode) return null;

  const getErrorConfig = () => {
    switch (error.errorCode) {
      case ErrorCode.LLM_TIMEOUT:
        // S8.1a: LLM Timeout
        return {
          icon: <Clock size={24} />,
          title: 'AI đang bận xử lý',
          message: error.errorMessage || 'AI đang bận xử lý câu hỏi của bạn — thử lại nhé.',
          suggestion: 'Model đang quá tải hoặc kết nối chậm.',
          actions: [
            {
              type: 'RETRY',
              label: 'Thử lại',
              icon: '🔄',
              onClick: onRetry || (() => window.location.reload()),
            },
            {
              type: 'SWITCH_LOCAL_MODE',
              label: 'Dùng Local Mode',
              icon: '🔒',
              disabled: true,
              tooltip: 'Coming soon in v2',
              onClick: onSwitchToLocalMode || (() => {}),
            },
          ] as ErrorAction[],
        };

      case ErrorCode.AI_NO_RESPONSE:
        // S8.1f: AI không phản hồi sau 30s
        return {
          icon: <AlertTriangle size={24} />,
          title: '⚠️ AI không phản hồi',
          message: error.errorMessage || 'Có thể do API key không hợp lệ, mạng gián đoạn, hoặc model đang quá tải.',
          suggestion: 'Thử lại sau vài giây hoặc kiểm tra cài đặt.',
          actions: [
            {
              type: 'RETRY',
              label: 'Thử lại',
              icon: '🔄',
              onClick: onRetry || (() => window.location.reload()),
            },
            {
              type: 'GO_TO_SETTINGS',
              label: 'Kiểm tra Settings',
              icon: '⚙️',
              onClick: onGoToSettings || (() => {}),
            },
          ] as ErrorAction[],
        };

      case ErrorCode.INVALID_API_KEY:
        // S8.1d: Invalid API Key
        return {
          icon: <Settings size={24} />,
          title: 'API Key không hợp lệ',
          message: error.errorMessage || 'API Key không hợp lệ hoặc hết hạn.',
          suggestion: 'Kiểm tra file .env hoặc Settings.',
          actions: [
            {
              type: 'GO_TO_SETTINGS',
              label: 'Đi đến Settings',
              icon: '⚙️',
              onClick: onGoToSettings || (() => {}),
            },
          ] as ErrorAction[],
        };

      case ErrorCode.NETWORK_ERROR:
        // S8.1e: Network Failure
        return {
          icon: <WifiOff size={24} />,
          title: 'Mất kết nối mạng',
          message: error.errorMessage || 'Không thể kết nối đến server. Kiểm tra internet hoặc dùng Local Mode.',
          actions: [
            {
              type: 'RETRY',
              label: 'Thử lại',
              icon: '🔄',
              onClick: onRetry || (() => window.location.reload()),
            },
            {
              type: 'SWITCH_LOCAL_MODE',
              label: 'Dùng Local Mode',
              icon: '🔒',
              disabled: true,
              tooltip: 'Coming soon in v2',
              onClick: onSwitchToLocalMode || (() => {}),
            },
          ] as ErrorAction[],
        };

      default:
        // Generic error
        return {
          icon: <AlertTriangle size={24} />,
          title: 'Đã xảy ra lỗi',
          message: error.errorMessage || 'Có lỗi không mong muốn xảy ra.',
          actions: isRetryable({ code: error.errorCode })
            ? [
                {
                  type: 'RETRY',
                  label: 'Thử lại',
                  icon: '🔄',
                  onClick: onRetry || (() => window.location.reload()),
                },
              ] as ErrorAction[]
            : [],
        };
    }
  };

  const config = getErrorConfig();

  return (
    <div className={cn('chat-error-card', className)}>
      <div className="error-content">
        <div className="error-header">
          <div className="error-icon">{config.icon}</div>
          <h4 className="error-title">{config.title}</h4>
        </div>
        
        <p className="error-message">{config.message}</p>
        
        {config.suggestion && (
          <p className="error-suggestion">{config.suggestion}</p>
        )}
        
        {config.actions.length > 0 && (
          <div className="error-actions">
            {config.actions.map((action, index) => (
              <Button
                key={index}
                variant={action.type === 'RETRY' ? 'default' : 'outline'}
                onClick={action.onClick}
                disabled={action.disabled}
                title={action.tooltip}
                className={cn(
                  'error-action-btn',
                  action.type === 'RETRY' && 'retry-btn',
                  action.type === 'GO_TO_SETTINGS' && 'settings-btn'
                )}
              >
                {action.icon && <span className="action-icon">{action.icon}</span>}
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatErrorCard;
