import { QueryClient } from '@tanstack/react-query';

// Create a client with optimal caching settings
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Keep data fresh for 5 minutes
      staleTime: 5 * 60 * 1000,
      // Cache data for 30 minutes
      gcTime: 30 * 60 * 1000,
      // Retry failed requests 2 times
      retry: 2,
      // Don't refetch on window focus by default
      refetchOnWindowFocus: false,
      // Refetch on reconnect
      refetchOnReconnect: true,
    },
  },
});

// Query keys for consistent caching
export const queryKeys = {
  // Tickets
  tickets: ['tickets'],
  ticketsList: (filters) => ['tickets', 'list', filters],
  ticketDetail: (id) => ['tickets', 'detail', id],
  ticketComments: (id) => ['tickets', id, 'comments'],

  // Dashboard
  dashboard: ['dashboard'],
  dashboardStats: ['dashboard', 'stats'],

  // Users
  users: ['users'],
  usersList: ['users', 'list'],
  currentUser: ['users', 'me'],

  // Static data (rarely changes)
  departments: ['departments'],
  products: ['products'],

  // Analytics
  analytics: (params) => ['analytics', params],
};

// Cache invalidation helpers
export const invalidateTickets = () => {
  queryClient.invalidateQueries({ queryKey: queryKeys.tickets });
  queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
};

export const invalidateTicketDetail = (id) => {
  queryClient.invalidateQueries({ queryKey: queryKeys.ticketDetail(id) });
  queryClient.invalidateQueries({ queryKey: queryKeys.tickets });
};
