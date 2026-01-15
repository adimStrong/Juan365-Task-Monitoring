import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI, dashboardAPI, ticketsAPI } from '../services/api';
import { queryClient, queryKeys } from '../lib/queryClient';

const AuthContext = createContext(null);

// Prefetch common data after authentication for faster navigation
const prefetchCommonData = () => {
  // Prefetch dashboard stats
  queryClient.prefetchQuery({
    queryKey: queryKeys.dashboardStats,
    queryFn: () => dashboardAPI.getStats().then(res => res.data),
  });
  // Prefetch my tasks
  queryClient.prefetchQuery({
    queryKey: queryKeys.myTasks,
    queryFn: () => dashboardAPI.getMyTasks().then(res => res.data.results || res.data),
  });
  // Prefetch ticket list (first page)
  queryClient.prefetchQuery({
    queryKey: queryKeys.ticketsList({}),
    queryFn: () => ticketsAPI.list({}).then(res => res.data.results || res.data),
  });
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const response = await authAPI.getMe();
        setUser(response.data);
        // Prefetch common data for faster navigation
        prefetchCommonData();
      } catch (error) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }
    }
    setLoading(false);
  };

  const login = async (username, password) => {
    const response = await authAPI.login(username, password);
    const { access, refresh } = response.data;

    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);

    const userResponse = await authAPI.getMe();
    setUser(userResponse.data);

    // Prefetch common data for faster navigation after login
    prefetchCommonData();

    return userResponse.data;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
    isManager: user?.role === 'admin' || user?.role === 'manager',
    isAdmin: user?.role === 'admin',
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
