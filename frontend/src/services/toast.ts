import { toast } from 'sonner';

/**
 * Standardized toast notification service for AetherTutor.
 * 
 * Provides consistent defaults for duration, dismissibility, and styling
 * across all toast notifications in the application.
 * 
 * Usage:
 *   import { toastService } from '@/services/toast';
 *   toastService.success('Document uploaded successfully');
 *   toastService.error('Upload failed', 'Please check your connection and try again.');
 */
export const toastService = {
  /**
   * Show a success toast.
   * @param message - The success message to display
   * @param duration - Auto-dismiss duration in ms (default: 3000)
   */
  success: (message: string, duration = 3000) =>
    toast.success(message, { duration }),

  /**
   * Show an error toast.
   * @param message - The error message to display
   * @param description - Optional detailed description
   */
  error: (message: string, description?: string) =>
    toast.error(message, {
      duration: 5000,
      dismissible: true,
      description,
    }),

  /**
   * Show a warning toast.
   * @param message - The warning message to display
   * @param duration - Auto-dismiss duration in ms (default: 4000)
   */
  warning: (message: string, duration = 4000) =>
    toast.warning(message, { duration }),

  /**
   * Show an info toast.
   * @param message - The info message to display
   * @param duration - Auto-dismiss duration in ms (default: 3000)
   */
  info: (message: string, duration = 3000) =>
    toast.info(message, { duration }),

  /**
   * Show a loading toast (spinner).
   * Returns a toast ID that can be used to dismiss or update it.
   * @param message - The loading message to display
   * @returns Toast ID for later dismissal
   */
  loading: (message: string) =>
    toast.loading(message),

  /**
   * Dismiss a toast by ID, or all toasts if no ID provided.
   * @param id - Optional toast ID to dismiss
   */
  dismiss: (id?: string | number) =>
    toast.dismiss(id),

  /**
   * Show a promise-based toast that resolves/dismisses on promise completion.
   * @param promise - The promise to track
   * @param messages - Messages for loading, success, and error states
   * @returns Toast ID
   */
  promise: <T>(
    promise: Promise<T>,
    messages: {
      loading: string;
      success: string | ((data: T) => string);
      error: string | ((error: unknown) => string);
    }
  ) =>
    toast.promise(promise, {
      loading: messages.loading,
      success: messages.success,
      error: messages.error,
    }),
};
