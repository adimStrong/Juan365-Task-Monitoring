import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ticketsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import TicketCard from '../components/TicketCard';
import TicketPreviewModal from '../components/TicketPreviewModal';

const TicketList = () => {
  const { isManager } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState('table'); // 'table' or 'cards'
  const [previewTicketId, setPreviewTicketId] = useState(null);

  // Filters from URL
  const statusFilter = searchParams.get('status') || '';
  const priorityFilter = searchParams.get('priority') || '';
  const searchQuery = searchParams.get('search') || '';
  const dateFrom = searchParams.get('date_from') || '';
  const dateTo = searchParams.get('date_to') || '';

  useEffect(() => {
    fetchTickets();
  }, [statusFilter, priorityFilter, searchQuery, dateFrom, dateTo]);

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
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (priorityFilter) params.priority = priorityFilter;
      if (searchQuery) params.search = searchQuery;
      if (dateFrom) params.created_after = dateFrom;
      if (dateTo) params.created_before = dateTo;

      const response = await ticketsAPI.list(params);
      setTickets(response.data.results || response.data);
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
    setSearchParams(searchParams);
  };

  const clearFilters = () => {
    setSearchParams({});
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
      rejected: 'bg-red-100 text-red-800',
      in_progress: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getStatusText = (status) => {
    const texts = {
      requested: 'For Dept Approval',
      pending_creative: 'For Creative Approval',
      approved: 'Approved',
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
                value={searchQuery}
                onChange={(e) => handleFilterChange('search', e.target.value)}
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

        {/* Results count */}
        {!loading && (
          <div className="text-sm text-gray-500">
            Showing {tickets.length} ticket{tickets.length !== 1 ? 's' : ''}
            {hasActiveFilters && ' (filtered)'}
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="bg-white shadow rounded-lg flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
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
                          {ticket.assigned_to?.first_name || ticket.assigned_to?.username || '-'}
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
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {previewTicketId && (
        <TicketPreviewModal
          ticketId={previewTicketId}
          onClose={() => setPreviewTicketId(null)}
        />
      )}
    </Layout>
  );
};

export default TicketList;
