import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import RootLayout from './layouts/RootLayout';
import Dashboard from './pages/Dashboard';
import Vault from './pages/Vault';
import Chat from './pages/Chat';
import GraphExplorer from './pages/GraphExplorer';
import GlobalGraphExplorer from './pages/GlobalGraphExplorer';
import Flashcards from './pages/Flashcards';
import Quiz from './pages/Quiz';
import Zettelkasten from './pages/Zettelkasten';
import DocumentGuard from './components/shared/DocumentGuard';
import { ErrorBoundary } from './components/shared/ErrorBoundary';
import { FallbackError } from './components/shared/FallbackError';

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
            <DocumentGuard><GraphExplorer /></DocumentGuard>
          </ErrorBoundary>
        ),
        errorElement: <ErrorPage />,
      },
      {
        path: 'global-graph',
        element: (
          <ErrorBoundary>
            <GlobalGraphExplorer />
          </ErrorBoundary>
        ),
        errorElement: <ErrorPage />,
      },
      {
        path: 'flashcards',
        element: <Flashcards />,
        errorElement: <ErrorPage />,
      },
      {
        path: 'quiz',
        element: <Quiz />,
        errorElement: <ErrorPage />,
      },
      {
        path: 'notes',
        element: <Zettelkasten />,
        errorElement: <ErrorPage />,
      },
    ],
  },
]);

export function Router() {
  return <RouterProvider router={router} />;
}
