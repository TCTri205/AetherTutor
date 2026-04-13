import { createBrowserRouter, RouterProvider, Navigate, lazy, Suspense } from 'react-router-dom';
import RootLayout from './layouts/RootLayout';
import Dashboard from './pages/Dashboard';
import Vault from './pages/Vault';
import Chat from './pages/Chat';
import MediaViewer from './pages/MediaViewer';
import { OfflinePage } from './pages/OfflinePage';
import DocumentGuard from './components/shared/DocumentGuard';
import { ErrorBoundary } from './components/shared/ErrorBoundary';
import { FallbackError } from './components/shared/FallbackError';
import { ThemeProvider } from './providers/ThemeProvider';
import { InstallPrompt } from './components/shared/InstallPrompt';
import LoadingSkeleton from './components/shared/LoadingSkeleton';
import './styles/tokens.css';

// Lazy load heavy pages (code splitting)
const GraphExplorer = lazy(() => import('./pages/GraphExplorer'));
const GlobalGraphExplorer = lazy(() => import('./pages/GlobalGraphExplorer'));
const Flashcards = lazy(() => import('./pages/Flashcards'));
const Quiz = lazy(() => import('./pages/Quiz'));
const Zettelkasten = lazy(() => import('./pages/Zettelkasten'));
const TeamSettings = lazy(() => import('./pages/TeamSettings'));
const LanguageChat = lazy(() => import('./pages/LanguageChat'));
const MathChat = lazy(() => import('./pages/MathChat'));

// Error page component for route-level errors
const ErrorPage = ({ error }: { error?: any }) => (
  <FallbackError 
    error={error instanceof Error ? error : new Error(String(error))} 
    onRetry={() => window.location.reload()}
    onGoHome={() => window.location.href = '/dashboard'}
  />
);

const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    errorElement: <ErrorPage />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { 
        path: 'dashboard', 
        element: <Dashboard />,
        errorElement: <ErrorPage />,
      },
      { 
        path: 'vault', 
        element: <Vault />,
        errorElement: <ErrorPage />,
      },
      {
        path: 'chat/:documentId?',
        element: (
          <ErrorBoundary>
            <DocumentGuard><Chat /></DocumentGuard>
          </ErrorBoundary>
        ),
        errorElement: <ErrorPage />,
      },
      {
        path: 'graph/:documentId?',
        element: (
          <ErrorBoundary>
            <Suspense fallback={<LoadingSkeleton />}>
              <DocumentGuard><GraphExplorer /></DocumentGuard>
            </Suspense>
          </ErrorBoundary>
        ),
        errorElement: <ErrorPage />,
      },
      {
        path: 'global-graph',
        element: (
          <ErrorBoundary>
            <Suspense fallback={<LoadingSkeleton />}>
              <GlobalGraphExplorer />
            </Suspense>
          </ErrorBoundary>
        ),
        errorElement: <ErrorPage />,
      },
      {
        path: 'flashcards',
        element: (
          <ErrorBoundary>
            <Suspense fallback={<LoadingSkeleton />}>
              <Flashcards />
            </Suspense>
          </ErrorBoundary>
        ),
        errorElement: <ErrorPage />,
      },
      {
        path: 'quiz',
        element: (
          <ErrorBoundary>
            <Suspense fallback={<LoadingSkeleton />}>
              <Quiz />
            </Suspense>
          </ErrorBoundary>
        ),
        errorElement: <ErrorPage />,
      },
      {
        path: 'notes',
        element: (
          <ErrorBoundary>
            <Suspense fallback={<LoadingSkeleton />}>
              <Zettelkasten />
            </Suspense>
          </ErrorBoundary>
        ),
        errorElement: <ErrorPage />,
      },
      {
        path: 'team/:teamId',
        element: (
          <ErrorBoundary>
            <Suspense fallback={<LoadingSkeleton />}>
              <TeamSettings />
            </Suspense>
          </ErrorBoundary>
        ),
        errorElement: <ErrorPage />,
      },
      {
        path: 'offline',
        element: <OfflinePage />,
      },
      {
        path: 'language-chat',
        element: (
          <ErrorBoundary>
            <Suspense fallback={<LoadingSkeleton />}>
              <LanguageChat />
            </Suspense>
          </ErrorBoundary>
        ),
        errorElement: <ErrorPage />,
      },
      {
        path: 'math-chat',
        element: (
          <ErrorBoundary>
            <Suspense fallback={<LoadingSkeleton />}>
              <MathChat />
            </Suspense>
          </ErrorBoundary>
        ),
        errorElement: <ErrorPage />,
      },
      {
        path: 'media/:documentId',
        element: (
          <ErrorBoundary>
            <MediaViewer />
          </ErrorBoundary>
        ),
        errorElement: <ErrorPage />,
      },
    ],
  },
]);

export function Router() {
  return (
    <ThemeProvider>
      <OfflinePage />
      <InstallPrompt />
      <RouterProvider router={router} />
    </ThemeProvider>
  );
}
