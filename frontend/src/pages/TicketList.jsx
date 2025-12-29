// v1.0.2 - Force Vercel rebuild Dec 27 2025
import { useState, useEffect, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ticketsAPI, usersAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import Layout from '../components/Layout';
import { TicketListSkeleton } from '../components/Skeleton';
import TicketCard from '../components/TicketCard';
import TicketPreviewModal from '../components/TicketPreviewModal';

const TicketList = () => {
  const { user, isManager } = useAuth();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tickets, setTickets] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState('table'); // 'table' or 'cards'
  const [previewTicketId, setPreviewTicketId] = useState(null);
  const [localSearch, setLocalSearch] = useState(''); // Local search state for debouncing
  const searchDebounceRef = useRef(null);

  // Inline action states
  const [actionLoading, setActionLoading] = useState(null); // ticketId being processed
  const [rejectModal, setRejectModal] = useState({ show: false, ticketId: null });
  const [rejectReason, setRejectReason] = useState('');
  const [assignModal, setAssignModal] = useState({ show: false, ticketId: null });
  const [selectedAssignees, setSelectedAssignees] = useState([]);
  // Scheduled task complete modal
  const [scheduledCompleteModal, setScheduledCompleteModal] = useState({ show: false, ticket: null });
  const [actualEnd, setActualEnd] = useState('');

  // Filters from URL
  const statusFilter = searchParams.get('status') || '';
  const priorityFilter = searchParams.get('priority') || '';
  const searchQuery = searchParams.get('search') || '';
  const dateFrom = searchParams.get('date_from') || '';
  const dateTo = searchParams.get('date_to') || '';
  const myTasksFilter = searchParams.get('my_tasks') || '';

  // Pagination from URL
  const currentPage = parseInt(searchParams.get('page') || '1', 10);
  const pageSize = parseInt(searchParams.get('page_size') || '20', 10);

  // Pagination state
  const [paginationInfo, setPaginationInfo] = useState({
    count: 0,
    total_pages: 1,
    current_page: 1,
    page_size: 20,
    next: null,
    previous: null
  });

  // Sync local search with URL on mount
  useEffect(() => {
    setLocalSearch(searchQuery);
  }, []);

  // Debounced search effect
  useEffect(() => {
    // Clear previous timeout
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }
    // Set new timeout for 300ms debounce
    searchDebounceRef.current = setTimeout(() => {
      if (localSearch !== searchQuery) {
        if (localSearch) {
          searchParams.set('search', localSearch);
        } else {
          searchParams.delete('search');
        }
        // Reset to page 1 when search changes
        searchParams.set('page', '1');
        setSearchParams(searchParams);
      }
    }, 300);

    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current);
      }
    };
  }, [localSearch]);

  useEffect(() => {
    fetchTickets();
    fetchUsers();
  }, [statusFilter, priorityFilter, searchQuery, dateFrom, dateTo, myTasksFilter, currentPage, pageSize]);

  // Fetch users for assign modal
  const fetchUsers = async () => {
    try {
      const response = await usersAPI.list();
      const usersData = response.data;
      setUsers(Array.isArray(usersData) ? usersData : (usersData.results || []));
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  // Handle action from preview modal - update only that ticket, not full reload
  const handleTicketAction = async (action, ticketId) => {
    try {
      // Fetch updated ticket data
      const response = await ticketsAPI.get(ticketId);
      const updatedTicket = response.data;

      // Update only that ticket in the list
      setTickets(prevTickets =>
        prevTickets.map(t => t.id === ticketId ? updatedTicket : t)
      );

      toast.success(`Ticket ${action} successful!`);
    } catch (error) {
      // If ticket was moved (e.g., rejected), remove it from list
      setTickets(prevTickets => prevTickets.filter(t => t.id !== ticketId));
    }
  };

  // Permission helper for inline actions
  const getTicketPermissions = (ticket) => {
    const isRequester = user?.id === ticket.requester?.id;
    const isAssigned = user?.id === ticket.assigned_to?.id;
    const isCollaborator = ticket.collaborators?.some(c => c.user?.id === user?.id);

    return {
      canApprove: isManager && ['requested', 'pending_creative'].includes(ticket.status),
      canReject: isManager && ['requested', 'pending_creative'].includes(ticket.status),
      canAssign: isManager && ticket.status === 'approved',
      canStart: (isAssigned || isCollaborator) && ticket.status === 'approved',
      canComplete: (isAssigned || isCollaborator || isManager) && ticket.status === 'in_progress',
      canRequestRevision: (isRequester || isManager) && ticket.status === 'completed' && !ticket.confirmed_by_requester,
    };
  };

  // Inline action handler
  const handleInlineAction = async (e, action, ticket) => {
    e.stopPropagation(); // Prevent row click
    const ticketId = ticket.id;

    // Prevent double-clicks - check if already processing
    if (actionLoading === ticketId) return;

    if (action === 'reject') {
      setRejectModal({ show: true, ticketId });
      setRejectReason('');
      return;
    }

    if (action === 'assign') {
      setAssignModal({ show: true, ticketId });
      setSelectedAssignees([]);
      return;
    }

    // Set loading IMMEDIATELY to prevent double-clicks
    setActionLoading(ticketId);
    try {
      if (action === 'approve') {
        await ticketsAPI.approve(ticketId);
      } else if (action === 'start') {
        await ticketsAPI.start(ticketId);
      } else if (action === 'complete') {
        // For scheduled tasks, show modal to get end time
        const ticket = tickets.find(t => t.id === ticketId);
        const scheduledTypes = ['videoshoot', 'photoshoot', 'live_production'];
        if (ticket && scheduledTypes.includes(ticket.request_type)) {
          setScheduledCompleteModal({ show: true, ticket });
          setActionLoading(null);
          return;
        }
        await ticketsAPI.complete(ticketId);
      } else if (action === 'revision') {
        await ticketsAPI.requestRevision(ticketId, { reason: 'Revision requested' });
      }

      // Refresh the ticket
      const response = await ticketsAPI.get(ticketId);
      setTickets(prev => prev.map(t => t.id === ticketId ? response.data : t));
      toast.success(`Ticket ${action} successful!`);
    } catch (error) {
      toast.error(error.response?.data?.error || `Failed to ${action}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Handle reject submit
  const handleRejectSubmit = async () => {
    if (!rejectReason.trim()) {
      toast.error('Please provide a reason');
      return;
    }
    const ticketId = rejectModal.ticketId;
    setActionLoading(ticketId);
    try {
      await ticketsAPI.reject(ticketId, { reason: rejectReason });
      // Remove from list since rejected tickets go to trash
      setTickets(prev => prev.filter(t => t.id !== ticketId));
      toast.success('Ticket rejected!');
      setRejectModal({ show: false, ticketId: null });
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to reject');
    } finally {
      setActionLoading(null);
    }
  };

  // Handle assign submit
  const handleAssignSubmit = async () => {
    if (selectedAssignees.length === 0) {
      toast.error('Please select at least one person');
      return;
    }
    const ticketId = assignModal.ticketId;
    setActionLoading(ticketId);
    try {
      // First user is assigned_to
      await ticketsAPI.assign(ticketId, selectedAssignees[0]);

      // Add remaining users as collaborators
      for (const odIds of selectedAssignees.slice(1)) {
        await ticketsAPI.addCollaborator(ticketId, odIds);
      }

      const response = await ticketsAPI.get(ticketId);
      setTickets(prev => prev.map(t => t.id === ticketId ? response.data : t));
      toast.success('Ticket assigned!');
      setAssignModal({ show: false, ticketId: null });
    } catch (error) {
      console.error('Assign error:', error.response?.data || error);
      const errorMsg = error.response?.data?.error || error.response?.data?.assigned_to?.[0] || error.response?.data?.detail || 'Failed to assign';
      toast.error(errorMsg);
    } finally {
      setActionLoading(null);
    }
  };

  // Get Creative department members for assign
  const getCreativeMembers = () => {
    return users.filter(u => u.user_department_info?.is_creative) || [];
  };

  // Handle scheduled task complete submit
  const handleScheduledCompleteSubmit = async () => {
    if (!actualEnd) {
      toast.error('Please enter the end time');
      return;
    }
    const ticketId = scheduledCompleteModal.ticket?.id;
    setActionLoading(ticketId);
    try {
      await ticketsAPI.complete(ticketId, actualEnd);
      const response = await ticketsAPI.get(ticketId);
      setTickets(prev => prev.map(t => t.id === ticketId ? response.data : t));
      toast.success('Ticket completed!');
      setScheduledCompleteModal({ show: false, ticket: null });
      setActualEnd('');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to complete');
    } finally {
      setActionLoading(null);
    }
  };

  // Load view preference from localStorage
  useEffect(() => {
    const savedView = localStorage.getItem('ticketViewMode');
    if (savedView) {
      setViewMode(savedView);
    }
  }, []);

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        page_size: pageSize
      };
      if (statusFilter) params.status = statusFilter;
      if (priorityFilter) params.priority = priorityFilter;
      if (searchQuery) params.search = searchQuery;
      if (dateFrom) params.created_after = dateFrom;
      if (dateTo) params.created_before = dateTo;
      if (myTasksFilter) params.my_tasks = myTasksFilter;

      const response = await ticketsAPI.list(params);
      const data = response.data;

      // Handle paginated response
      if (data.results) {
        setTickets(data.results);
        setPaginationInfo({
          count: data.count || 0,
          total_pages: data.total_pages || 1,
          current_page: data.current_page || 1,
          page_size: data.page_size || pageSize,
          next: data.next,
          previous: data.previous
        });
      } else {
        // Fallback for non-paginated response
        setTickets(Array.isArray(data) ? data : []);
        setPaginationInfo({
          count: Array.isArray(data) ? data.length : 0,
          total_pages: 1,
          current_page: 1,
          page_size: pageSize,
          next: null,
          previous: null
        });
      }
    } catch (error) {
      console.error('Failed to fetch tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    if (value) {
      searchParams.set(key, value);
    } else {
      searchParams.delete(key);
    }
    // Reset to page 1 when filters change
    searchParams.set('page', '1');
    setSearchParams(searchParams);
  };

  const clearFilters = () => {
    setSearchParams({});
  };

  // Pagination handlers
  const handlePageChange = (newPage) => {
    searchParams.set('page', newPage.toString());
    setSearchParams(searchParams);
  };

  const handlePageSizeChange = (newSize) => {
    searchParams.set('page_size', newSize.toString());
    searchParams.set('page', '1'); // Reset to page 1 when changing page size
    setSearchParams(searchParams);
  };

  const toggleViewMode = (mode) => {
    setViewMode(mode);
    localStorage.setItem('ticketViewMode', mode);
  };

  const handleCardClick = (ticket) => {
    setPreviewTicketId(ticket.id);
  };

  const hasActiveFilters = statusFilter || priorityFilter || searchQuery || dateFrom || dateTo;

  const getPriorityColor = (priority) => {
    const colors = {
      urgent: 'bg-red-100 text-red-800',
      high: 'bg-orange-100 text-orange-800',
      medium: 'bg-yellow-100 text-yellow-800',
      low: 'bg-green-100 text-green-800',
    };
    return colors[priority] || 'bg-gray-100 text-gray-800';
  };

  const getStatusColor = (status) => {
    const colors = {
      requested: 'bg-blue-100 text-blue-800',
      pending_creative: 'bg-purple-100 text-purple-800',
      approved: 'bg-cyan-100 text-cyan-800',
      rejected: 'bg-gray-100 text-gray-800',
      in_progress: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getStatusText = (status) => {
    const texts = {
      requested: 'For Dept Approval',
      pending_creative: 'For Creative Approval',
      approved: 'Not Yet Started',
      rejected: 'Rejected',
      in_progress: 'In Progress',
      completed: 'Completed',
    };
    return texts[status] || status?.replace('_', ' ');
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Tickets</h1>
          <Link
            to="/tickets/new"
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            + New Ticket
          </Link>
        </div>

        {/* Search, Filters & View Toggle */}
        <div className="bg-white shadow rounded-lg p-4">
          {/* Search Bar and View Toggle */}
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-4 mb-4">
            <div className="flex-1">
              <input
                type="text"
                placeholder="Search tickets..."
                value={localSearch}
                onChange={(e) => setLocalSearch(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-4 py-2 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="flex gap-2">
              {/* View Toggle */}
              <div className="flex border border-gray-300 rounded-md overflow-hidden">
                <button
                  onClick={() => toggleViewMode('table')}
                  className={`px-3 py-2 ${viewMode === 'table' ? 'bg-blue-500 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
                  title="Table View"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                  </svg>
                </button>
                <button
                  onClick={() => toggleViewMode('cards')}
                  className={`px-3 py-2 ${viewMode === 'cards' ? 'bg-blue-500 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
                  title="Card View"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                  </svg>
                </button>
              </div>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`px-4 py-2 border rounded-md text-sm font-medium ${
                  showFilters || hasActiveFilters
                    ? 'border-blue-500 text-blue-600 bg-blue-50'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                <svg className="w-5 h-5 inline-block mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                </svg>
                Filters {hasActiveFilters && `(${[statusFilter, priorityFilter, dateFrom, dateTo].filter(Boolean).length})`}
              </button>
            </div>
          </div>

          {/* Advanced Filters */}
          {showFilters && (
            <div className="border-t pt-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                  <select
                    value={statusFilter}
                    onChange={(e) => handleFilterChange('status', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">All Status</option>
                    <option value="requested">For Dept Approval</option>
                    <option value="pending_creative">For Creative Approval</option>
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                  <select
                    value={priorityFilter}
                    onChange={(e) => handleFilterChange('priority', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">All Priority</option>
                    <option value="urgent">Urgent</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => handleFilterChange('date_from', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => handleFilterChange('date_to', e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
              {hasActiveFilters && (
                <div className="mt-4 flex justify-end">
                  <button
                    onClick={clearFilters}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Clear all filters
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Results count and Page Size Selector */}
        {!loading && (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="text-sm text-gray-500">
              Showing {tickets.length} of {paginationInfo.count} ticket{paginationInfo.count !== 1 ? 's' : ''}
              {hasActiveFilters && ' (filtered)'}
              {paginationInfo.total_pages > 1 && ` • Page ${paginationInfo.current_page} of ${paginationInfo.total_pages}`}
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">Show:</label>
              <select
                value={pageSize}
                onChange={(e) => handlePageSizeChange(parseInt(e.target.value, 10))}
                className="border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="10">10</option>
                <option value="20">20</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
              <span className="text-sm text-gray-600">per page</span>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    {['Ticket', 'Requester', 'Assigned To', 'Status', 'Priority', 'Created', 'Product', 'Category', 'Actions'].map((h) => (
                      <th key={h} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {[...Array(6)].map((_, i) => (
                    <tr key={i}>
                      {[...Array(9)].map((_, j) => (
                        <td key={j} className="px-6 py-4">
                          <div className="animate-pulse bg-gray-200 rounded h-4 w-full" />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : tickets.length === 0 ? (
          /* Empty State */
          <div className="bg-white shadow rounded-lg text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">
              {hasActiveFilters ? 'No tickets match your filters' : 'No tickets found'}
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              {hasActiveFilters ? 'Try adjusting your filters' : 'Create your first ticket to get started.'}
            </p>
            <div className="mt-6">
              {hasActiveFilters ? (
                <button
                  onClick={clearFilters}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  Clear Filters
                </button>
              ) : (
                <Link
                  to="/tickets/new"
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                  + New Ticket
                </Link>
              )}
            </div>
          </div>
        ) : viewMode === 'cards' ? (
          /* Card View */
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {tickets.map((ticket) => (
              <TicketCard
                key={ticket.id}
                ticket={ticket}
                onClick={handleCardClick}
              />
            ))}
          </div>
        ) : (
          /* Table View */
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Ticket
                    </th>
                    <th className="hidden sm:table-cell px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Requester
                    </th>
                    <th className="hidden md:table-cell px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Assigned To
                    </th>
                    <th className="px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Priority
                    </th>
                    <th className="hidden sm:table-cell px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="hidden lg:table-cell px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Product
                    </th>
                    <th className="hidden lg:table-cell px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Category
                    </th>
                    <th className="px-3 py-2 sm:px-6 sm:py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tickets.map((ticket) => (
                    <tr
                      key={ticket.id}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => setPreviewTicketId(ticket.id)}
                    >
                      <td className="px-3 py-3 sm:px-6 sm:py-4">
                        <div className="text-sm font-medium text-blue-600 hover:text-blue-800">
                          #{ticket.id} - {ticket.title}
                        </div>
                        {ticket.is_overdue && (
                          <span className="text-xs text-red-600 font-medium">Overdue!</span>
                        )}
                        {ticket.revision_count > 0 && (
                          <span className="text-xs text-orange-600 ml-2">
                            ({ticket.revision_count} rev)
                          </span>
                        )}
                        {/* Show requester on mobile */}
                        <div className="sm:hidden text-xs text-gray-500 mt-1">
                          From: {ticket.requester?.first_name || ticket.requester?.username}
                        </div>
                      </td>
                      <td className="hidden sm:table-cell px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {ticket.requester?.first_name || ticket.requester?.username}
                        </div>
                      </td>
                      <td className="hidden md:table-cell px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {ticket.assigned_to
                            ? (() => {
                                const totalUsers = (ticket.assigned_to ? 1 : 0) + (ticket.collaborators?.length || 0);
                                return totalUsers === 1
                                  ? (ticket.assigned_to?.first_name || ticket.assigned_to?.username)
                                  : `${totalUsers} users`;
                              })()
                            : '-'}
                        </div>
                      </td>
                      <td className="px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(ticket.status)}`}>
                          {getStatusText(ticket.status)}
                        </span>
                      </td>
                      <td className="px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs rounded-full ${getPriorityColor(ticket.priority)}`}>
                          {ticket.priority}
                        </span>
                      </td>
                      <td className="hidden sm:table-cell px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(ticket.created_at)}
                      </td>
                      <td className="hidden lg:table-cell px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap text-sm text-gray-900">
                        {ticket.ticket_product?.name || ticket.product || '-'}
                      </td>
                      <td className="hidden lg:table-cell px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap">
                        {ticket.ticket_product?.category ? (
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            ticket.ticket_product.category === 'ads' ? 'bg-orange-100 text-orange-800' :
                            ticket.ticket_product.category === 'telegram' ? 'bg-sky-100 text-sky-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {ticket.ticket_product.category.charAt(0).toUpperCase() + ticket.ticket_product.category.slice(1)}
                          </span>
                        ) : '-'}
                      </td>
                      <td className="px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap text-center">
                        {(() => {
                          const perms = getTicketPermissions(ticket);
                          const isLoading = actionLoading === ticket.id;
                          const hasAction = perms.canApprove || perms.canReject || perms.canAssign || perms.canStart || perms.canComplete || perms.canRequestRevision;

                          if (!hasAction) {
                            return <span className="text-gray-400 text-xs">-</span>;
                          }

                          return (
                            <div className="flex items-center justify-center gap-1 flex-wrap">
                              {perms.canApprove && (
                                <button
                                  onClick={(e) => handleInlineAction(e, 'approve', ticket)}
                                  disabled={isLoading}
                                  className="px-2 py-1 text-xs font-medium text-green-700 bg-green-100 hover:bg-green-200 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                                  title="Approve"
                                >
                                  {isLoading ? '...' : '✓'}
                                </button>
                              )}
                              {perms.canReject && (
                                <button
                                  onClick={(e) => handleInlineAction(e, 'reject', ticket)}
                                  disabled={isLoading}
                                  className="px-2 py-1 text-xs font-medium text-red-700 bg-red-100 hover:bg-red-200 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                                  title="Reject"
                                >
                                  {isLoading ? '...' : '✗'}
                                </button>
                              )}
                              {perms.canAssign && (
                                <button
                                  onClick={(e) => handleInlineAction(e, 'assign', ticket)}
                                  disabled={isLoading}
                                  className="px-2 py-1 text-xs font-medium text-blue-700 bg-blue-100 hover:bg-blue-200 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                                  title="Assign"
                                >
                                  {isLoading ? '...' : 'Assign'}
                                </button>
                              )}
                              {perms.canStart && (
                                <button
                                  onClick={(e) => handleInlineAction(e, 'start', ticket)}
                                  disabled={isLoading}
                                  className="px-2 py-1 text-xs font-medium text-yellow-700 bg-yellow-100 hover:bg-yellow-200 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                                  title="Start Editing"
                                >
                                  {isLoading ? '...' : 'Start'}
                                </button>
                              )}
                              {perms.canComplete && (
                                <button
                                  onClick={(e) => handleInlineAction(e, 'complete', ticket)}
                                  disabled={isLoading}
                                  className="px-2 py-1 text-xs font-medium text-green-700 bg-green-100 hover:bg-green-200 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                                  title="Mark Complete"
                                >
                                  {isLoading ? '...' : 'Done'}
                                </button>
                              )}
                              {perms.canRequestRevision && (
                                <button
                                  onClick={(e) => handleInlineAction(e, 'revision', ticket)}
                                  disabled={isLoading}
                                  className="px-2 py-1 text-xs font-medium text-orange-700 bg-orange-100 hover:bg-orange-200 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                                  title="Request Revision"
                                >
                                  {isLoading ? '...' : 'Revise'}
                                </button>
                              )}
                            </div>
                          );
                        })()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Pagination Controls */}
        {!loading && paginationInfo.total_pages > 1 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white shadow rounded-lg px-4 py-3">
            <div className="text-sm text-gray-600">
              Page {paginationInfo.current_page} of {paginationInfo.total_pages}
            </div>
            <div className="flex items-center gap-2">
              {/* First Page */}
              <button
                onClick={() => handlePageChange(1)}
                disabled={paginationInfo.current_page === 1}
                className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                title="First Page"
              >
                ««
              </button>
              {/* Previous */}
              <button
                onClick={() => handlePageChange(paginationInfo.current_page - 1)}
                disabled={!paginationInfo.previous}
                className="px-4 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              {/* Page Numbers */}
              <div className="hidden sm:flex items-center gap-1">
                {(() => {
                  const pages = [];
                  const total = paginationInfo.total_pages;
                  const current = paginationInfo.current_page;
                  const maxVisible = 5;

                  let start = Math.max(1, current - Math.floor(maxVisible / 2));
                  let end = Math.min(total, start + maxVisible - 1);

                  if (end - start + 1 < maxVisible) {
                    start = Math.max(1, end - maxVisible + 1);
                  }

                  for (let i = start; i <= end; i++) {
                    pages.push(
                      <button
                        key={i}
                        onClick={() => handlePageChange(i)}
                        className={`px-3 py-1 text-sm font-medium rounded-md ${
                          i === current
                            ? 'bg-blue-600 text-white'
                            : 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        {i}
                      </button>
                    );
                  }
                  return pages;
                })()}
              </div>
              {/* Next */}
              <button
                onClick={() => handlePageChange(paginationInfo.current_page + 1)}
                disabled={!paginationInfo.next}
                className="px-4 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
              {/* Last Page */}
              <button
                onClick={() => handlePageChange(paginationInfo.total_pages)}
                disabled={paginationInfo.current_page === paginationInfo.total_pages}
                className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Last Page"
              >
                »»
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {previewTicketId && (
        <TicketPreviewModal
          ticketId={previewTicketId}
          onClose={() => setPreviewTicketId(null)}
          currentUser={user}
          isManager={isManager}
          users={users}
          onAction={handleTicketAction}
        />
      )}

      {/* Reject Modal */}
      {rejectModal.show && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black bg-opacity-50" onClick={() => setRejectModal({ show: false, ticketId: null })} />
            <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Reject Ticket</h3>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Enter rejection reason..."
                rows={3}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-red-500 focus:border-red-500"
              />
              <div className="flex justify-end gap-2 mt-4">
                <button
                  onClick={() => setRejectModal({ show: false, ticketId: null })}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRejectSubmit}
                  disabled={actionLoading === rejectModal.ticketId}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
                >
                  {actionLoading === rejectModal.ticketId ? 'Rejecting...' : 'Reject'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Assign Modal */}
      {assignModal.show && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black bg-opacity-50" onClick={() => setAssignModal({ show: false, ticketId: null })} />
            <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Assign Ticket</h3>
              <p className="text-sm text-gray-500 mb-3">Select Creative team members:</p>
              <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-md">
                {getCreativeMembers().length === 0 ? (
                  <p className="text-sm text-gray-500 p-3">No Creative members found</p>
                ) : (
                  getCreativeMembers().map((member) => (
                    <label
                      key={member.id}
                      className="flex items-center p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-0"
                    >
                      <input
                        type="checkbox"
                        checked={selectedAssignees.includes(member.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedAssignees([...selectedAssignees, member.id]);
                          } else {
                            setSelectedAssignees(selectedAssignees.filter(id => id !== member.id));
                          }
                        }}
                        className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <span className="ml-3 text-sm text-gray-700">
                        {member.first_name || member.username}
                        {member.role && <span className="text-gray-400 ml-1">({member.role})</span>}
                      </span>
                    </label>
                  ))
                )}
              </div>
              {selectedAssignees.length > 0 && (
                <p className="text-xs text-gray-500 mt-2">
                  {selectedAssignees.length} selected
                </p>
              )}
              <div className="flex justify-end gap-2 mt-4">
                <button
                  onClick={() => setAssignModal({ show: false, ticketId: null })}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAssignSubmit}
                  disabled={actionLoading === assignModal.ticketId || selectedAssignees.length === 0}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {actionLoading === assignModal.ticketId ? 'Assigning...' : 'Assign'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Scheduled Task Complete Modal */}
      {scheduledCompleteModal.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Complete {scheduledCompleteModal.ticket?.request_type?.replace('_', ' ')}
            </h3>
            <div className="space-y-4">
              {scheduledCompleteModal.ticket?.scheduled_start && (
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Scheduled Start:</span>{' '}
                  {new Date(scheduledCompleteModal.ticket.scheduled_start).toLocaleString()}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  When did the {scheduledCompleteModal.ticket?.request_type?.replace('_', ' ')} end?
                </label>
                <input
                  type="datetime-local"
                  value={actualEnd}
                  onChange={(e) => setActualEnd(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-green-500 focus:border-green-500"
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-2">
              <button
                onClick={() => {
                  setScheduledCompleteModal({ show: false, ticket: null });
                  setActualEnd('');
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleScheduledCompleteSubmit}
                disabled={actionLoading === scheduledCompleteModal.ticket?.id || !actualEnd}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {actionLoading === scheduledCompleteModal.ticket?.id ? 'Completing...' : 'Mark Complete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default TicketList;
