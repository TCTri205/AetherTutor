import axios, { AxiosError } from 'axios';
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { ErrorCode, mapHttpStatusToErrorCode } from '../types/errors';

/**
 * Custom API Error class for structured error handling.
 */
export class ApiError extends Error {
  status?: number;
  data?: any;
  code?: ErrorCode;

  constructor(message: string, status?: number, data?: any, code?: ErrorCode) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    this.code = code;
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor (Temporary Authentication via X-User-Id)
// ⚠️ WARNING: This is a TEMPORARY placeholder for Stage 2 multi-tenancy.
// Production MUST replace with proper JWT-based authentication.
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Allow per-user isolation via localStorage (dev/testing) or env variable
    const userId =
      localStorage.getItem('aether_user_id') ||
      import.meta.env.VITE_DEFAULT_USER_ID ||
      '00000000-0000-0000-0000-000000000001';
    config.headers['X-User-Id'] = userId;
    return config;
  },
  (error: any) => Promise.reject(error)
);

// Response Interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Check if the response is HTML (indicates a backend crash/misconfiguration)
    const contentType = response.headers['content-type'];
    if (contentType && contentType.includes('text/html')) {
      throw new ApiError(
        'Dữ liệu trả về không hợp lệ (HTML thay vì JSON). Có thể server đang gặp lỗi cấu hình.',
        500,
        null,
        ErrorCode.INVALID_RESPONSE_FORMAT
      );
    }
    return response;
  },
  async (error: AxiosError) => {
    const { config, response } = error;

    // Retry Logic for 502/503 on GET requests (only once as per plan)
    if (
      config &&
      config.method === 'get' &&
      response &&
      [502, 503].includes(response.status) &&
      !(config as any)._retry
    ) {
      (config as any)._retry = true;
      console.warn(`API is busy (${response.status}). Retrying once...`);
      return api(config);
    }

    // Structured Error Mapping
    if (response) {
      const status = response.status;
      const data = response.data as any;
      const message = data?.detail || data?.message || error.message;
      
      // Map HTTP status to error code
      const errorCode = mapHttpStatusToErrorCode(status, message);
      
      // Special handling for specific error messages
      let finalCode = errorCode;
      
      // Check for scanned PDF error
      if (message?.toLowerCase().includes('scan') || 
          message?.toLowerCase().includes('no text') ||
          message?.toLowerCase().includes('image-only')) {
        finalCode = ErrorCode.SCANNED_PDF;
      }
      
      // Check for invalid API key error (401)
      if (status === 401) {
        finalCode = ErrorCode.INVALID_API_KEY;
      }

      throw new ApiError(message, status, data, finalCode);
    } else if (error.request) {
      throw new ApiError('Không thể kết nối đến server. Vui lòng kiểm tra kết nối mạng.', 0, null, ErrorCode.NETWORK_ERROR);
    } else {
      throw new ApiError(error.message, 0, null, ErrorCode.UNKNOWN_ERROR);
    }
  }
);

export default api;
