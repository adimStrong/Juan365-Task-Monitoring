import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ticketsAPI, usersAPI, departmentsAPI, productsAPI, dashboardAPI } from '../services/api';
import { queryKeys } from '../lib/queryClient';

// ==================
// DEPARTMENTS (cached for 1 hour)
// ==================
export const useDepartments = () => {
  return useQuery({
    queryKey: queryKeys.departments,
    queryFn: async () => {
      const response = await departmentsAPI.list();
      return response.data;
    },
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 2 * 60 * 60 * 1000, // 2 hours
  });
};

// ==================
// PRODUCTS (cached for 1 hour)
// ==================
export const useProducts = (category = null) => {
  return useQuery({
    queryKey: [...queryKeys.products, category],
    queryFn: async () => {
      const params = category ? { category } : {};
      const response = await productsAPI.list(params);
      return response.data;
    },
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 2 * 60 * 60 * 1000, // 2 hours
  });
};

// ==================
// USERS (cached for 5 minutes)
// ==================
export const useUsers = () => {
  return useQuery({
    queryKey: queryKeys.usersList,
    queryFn: async () => {
      const response = await usersAPI.list();
      const data = response.data;
      return Array.isArray(data) ? data : (data.results || []);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// ==================
// DASHBOARD STATS (cached for 1 minute)
// ==================
export const useDashboardStats = () => {
  return useQuery({
    queryKey: queryKeys.dashboardStats,
    queryFn: async () => {
      const response = await dashboardAPI.getStats();
      return response.data;
    },
    staleTime: 60 * 1000, // 1 minute - dashboard needs fresh data
    refetchInterval: 60 * 1000, // Auto-refresh every minute
  });
};

// ==================
// TICKETS LIST (cached for 30 seconds)
// ==================
export const useTickets = (filters = {}) => {
  return useQuery({
    queryKey: queryKeys.ticketsList(filters),
    queryFn: async () => {
      const response = await ticketsAPI.list(filters);
      return response.data.results || response.data;
    },
    staleTime: 30 * 1000, // 30 seconds - tickets change frequently
  });
};

// ==================
// SINGLE TICKET (cached for 1 minute)
// ==================
export const useTicket = (id) => {
  return useQuery({
    queryKey: queryKeys.ticketDetail(id),
    queryFn: async () => {
      const response = await ticketsAPI.get(id);
      return response.data;
    },
    enabled: !!id, // Only run if ID is provided
    staleTime: 60 * 1000, // 1 minute
  });
};

// ==================
// TICKET COMMENTS
// ==================
export const useTicketComments = (ticketId) => {
  return useQuery({
    queryKey: queryKeys.ticketComments(ticketId),
    queryFn: async () => {
      const response = await ticketsAPI.getComments(ticketId);
      return response.data;
    },
    enabled: !!ticketId,
    staleTime: 30 * 1000,
  });
};

// ==================
// MUTATIONS
// ==================

// Approve ticket
export const useApproveTicket = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ticketId) => ticketsAPI.approve(ticketId),
    onSuccess: (_, ticketId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tickets });
      queryClient.invalidateQueries({ queryKey: queryKeys.ticketDetail(ticketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
};

// Reject ticket
export const useRejectTicket = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticketId, reason }) => ticketsAPI.reject(ticketId, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tickets });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
};

// Assign ticket
export const useAssignTicket = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticketId, userId }) => ticketsAPI.assign(ticketId, userId),
    onSuccess: (_, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tickets });
      queryClient.invalidateQueries({ queryKey: queryKeys.ticketDetail(ticketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
};

// Start ticket
export const useStartTicket = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ticketId) => ticketsAPI.start(ticketId),
    onSuccess: (_, ticketId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tickets });
      queryClient.invalidateQueries({ queryKey: queryKeys.ticketDetail(ticketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
};

// Complete ticket
export const useCompleteTicket = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ticketId) => ticketsAPI.complete(ticketId),
    onSuccess: (_, ticketId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tickets });
      queryClient.invalidateQueries({ queryKey: queryKeys.ticketDetail(ticketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
};

// Add comment
export const useAddComment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticketId, comment, parentId }) =>
      ticketsAPI.addComment(ticketId, comment, parentId),
    onSuccess: (_, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ticketComments(ticketId) });
    },
  });
};

// ==================
// ANALYTICS (cached for 5 minutes - expensive query)
// Netflix-style: Show stale data immediately, refresh in background
// ==================
export const useAnalytics = (dateFrom, dateTo) => {
  return useQuery({
    queryKey: queryKeys.analytics({ dateFrom, dateTo }),
    queryFn: async () => {
      const { analyticsAPI } = await import('../services/api');
      const response = await analyticsAPI.get({ date_from: dateFrom, date_to: dateTo });
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes - analytics don't change frequently
    gcTime: 30 * 60 * 1000, // 30 minutes - keep in cache longer
    // Show stale data while revalidating (Netflix pattern)
    refetchOnMount: 'always', // Always check for fresh data
    refetchOnWindowFocus: false, // Don't refetch on tab switch
  });
};
