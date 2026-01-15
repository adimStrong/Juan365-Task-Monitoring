import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { ROUTES } from './constants/routes';
import ErrorBoundary from './components/ErrorBoundary';
import RoleProtectedRoute from './components/RoleProtectedRoute';

// Eager load auth pages (needed immediately)
import Login from './pages/Login';
import Register from './pages/Register';

// Lazy load protected pages (code splitting)
const Dashboard = lazy(() => import('./pages/Dashboard'));
const TicketList = lazy(() => import('./pages/TicketList'));
const TicketDetail = lazy(() => import('./pages/TicketDetail'));
const CreateTicket = lazy(() => import('./pages/CreateTicket'));
const Notifications = lazy(() => import('./pages/Notifications'));
const ActivityLog = lazy(() => import('./pages/ActivityLog'));
const Users = lazy(() => import('./pages/Users'));
const Admin = lazy(() => import('./pages/Admin'));
const Trash = lazy(() => import('./pages/Trash'));
const Analytics = lazy(() => import('./pages/Analytics'));
const NotFound = lazy(() => import('./pages/NotFound'));

// Loading spinner for lazy loaded components
const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-100">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
  </div>
);

// Protected Route wrapper
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <PageLoader />;
  }

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} replace />;
  }

  return <Suspense fallback={<PageLoader />}>{children}</Suspense>;
};

// Public Route wrapper (redirect if authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <PageLoader />;
  }

  if (isAuthenticated) {
    return <Navigate to={ROUTES.HOME} replace />;
  }

  return children;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path={ROUTES.LOGIN}
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />
      <Route
        path={ROUTES.REGISTER}
        element={
          <PublicRoute>
            <Register />
          </PublicRoute>
        }
      />

      {/* Protected Routes - All authenticated users */}
      <Route
        path={ROUTES.HOME}
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.TICKETS}
        element={
          <ProtectedRoute>
            <TicketList />
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.TICKETS_NEW}
        element={
          <ProtectedRoute>
            <CreateTicket />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tickets/:id"
        element={
          <ProtectedRoute>
            <TicketDetail />
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.NOTIFICATIONS}
        element={
          <ProtectedRoute>
            <Notifications />
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.ACTIVITY}
        element={
          <ProtectedRoute>
            <ActivityLog />
          </ProtectedRoute>
        }
      />

      {/* Protected Routes - Manager/Admin only */}
      <Route
        path={ROUTES.USERS}
        element={
          <ProtectedRoute>
            <RoleProtectedRoute requiredRole="manager">
              <Users />
            </RoleProtectedRoute>
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.ADMIN}
        element={
          <ProtectedRoute>
            <RoleProtectedRoute requiredRole="manager">
              <Admin />
            </RoleProtectedRoute>
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.TRASH}
        element={
          <ProtectedRoute>
            <RoleProtectedRoute requiredRole="manager">
              <Trash />
            </RoleProtectedRoute>
          </ProtectedRoute>
        }
      />
      <Route
        path={ROUTES.ANALYTICS}
        element={
          <ProtectedRoute>
            <RoleProtectedRoute requiredRole="manager">
              <Analytics />
            </RoleProtectedRoute>
          </ProtectedRoute>
        }
      />

      {/* 404 Not Found */}
      <Route
        path="*"
        element={
          <Suspense fallback={<PageLoader />}>
            <NotFound />
          </Suspense>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <AuthProvider>
          <ToastProvider>
            <AppRoutes />
          </ToastProvider>
        </AuthProvider>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
