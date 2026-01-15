import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ROUTES } from '../constants/routes';
import PageLoader from './PageLoader';

/**
 * Role-based route protection component
 * Redirects non-manager users to dashboard if they try to access manager-only routes
 */
const RoleProtectedRoute = ({ children, requiredRole = 'manager' }) => {
  const { loading, isManager, isAdmin } = useAuth();

  if (loading) {
    return <PageLoader />;
  }

  // Check role requirements
  const hasRequiredRole = () => {
    if (requiredRole === 'admin') {
      return isAdmin;
    }
    if (requiredRole === 'manager') {
      return isManager; // isManager includes admin
    }
    return true;
  };

  if (!hasRequiredRole()) {
    // Redirect to dashboard with a message (could be enhanced with toast)
    return <Navigate to={ROUTES.HOME} replace />;
  }

  return children;
};

export default RoleProtectedRoute;
