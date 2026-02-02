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
// MY TASKS (cached for 1 minute)
// ==================
export const useMyTasks = () => {
  return useQuery({
    queryKey: queryKeys.myTasks,
    queryFn: async () => {
      const response = await dashboardAPI.getMyTasks();
      return response.data.results || response.data;
    },
    staleTime: 60 * 1000,
  });
};

// ==================
// PENDING APPROVALS (cached for 1 minute, managers only)
// ==================
export const usePendingApprovals = (isManager = false) => {
  return useQuery({
    queryKey: queryKeys.pendingApprovals,
    queryFn: async () => {
      const response = await dashboardAPI.getPendingApprovals();
      return response.data;
    },
    enabled: isManager, // Only fetch for managers
    staleTime: 60 * 1000,
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
      return response.data;
    },
    staleTime: 30 * 1000, // 30 seconds - tickets change frequently
    placeholderData: (previousData) => previousData, // Keep previous data while loading new page
  });
};

// Prefetch next/previous pages for smooth pagination
export const usePrefetchTickets = () => {
  const queryClient = useQueryClient();

  return (filters) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.ticketsList(filters),
      queryFn: async () => {
        const response = await ticketsAPI.list(filters);
        return response.data;
      },
      staleTime: 30 * 1000,
    });
  };
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
// MUTATIONS WITH OPTIMISTIC UPDATES
// ==================

// Helper to update ticket in list cache
const updateTicketInLists = (queryClient, ticketId, updater) => {
  // Update all ticket list queries
  queryClient.setQueriesData(
    { queryKey: queryKeys.tickets },
    (old) => {
      if (!old) return old;
      // Handle paginated response (results array)
      if (old.results) {
        return {
          ...old,
          results: old.results.map((ticket) =>
            ticket.id === ticketId ? updater(ticket) : ticket
          ),
        };
      }
      // Handle array response
      if (Array.isArray(old)) {
        return old.map((ticket) =>
          ticket.id === ticketId ? updater(ticket) : ticket
        );
      }
      return old;
    }
  );
};

// Helper to update ticket detail cache
const updateTicketDetail = (queryClient, ticketId, updater) => {
  queryClient.setQueryData(queryKeys.ticketDetail(ticketId), (old) => {
    if (!old) return old;
    return updater(old);
  });
};

// Approve ticket (with optimistic update)
export const useApproveTicket = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ticketId) => ticketsAPI.approve(ticketId),
    onMutate: async (ticketId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.tickets });
      await queryClient.cancelQueries({ queryKey: queryKeys.ticketDetail(ticketId) });

      // Snapshot previous values
      const previousDetail = queryClient.getQueryData(queryKeys.ticketDetail(ticketId));

      // Optimistically update
      const updater = (ticket) => ({
        ...ticket,
        status: 'approved',
        status_display: 'Approved',
      });
      updateTicketInLists(queryClient, ticketId, updater);
      updateTicketDetail(queryClient, ticketId, updater);

      return { previousDetail, ticketId };
    },
    onError: (err, ticketId, context) => {
      // Rollback on error
      if (context?.previousDetail) {
        queryClient.setQueryData(queryKeys.ticketDetail(ticketId), context.previousDetail);
      }
      // Invalidate to refetch correct data
      queryClient.invalidateQueries({ queryKey: queryKeys.tickets });
    },
    onSettled: (_, __, ticketId) => {
      // Always refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: queryKeys.ticketDetail(ticketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.pendingApprovals });
      queryClient.invalidateQueries({ queryKey: queryKeys.myTasks });
    },
  });
};

// Reject ticket (with optimistic update)
export const useRejectTicket = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticketId, reason }) => ticketsAPI.reject(ticketId, { reason }),
    onMutate: async ({ ticketId }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.tickets });
      await queryClient.cancelQueries({ queryKey: queryKeys.ticketDetail(ticketId) });

      const previousDetail = queryClient.getQueryData(queryKeys.ticketDetail(ticketId));

      const updater = (ticket) => ({
        ...ticket,
        status: 'rejected',
        status_display: 'Rejected',
      });
      updateTicketInLists(queryClient, ticketId, updater);
      updateTicketDetail(queryClient, ticketId, updater);

      return { previousDetail, ticketId };
    },
    onError: (err, { ticketId }, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(queryKeys.ticketDetail(ticketId), context.previousDetail);
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.tickets });
    },
    onSettled: (_, __, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ticketDetail(ticketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.pendingApprovals });
    },
  });
};

// Assign ticket (with optimistic update)
export const useAssignTicket = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticketId, userId }) => ticketsAPI.assign(ticketId, userId),
    onMutate: async ({ ticketId, userId }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.tickets });
      await queryClient.cancelQueries({ queryKey: queryKeys.ticketDetail(ticketId) });

      const previousDetail = queryClient.getQueryData(queryKeys.ticketDetail(ticketId));

      // Try to get assigned user info from users cache
      const users = queryClient.getQueryData(queryKeys.usersList);
      const assignedUser = users?.find((u) => u.id === userId);

      const updater = (ticket) => ({
        ...ticket,
        status: 'assigned',
        status_display: 'Assigned',
        assigned_to: userId,
        assigned_to_name: assignedUser?.full_name || assignedUser?.username || 'Assigning...',
      });
      updateTicketInLists(queryClient, ticketId, updater);
      updateTicketDetail(queryClient, ticketId, updater);

      return { previousDetail, ticketId };
    },
    onError: (err, { ticketId }, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(queryKeys.ticketDetail(ticketId), context.previousDetail);
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.tickets });
    },
    onSettled: (_, __, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ticketDetail(ticketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.myTasks });
    },
  });
};

// Start ticket (with optimistic update)
export const useStartTicket = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ticketId) => ticketsAPI.start(ticketId),
    onMutate: async (ticketId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.tickets });
      await queryClient.cancelQueries({ queryKey: queryKeys.ticketDetail(ticketId) });

      const previousDetail = queryClient.getQueryData(queryKeys.ticketDetail(ticketId));

      const updater = (ticket) => ({
        ...ticket,
        status: 'in_progress',
        status_display: 'In Progress',
        started_at: new Date().toISOString(),
      });
      updateTicketInLists(queryClient, ticketId, updater);
      updateTicketDetail(queryClient, ticketId, updater);

      return { previousDetail, ticketId };
    },
    onError: (err, ticketId, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(queryKeys.ticketDetail(ticketId), context.previousDetail);
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.tickets });
    },
    onSettled: (_, __, ticketId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ticketDetail(ticketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.myTasks });
    },
  });
};

// Complete ticket (with optimistic update)
export const useCompleteTicket = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (ticketId) => ticketsAPI.complete(ticketId),
    onMutate: async (ticketId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.tickets });
      await queryClient.cancelQueries({ queryKey: queryKeys.ticketDetail(ticketId) });

      const previousDetail = queryClient.getQueryData(queryKeys.ticketDetail(ticketId));

      const updater = (ticket) => ({
        ...ticket,
        status: 'completed',
        status_display: 'Completed',
        completed_at: new Date().toISOString(),
      });
      updateTicketInLists(queryClient, ticketId, updater);
      updateTicketDetail(queryClient, ticketId, updater);

      return { previousDetail, ticketId };
    },
    onError: (err, ticketId, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(queryKeys.ticketDetail(ticketId), context.previousDetail);
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.tickets });
    },
    onSettled: (_, __, ticketId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ticketDetail(ticketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.myTasks });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
    },
  });
};

// Add comment (with optimistic update)
export const useAddComment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticketId, comment, parentId }) =>
      ticketsAPI.addComment(ticketId, comment, parentId),
    onMutate: async ({ ticketId, comment, parentId }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.ticketComments(ticketId) });

      const previousComments = queryClient.getQueryData(queryKeys.ticketComments(ticketId));

      // Create optimistic comment
      const optimisticComment = {
        id: `temp-${Date.now()}`,
        content: comment,
        parent_id: parentId || null,
        created_at: new Date().toISOString(),
        user: { username: 'You' }, // Will be replaced by server response
        is_optimistic: true, // Flag to identify optimistic updates
      };

      queryClient.setQueryData(queryKeys.ticketComments(ticketId), (old) => {
        if (!old) return [optimisticComment];
        if (Array.isArray(old)) return [...old, optimisticComment];
        if (old.results) return { ...old, results: [...old.results, optimisticComment] };
        return old;
      });

      return { previousComments, ticketId };
    },
    onError: (err, { ticketId }, context) => {
      if (context?.previousComments) {
        queryClient.setQueryData(queryKeys.ticketComments(ticketId), context.previousComments);
      }
    },
    onSettled: (_, __, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ticketComments(ticketId) });
    },
  });
};

// ==================
// ANALYTICS (cached for 5 minutes - expensive query)
// Netflix-style: Show stale data immediately, refresh in background
// ==================
export const useAnalytics = (dateFrom, dateTo, enabled = true) => {
  return useQuery({
    queryKey: queryKeys.analytics({ dateFrom, dateTo }),
    queryFn: async () => {
      const params = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const { analyticsAPI } = await import('../services/api');
      const response = await analyticsAPI.getAnalytics(params);
      return response.data;
    },
    enabled, // Allow conditional fetching
    staleTime: 5 * 60 * 1000, // 5 minutes - analytics don't change frequently
    gcTime: 30 * 60 * 1000, // 30 minutes - keep in cache longer
    placeholderData: (previousData) => previousData, // Show previous data while loading
    refetchOnWindowFocus: false, // Don't refetch on tab switch
  });
};

// Hook to get date range for analytics (initial load)
export const useAnalyticsDateRange = () => {
  return useQuery({
    queryKey: ['analytics', 'date-range'],
    queryFn: async () => {
      const { analyticsAPI } = await import('../services/api');
      const response = await analyticsAPI.getAnalytics({});
      return {
        minDate: response.data.date_range?.min_date || '',
        maxDate: response.data.date_range?.max_date || '',
      };
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 60 * 60 * 1000, // 1 hour
  });
};

// ==================
// MONTHLY REPORT (cached for 10 minutes)
// ==================
export const useMonthlyReport = (year, month, enabled = true) => {
  return useQuery({
    queryKey: ['monthly-report', year, month],
    queryFn: async () => {
      const { monthlyReportAPI } = await import('../services/api');
      const response = await monthlyReportAPI.getReport(year, month);
      return response.data;
    },
    enabled: enabled && !!year && !!month,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
    placeholderData: (previousData) => previousData,
    refetchOnWindowFocus: false,
  });
};
