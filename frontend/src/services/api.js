import axios from 'axios';

// Use environment variable or default to localhost
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/auth/refresh/`, {
            refresh: refreshToken,
          });

          const { access } = response.data;
          localStorage.setItem('access_token', access);

          originalRequest.headers.Authorization = `Bearer ${access}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, logout
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (username, password) =>
    api.post('/auth/login/', { username, password }),

  register: (data) =>
    api.post('/auth/register/', data),

  getMe: () =>
    api.get('/auth/me/'),

  updateMe: (data) =>
    api.patch('/auth/me/', data),

  getDepartments: () =>
    api.get('/auth/departments/'),
};

// Tickets API
export const ticketsAPI = {
  list: (params = {}) =>
    api.get('/tickets/', { params }),

  get: (id) =>
    api.get(`/tickets/${id}/`),

  create: (data) =>
    api.post('/tickets/', data),

  update: (id, data) =>
    api.patch(`/tickets/${id}/`, data),

  delete: (id) =>
    api.delete(`/tickets/${id}/`),

  // Actions
  approve: (id) =>
    api.post(`/tickets/${id}/approve/`),

  reject: (id, reason = '') =>
    api.post(`/tickets/${id}/reject/`, { reason }),

  assign: (id, userId, scheduledStart = null, scheduledEnd = null) => {
    const data = { assigned_to: userId };
    if (scheduledStart) data.scheduled_start = scheduledStart;
    if (scheduledEnd) data.scheduled_end = scheduledEnd;
    return api.post(`/tickets/${id}/assign/`, data);
  },

  start: (id) =>
    api.post(`/tickets/${id}/start/`),

  complete: (id, actualEnd = null) => {
    const data = {};
    if (actualEnd) data.actual_end = actualEnd;
    return api.post(`/tickets/${id}/complete/`, data);
  },

  // Comments
  getComments: (id) =>
    api.get(`/tickets/${id}/comments/`),

  addComment: (id, comment, parentId = null) =>
    api.post(`/tickets/${id}/comments/`, { comment, parent: parentId }),

  // Attachments
  getAttachments: (id) =>
    api.get(`/tickets/${id}/attachments/`),

  addAttachment: (id, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/tickets/${id}/attachments/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  deleteAttachment: (attachmentId) =>
    api.delete(`/attachments/${attachmentId}/`),

  // Requester confirmation
  confirmComplete: (id) =>
    api.post(`/tickets/${id}/confirm/`),

  // Request revision
  requestRevision: (id, revisionComments) =>
    api.post(`/tickets/${id}/request_revision/`, { revision_comments: revisionComments }),

  // Collaborators
  getCollaborators: (id) =>
    api.get(`/tickets/${id}/collaborators/`),

  addCollaborator: (id, userId) =>
    api.post(`/tickets/${id}/collaborators/`, { user_id: userId }),

  removeCollaborator: (id, userId) =>
    api.delete(`/tickets/${id}/collaborators/`, { data: { user_id: userId } }),

  // History & Rollback
  getHistory: (id) =>
    api.get(`/tickets/${id}/history/`),

  rollback: (id, activityId) =>
    api.post(`/tickets/${id}/rollback/`, { activity_id: activityId }),

  // Trash & Restore
  softDelete: (id) =>
    api.post(`/tickets/${id}/soft_delete/`),

  restore: (id) =>
    api.post(`/tickets/${id}/restore/`),

  getTrash: () =>
    api.get('/tickets/trash/'),

  permanentDelete: (id) =>
    api.delete(`/tickets/${id}/permanent_delete/`),
};

// Users API
export const usersAPI = {
  list: () =>
    api.get('/users/'),

  // User management (admin only)
  listAll: (params = {}) =>
    api.get('/users/manage/', { params }),

  get: (id) =>
    api.get(`/users/manage/${id}/`),

  approve: (id) =>
    api.post(`/users/manage/${id}/approve/`),

  reject: (id) =>
    api.post(`/users/manage/${id}/reject_user/`),

  changeRole: (id, role) =>
    api.post(`/users/manage/${id}/change_role/`, { role }),

  reactivate: (id) =>
    api.post(`/users/manage/${id}/reactivate/`),

  create: (data) =>
    api.post('/users/manage/', data),

  updateProfile: (id, data) =>
    api.patch(`/users/manage/${id}/update_profile/`, data),

  resetPassword: (id, password) =>
    api.post(`/users/manage/${id}/reset_password/`, { password }),

  deleteUser: (id) =>
    api.delete(`/users/manage/${id}/delete_user/`),

  unlockAccount: (id) =>
    api.post(`/users/manage/${id}/unlock_account/`),
};

// Dashboard API
export const dashboardAPI = {
  getStats: () =>
    api.get('/dashboard/stats/'),

  getMyTasks: () =>
    api.get('/dashboard/my-tasks/'),

  getTeamOverview: () =>
    api.get('/dashboard/team-overview/'),

  getOverdue: () =>
    api.get('/dashboard/overdue/'),

  getPendingApprovals: () =>
    api.get('/dashboard/pending-approvals/'),
};

// Analytics API
export const analyticsAPI = {
  getAnalytics: (params = {}) =>
    api.get('/analytics/', { params }),
};

// Notifications API
export const notificationsAPI = {
  list: () =>
    api.get('/notifications/'),

  getUnreadCount: () =>
    api.get('/notifications/unread_count/'),

  markAsRead: (id) =>
    api.post(`/notifications/${id}/read/`),

  markAllAsRead: () =>
    api.post('/notifications/read_all/'),
};

// Activities API
export const activitiesAPI = {
  list: (params = {}) =>
    api.get('/activities/', { params }),
};


// Departments API
export const departmentsAPI = {
  list: (params = {}) =>
    api.get('/departments/', { params }),

  get: (id) =>
    api.get(`/departments/${id}/`),

  create: (data) =>
    api.post('/departments/', data),

  update: (id, data) =>
    api.patch(`/departments/${id}/`, data),

  delete: (id) =>
    api.delete(`/departments/${id}/`),

  setManager: (id, userId) =>
    api.post(`/departments/${id}/set_manager/`, { user_id: userId }),
};

// Products API
export const productsAPI = {
  list: (params = {}) =>
    api.get('/products/', { params }),

  get: (id) =>
    api.get(`/products/${id}/`),

  create: (data) =>
    api.post('/products/', data),

  update: (id, data) =>
    api.patch(`/products/${id}/`, data),

  delete: (id) =>
    api.delete(`/products/${id}/`),
};

export default api;
