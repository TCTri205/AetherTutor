/**
 * Error codes cho các loại lỗi trong ứng dụng.
 * Sử dụng để phân loại và hiển thị UI phù hợp.
 */
export const ErrorCode = {
  // Upload errors
  FILE_TOO_LARGE: 'FILE_TOO_LARGE',           // S8.1b: File >50MB
  SCANNED_PDF: 'SCANNED_PDF',                 // S8.1c: PDF không có text layer
  INVALID_FILE_FORMAT: 'INVALID_FILE_FORMAT', // File không phải PDF
  
  // LLM/Chat errors
  LLM_TIMEOUT: 'LLM_TIMEOUT',                 // S8.1a: LLM timeout (504)
  AI_NO_RESPONSE: 'AI_NO_RESPONSE',           // S8.1f: Không nhận chunk sau 30s
  INVALID_API_KEY: 'INVALID_API_KEY',         // S8.1d: API key không hợp lệ (401)
  
  // Network errors
  NETWORK_ERROR: 'NETWORK_ERROR',             // S8.1e: Mất kết nối mạng
  SERVER_ERROR: 'SERVER_ERROR',               // 500 Internal Server Error
  
  // System errors
  INVALID_RESPONSE_FORMAT: 'INVALID_RESPONSE_FORMAT', // Backend trả HTML thay vì JSON
  UNKNOWN_ERROR: 'UNKNOWN_ERROR',             // Lỗi không xác định
} as const;

export type ErrorCode = typeof ErrorCode[keyof typeof ErrorCode];

/**
 * Interface cho error message hiển thị trong UI.
 */
export interface ErrorMessage {
  code: ErrorCode;
  title: string;
  message: string;
  suggestion?: string;
  actions: ErrorAction[];
}

/**
 * Các loại action có thể thực hiện để recovery từ lỗi.
 */
export type ErrorActionType = 
  | 'RETRY'              // Thử lại
  | 'DISMISS'            // Đóng thông báo lỗi
  | 'SWITCH_LOCAL_MODE'  // Chuyển sang Local Mode (Ollama)
  | 'GO_TO_SETTINGS'     // Đi đến Settings page
  | 'DELETE';            // Xóa tài liệu

/**
 * Interface cho action button trong error UI.
 */
export interface ErrorAction {
  type: ErrorActionType;
  label: string;
  icon?: string;
  disabled?: boolean;
  tooltip?: string;
  onClick: () => void;
}

/**
 * Error state trong chat.
 */
export interface ChatErrorState {
  hasError: boolean;
  errorCode?: ErrorCode;
  errorMessage?: string;
  messageId?: string;
  timestamp: number;
}

/**
 * Error state trong document processing.
 */
export interface DocumentErrorState {
  hasError: boolean;
  errorCode?: ErrorCode;
  errorMessage?: string;
  documentId?: string;
  documentName?: string;
  timestamp: number;
}

/**
 * Helper function để tạo error message từ error code.
 */
export function getErrorMessage(code: ErrorCode, detail?: string): ErrorMessage {
  const messages: Record<ErrorCode, Omit<ErrorMessage, 'actions'>> = {
    [ErrorCode.FILE_TOO_LARGE]: {
      code: ErrorCode.FILE_TOO_LARGE,
      title: 'File quá lớn',
      message: 'File vượt giới hạn 50MB. Vui lòng nén file hoặc chọn file nhỏ hơn.',
      suggestion: undefined,
    },
    [ErrorCode.SCANNED_PDF]: {
      code: ErrorCode.SCANNED_PDF,
      title: 'Không thể đọc text từ PDF',
      message: 'PDF này là ảnh scan — hệ thống không đọc được text. Hãy dùng file PDF có text layer.',
      suggestion: undefined,
    },
    [ErrorCode.INVALID_FILE_FORMAT]: {
      code: ErrorCode.INVALID_FILE_FORMAT,
      title: 'Định dạng file không hợp lệ',
      message: 'Chỉ chấp nhận file PDF. Vui lòng chọn file khác.',
      suggestion: undefined,
    },
    [ErrorCode.LLM_TIMEOUT]: {
      code: ErrorCode.LLM_TIMEOUT,
      title: 'AI đang bận xử lý',
      message: 'AI đang bận xử lý câu hỏi của bạn — thử lại nhé.',
      suggestion: 'Model đang quá tải hoặc kết nối chậm.',
    },
    [ErrorCode.AI_NO_RESPONSE]: {
      code: ErrorCode.AI_NO_RESPONSE,
      title: '⚠️ AI không phản hồi',
      message: 'Có thể do API key không hợp lệ, mạng gián đoạn, hoặc model đang quá tải.',
      suggestion: 'Thử lại sau vài giây hoặc kiểm tra cài đặt.',
    },
    [ErrorCode.INVALID_API_KEY]: {
      code: ErrorCode.INVALID_API_KEY,
      title: 'API Key không hợp lệ',
      message: 'API Key không hợp lệ hoặc hết hạn. Vui lòng kiểm tra lại.',
      suggestion: 'Kiểm tra file .env hoặc Settings.',
    },
    [ErrorCode.NETWORK_ERROR]: {
      code: ErrorCode.NETWORK_ERROR,
      title: 'Mất kết nối mạng',
      message: 'Không thể kết nối đến server. Kiểm tra internet hoặc dùng Local Mode.',
      suggestion: undefined,
    },
    [ErrorCode.SERVER_ERROR]: {
      code: ErrorCode.SERVER_ERROR,
      title: 'Lỗi server',
      message: 'Server gặp lỗi_internal. Thử lại sau.',
      suggestion: undefined,
    },
    [ErrorCode.INVALID_RESPONSE_FORMAT]: {
      code: ErrorCode.INVALID_RESPONSE_FORMAT,
      title: 'Dữ liệu không hợp lệ',
      message: 'Server trả về dữ liệu không hợp lệ (HTML thay vì JSON). Có thể server đang gặp lỗi cấu hình.',
      suggestion: 'Khởi động lại backend.',
    },
    [ErrorCode.UNKNOWN_ERROR]: {
      code: ErrorCode.UNKNOWN_ERROR,
      title: 'Lỗi không xác định',
      message: 'Đã xảy ra lỗi không xác định. Thử lại hoặc liên hệ support.',
      suggestion: undefined,
    },
  };

  const baseMessage = messages[code];
  
  return {
    ...baseMessage,
    message: detail || baseMessage.message,
    actions: [], // Actions sẽ được thêm bởi component
  };
}

/**
 * Helper function để map HTTP status code sang ErrorCode.
 */
export function mapHttpStatusToErrorCode(status: number, detail?: string): ErrorCode {
  switch (status) {
    case 401:
      return ErrorCode.INVALID_API_KEY;
    case 413:
      return ErrorCode.FILE_TOO_LARGE;
    case 504:
      return ErrorCode.LLM_TIMEOUT;
    case 500:
    case 502:
    case 503:
      return ErrorCode.SERVER_ERROR;
    default:
      return ErrorCode.UNKNOWN_ERROR;
  }
}

/**
 * Kiểm tra xem error có phải là network error không.
 */
export function isNetworkError(error: any): boolean {
  return (
    error?.code === 'NETWORK_ERROR' ||
    error?.code === ErrorCode.NETWORK_ERROR ||
    error?.message?.includes('Network Error') ||
    error?.status === 0
  );
}

/**
 * Kiểm tra xem error có retry được không.
 */
export function isRetryable(error: any): boolean {
  const nonRetryableCodes = [
    ErrorCode.FILE_TOO_LARGE,
    ErrorCode.SCANNED_PDF,
    ErrorCode.INVALID_FILE_FORMAT,
    ErrorCode.INVALID_API_KEY,
  ];
  
  return !nonRetryableCodes.includes(error?.code);
}
