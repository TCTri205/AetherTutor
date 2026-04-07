import React, { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { FallbackError } from './FallbackError';

interface Props {
  children: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Global Error Boundary component.
 * Catches JavaScript errors in child components and displays fallback UI.
 * Prevents "white screen of death" when a component crashes.
 */
export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
    
    // Call optional error reporting callback
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
    
    // TODO: Send to error tracking service (Sentry, etc.)
    // if (process.env.NODE_ENV === 'production') {
    //   sendToSentry(error, errorInfo);
    // }
  }

  public render() {
    if (this.state.hasError) {
      return <FallbackError error={this.state.error} />;
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
