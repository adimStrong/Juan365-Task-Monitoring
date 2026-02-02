/**
 * Centralized route constants for the ticketing system
 * This prevents hardcoding routes throughout the application
 */

export const ROUTES = {
  // Public routes
  LOGIN: '/login',
  REGISTER: '/register',

  // Protected routes - All users
  HOME: '/',
  TICKETS: '/tickets',
  TICKETS_NEW: '/tickets/new',
  TICKETS_DETAIL: (id) => `/tickets/${id}`,
  NOTIFICATIONS: '/notifications',
  ACTIVITY: '/activity',

  // Protected routes - Managers only
  USERS: '/users',
  ANALYTICS: '/analytics',
  MONTHLY_REPORT: '/monthly',
  TRASH: '/trash',
  ADMIN: '/admin',
};

// Routes that require manager/admin role
export const MANAGER_ONLY_ROUTES = [
  ROUTES.USERS,
  ROUTES.ANALYTICS,
  ROUTES.MONTHLY_REPORT,
  ROUTES.TRASH,
  ROUTES.ADMIN,
];

// Helper to check if a path requires manager role
export const requiresManagerRole = (path) => {
  return MANAGER_ONLY_ROUTES.some(route => path.startsWith(route));
};

// Navigation links configuration
export const getNavLinks = (isManager) => [
  { to: ROUTES.HOME, label: 'Dashboard', show: true },
  { to: ROUTES.TICKETS, label: 'Tickets', show: true, matchPrefix: true },
  { to: ROUTES.ACTIVITY, label: 'Activity', show: true },
  { to: ROUTES.NOTIFICATIONS, label: 'Notifications', show: true },
  { to: ROUTES.USERS, label: 'Users', show: isManager },
  { to: ROUTES.ANALYTICS, label: 'Analytics', show: isManager },
  { to: ROUTES.MONTHLY_REPORT, label: 'Monthly Report', show: isManager },
  { to: ROUTES.TRASH, label: 'Trash', show: isManager },
  { to: ROUTES.ADMIN, label: 'Admin', show: isManager },
];
