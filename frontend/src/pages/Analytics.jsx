import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { useAnalytics, useAnalyticsDateRange } from '../hooks/useQueries';

const Analytics = () => {
  const navigate = useNavigate();
  const { user, isManager } = useAuth();

  // Date filter state
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [appliedDateFrom, setAppliedDateFrom] = useState('');
  const [appliedDateTo, setAppliedDateTo] = useState('');

  // Leaderboard state
  const [leaderboardCategory, setLeaderboardCategory] = useState('total');
  const [leaderboardTopN, setLeaderboardTopN] = useState(10);

  // Pagination state for user performance table
  const [performancePage, setPerformancePage] = useState(1);
  const [performancePerPage, setPerformancePerPage] = useState(10);

  // Fetch date range first (cached for 10 minutes)
  const { data: dateRange, isLoading: dateRangeLoading } = useAnalyticsDateRange();

  // Fetch analytics data with React Query (cached for 5 minutes)
  const {
    data: analytics,
    isLoading: analyticsLoading,
    error: analyticsError,
    isFetching
  } = useAnalytics(appliedDateFrom, appliedDateTo, !!appliedDateFrom && !!appliedDateTo);

  const minDate = dateRange?.minDate || '';
  const maxDate = dateRange?.maxDate || '';
  const loading = dateRangeLoading || (analyticsLoading && !analytics);
  const error = analyticsError ? 'Failed to load analytics data' : null;

  // Initialize dates when date range is loaded
  useEffect(() => {
    if (maxDate && !appliedDateFrom && !appliedDateTo) {
      setDateFrom(maxDate);
      setDateTo(maxDate);
      setAppliedDateFrom(maxDate);
      setAppliedDateTo(maxDate);
    }
  }, [maxDate, appliedDateFrom, appliedDateTo]);

  // Redirect non-managers
  useEffect(() => {
    if (!isManager) {
      navigate('/');
    }
  }, [isManager, navigate]);

  // Paginated user performance data
  const paginatedPerformance = useMemo(() => {
    if (!analytics?.user_performance) return { data: [], total: 0, totalPages: 0 };

    const filtered = analytics.user_performance.filter(u => u.total_assigned > 0);
    const total = filtered.length;
    const totalPages = Math.ceil(total / performancePerPage);
    const start = (performancePage - 1) * performancePerPage;
    const data = filtered.slice(start, start + performancePerPage);

    return { data, total, totalPages };
  }, [analytics?.user_performance, performancePage, performancePerPage]);

  // Reset to page 1 when per-page changes
  useEffect(() => {
    setPerformancePage(1);
  }, [performancePerPage]);

  const handleFilter = (e) => {
    e.preventDefault();
    setAppliedDateFrom(dateFrom);
    setAppliedDateTo(dateTo);
  };

  const clearFilters = () => {
    setDateFrom(maxDate);
    setDateTo(maxDate);
    setAppliedDateFrom(maxDate);
    setAppliedDateTo(maxDate);
  };

  const formatHours = (hours) => {
    // Format hours with detail: Xh Ym or Xm Ys
    if (hours === null || hours === undefined) return '-';
    const totalSeconds = Math.round(hours * 3600);
    if (totalSeconds < 60) return `${totalSeconds}s`;
    if (totalSeconds < 3600) {
      const mins = Math.floor(totalSeconds / 60);
      const secs = totalSeconds % 60;
      return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
    }
    const hrs = Math.floor(totalSeconds / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    return mins > 0 ? `${hrs}h ${mins}m` : `${hrs}h`;
  };

  const formatSeconds = (seconds) => {
    // Format seconds with detail: Xh Ym or Xm Ys
    if (seconds === null || seconds === undefined) return '-';
    seconds = Math.round(seconds);
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
    }
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return mins > 0 ? `${hrs}h ${mins}m` : `${hrs}h`;
  };

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-';
    return num.toLocaleString();
  };

  if (!isManager) {
    return null;
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
            <p className="text-gray-500 mt-1">Track team performance and ticket processing metrics</p>
          </div>
        </div>

        {/* Date Filter */}
        <div className="bg-white rounded-lg shadow-sm p-4">
          <form onSubmit={handleFilter} className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                min={minDate}
                max={dateTo || maxDate}
                disabled={!minDate}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                min={dateFrom || minDate}
                max={maxDate}
                disabled={!maxDate}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>
            <button
              type="submit"
              disabled={!minDate || isFetching}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isFetching && (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              )}
              Apply Filter
            </button>
            {(dateFrom !== maxDate || dateTo !== maxDate) && (
              <button
                type="button"
                onClick={clearFilters}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Clear
              </button>
            )}
            {/* Background refresh indicator */}
            {isFetching && analytics && (
              <span className="text-sm text-blue-600 flex items-center gap-1">
                <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Updating...
              </span>
            )}
          </form>
          {minDate && maxDate && (
            <p className="mt-2 text-xs text-gray-500">
              Data available from <span className="font-medium">{minDate}</span> to <span className="font-medium">{maxDate}</span>
              {analytics && <span className="ml-2 text-green-600">(Cached - instant load on revisit)</span>}
            </p>
          )}
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center h-64 space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            <div className="text-center">
              <p className="text-gray-600 font-medium">Loading Analytics...</p>
              <p className="text-sm text-gray-400 mt-1">Please wait while we calculate metrics from your data</p>
            </div>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            {error}
          </div>
        ) : analytics ? (
          <>
            {/* Overall Statistics - All Time */}
            {analytics.overall && (
              <div className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-xl shadow-lg p-6 mb-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-bold text-white">Overall Statistics</h2>
                    <p className="text-slate-300 text-sm">All-time metrics (not affected by date filter)</p>
                  </div>
                  <div className="bg-slate-600 px-3 py-1 rounded-full">
                    <span className="text-emerald-400 font-semibold">ALL TIME</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <p className="text-slate-400 text-xs uppercase tracking-wide">Total Tickets</p>
                    <p className="text-2xl font-bold text-white mt-1">{formatNumber(analytics.overall.total_tickets)}</p>
                    <p className="text-xs text-slate-400">{formatNumber(analytics.overall.completed_tickets)} completed</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <p className="text-slate-400 text-xs uppercase tracking-wide">Total Output</p>
                    <p className="text-2xl font-bold text-emerald-400 mt-1">{formatNumber(analytics.overall.total_quantity_produced)}</p>
                    <p className="text-xs text-slate-400">creatives produced</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <p className="text-slate-400 text-xs uppercase tracking-wide">Video Output</p>
                    <p className="text-2xl font-bold text-blue-400 mt-1">{formatNumber(analytics.overall.video_quantity || 0)}</p>
                    <p className="text-xs text-slate-400">video creatives</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <p className="text-slate-400 text-xs uppercase tracking-wide">Image Output</p>
                    <p className="text-2xl font-bold text-pink-400 mt-1">{formatNumber(analytics.overall.image_quantity || 0)}</p>
                    <p className="text-xs text-slate-400">image creatives</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <p className="text-slate-400 text-xs uppercase tracking-wide">Avg Time/Creative</p>
                    <p className="text-2xl font-bold text-amber-400 mt-1">{formatSeconds(analytics.overall.avg_time_per_creative_seconds)}</p>
                    <p className="text-xs text-slate-400">processing time</p>
                  </div>
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <p className="text-slate-400 text-xs uppercase tracking-wide">Completion Rate</p>
                    <p className="text-2xl font-bold text-green-400 mt-1">{analytics.overall.completion_rate}%</p>
                    <p className="text-xs text-slate-400">of assigned</p>
                  </div>
                </div>
              </div>
            )}

            {/* Summary Cards - Row 1 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Total Tickets</p>
                    <div className="flex items-baseline space-x-3">
                      <p className="text-3xl font-bold text-gray-900">{analytics.summary.total_tickets}</p>
                      <p className="text-lg text-blue-600 font-semibold">({analytics.summary.assigned_tickets || 0} assigned)</p>
                    </div>
                  </div>
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  {analytics.summary.completed_tickets} completed
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Completion Rate</p>
                    <p className="text-3xl font-bold text-green-600">{analytics.summary.completion_rate}%</p>
                  </div>
                  <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full"
                      style={{ width: `${analytics.summary.completion_rate}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-400 mt-1">
                    {analytics.summary.completed_tickets} of {analytics.summary.assigned_tickets || 0} assigned
                  </p>
                </div>
              </div>

              {/* NEW: Total Output */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Total Output</p>
                    <p className="text-3xl font-bold text-indigo-600">{analytics.summary.total_quantity_produced || 0}</p>
                  </div>
                  <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  Total creatives produced
                </div>
              </div>

              {/* NEW: Avg Quantity per Ticket */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Avg Output/Ticket</p>
                    <p className="text-3xl font-bold text-teal-600">{analytics.summary.avg_quantity_per_ticket || 0}</p>
                  </div>
                  <div className="w-12 h-12 bg-teal-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  Creatives per completed ticket
                </div>
              </div>
            </div>

            {/* Summary Cards - Row 2 (Time metrics) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Avg Time Per Creative */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Avg Time Per Creative</p>
                    <p className="text-3xl font-bold text-purple-600">{formatSeconds(analytics.summary.avg_time_per_creative_seconds)}</p>
                  </div>
                  <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  Processing time per unit
                </div>
              </div>

              {/* Avg Video Creation Time */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Avg Video Creation Time</p>
                    <p className="text-3xl font-bold text-blue-600">{formatSeconds(analytics.summary.avg_video_creation_seconds)}</p>
                  </div>
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  Time per video creative
                </div>
              </div>

              {/* Avg Image Creation Time */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Avg Image Creation Time</p>
                    <p className="text-3xl font-bold text-pink-600">{formatSeconds(analytics.summary.avg_image_creation_seconds)}</p>
                  </div>
                  <div className="w-12 h-12 bg-pink-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-pink-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  Time per image creative
                </div>
              </div>

              {/* Avg Acknowledge Time */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Avg Acknowledge Time</p>
                    <p className="text-3xl font-bold text-orange-600">{formatSeconds(analytics.summary.avg_acknowledge_seconds)}</p>
                  </div>
                  <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  Assignment to start editing
                </div>
              </div>
            </div>

            {/* Revision Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Revision Statistics</h3>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Tickets with Revisions</p>
                    <p className="text-2xl font-bold text-gray-900">{analytics.summary.tickets_with_revisions}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Revision Rate</p>
                    <p className="text-2xl font-bold text-red-600">{analytics.summary.revision_rate}%</p>
                  </div>
                </div>
                <div className="mt-4">
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-red-500 h-3 rounded-full"
                      style={{ width: `${Math.min(analytics.summary.revision_rate, 100)}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Lower is better - indicates first-time accuracy</p>
                </div>
              </div>

              {/* Priority Breakdown */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">By Priority</h3>
                <div className="space-y-3">
                  {analytics.by_priority.map((stat) => (
                    <div key={stat.priority} className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <span className={`w-3 h-3 rounded-full ${
                          stat.priority === 'urgent' ? 'bg-red-500' :
                          stat.priority === 'high' ? 'bg-orange-500' :
                          stat.priority === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                        }`} />
                        <span className="text-sm font-medium text-gray-700">{stat.display_name}</span>
                      </div>
                      <div className="flex items-center space-x-4 text-sm">
                        <span className="text-gray-500">{stat.total} tickets</span>
                        <span className="text-gray-500">Avg: {formatSeconds(stat.avg_processing_seconds)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* User Performance Table */}
            <div className="bg-white rounded-lg shadow-sm">
              <div className="px-6 py-4 border-b flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Team Performance</h3>
                  <p className="text-sm text-gray-500">Designer productivity metrics</p>
                </div>
                {/* Per-page filter */}
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-600">Show:</label>
                  <select
                    value={performancePerPage}
                    onChange={(e) => setPerformancePerPage(Number(e.target.value))}
                    className="px-2 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value={5}>5</option>
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                    <option value={999}>All</option>
                  </select>
                  <span className="text-sm text-gray-500">
                    ({paginatedPerformance.total} total)
                  </span>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-2 py-2 text-left font-medium text-gray-500 text-xs">User</th>
                      <th className="px-2 py-2 text-left font-medium text-gray-500 text-xs">Role</th>
                      <th className="px-2 py-2 text-center font-medium text-gray-500 text-xs">Assigned</th>
                      <th className="px-2 py-2 text-center font-medium text-gray-500 text-xs">Assigned<br/>Qty</th>
                      <th className="px-2 py-2 text-center font-medium text-gray-500 text-xs">Completed</th>
                      <th className="px-2 py-2 text-center font-medium text-gray-500 text-xs">Output</th>
                      <th className="px-2 py-2 text-center font-medium text-gray-500 text-xs">In<br/>Progress</th>
                      <th className="px-2 py-2 text-center font-medium text-gray-500 text-xs">Completion<br/>Rate</th>
                      <th className="px-2 py-2 text-center font-medium text-gray-500 text-xs">Processing<br/>Time</th>
                      <th className="px-2 py-2 text-center font-medium text-gray-500 text-xs">Avg Ack<br/>Time</th>
                      <th className="px-2 py-2 text-center font-medium text-gray-500 text-xs">Avg Video<br/>Time</th>
                      <th className="px-2 py-2 text-center font-medium text-gray-500 text-xs">Avg Image<br/>Time</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {/* Summary Row - always visible */}
                    {analytics.user_totals && (
                      <tr className="bg-gray-100 font-semibold">
                        <td className="px-2 py-1.5 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="w-6 h-6 bg-gray-700 rounded-full flex items-center justify-center text-white text-sm font-medium">
                              T
                            </div>
                            <div className="ml-3">
                              <div className="text-sm font-bold text-gray-900">TOTAL</div>
                              
                            </div>
                          </div>
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap">
                          <span className="px-2 py-1 text-xs rounded-full bg-gray-200 text-gray-700">
                            Summary
                          </span>
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-gray-900 font-bold">
                          {analytics.user_totals.total_assigned}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-blue-600 font-bold">
                          {analytics.user_totals.assigned_output || 0}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-green-600 font-bold">
                          {analytics.user_totals.completed}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-indigo-600 font-bold">
                          {analytics.user_totals.total_output || 0}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-yellow-600 font-bold">
                          {analytics.user_totals.in_progress}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center">
                          <span className="text-sm font-bold text-gray-900">
                            {analytics.summary.completion_rate}%
                          </span>
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-gray-900 font-bold">
                          {formatSeconds(analytics.summary.avg_processing_seconds)}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-orange-600 font-bold">
                          {formatSeconds(analytics.summary.avg_acknowledge_seconds)}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-blue-600 font-bold">
                          {formatSeconds(analytics.summary.avg_video_creation_seconds)}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-pink-600 font-bold">
                          {formatSeconds(analytics.summary.avg_image_creation_seconds)}
                        </td>
                      </tr>
                    )}
                    {paginatedPerformance.data.map((user) => (
                      <tr key={user.user_id} className="hover:bg-gray-50">
                        <td className="px-2 py-1.5 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                              {user.full_name?.[0]?.toUpperCase() || user.username?.[0]?.toUpperCase()}
                            </div>
                            <div className="ml-3">
                              <div className="text-sm font-medium text-gray-900">{user.full_name || user.username}</div>

                            </div>
                          </div>
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            user.role === 'admin' ? 'bg-red-100 text-red-800' :
                            user.role === 'manager' ? 'bg-purple-100 text-purple-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {user.role === 'manager' ? 'Approver' : user.role}
                          </span>
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-gray-900">
                          {user.total_assigned}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-blue-600">
                          {user.assigned_output || 0}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-green-600 font-medium">
                          {user.completed}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-indigo-600 font-medium">
                          {user.total_output || 0}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-yellow-600">
                          {user.in_progress}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center">
                          <div className="flex items-center justify-center">
                            <span className={`text-sm font-medium ${
                              user.completion_rate >= 80 ? 'text-green-600' :
                              user.completion_rate >= 50 ? 'text-yellow-600' : 'text-red-600'
                            }`}>
                              {user.completion_rate}%
                            </span>
                          </div>
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-gray-900">
                          {formatSeconds(user.avg_processing_seconds)}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-orange-600">
                          {formatSeconds(user.avg_acknowledge_seconds)}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-blue-600">
                          {formatSeconds(user.avg_video_creation_seconds)}
                        </td>
                        <td className="px-2 py-1.5 whitespace-nowrap text-center text-sm text-pink-600">
                          {formatSeconds(user.avg_image_creation_seconds)}
                        </td>
                      </tr>
                    ))}
                    {paginatedPerformance.data.length === 0 && (
                      <tr>
                        <td colSpan="12" className="px-6 py-8 text-center text-gray-500">
                          No user performance data available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {/* Pagination Controls */}
              {paginatedPerformance.totalPages > 1 && (
                <div className="px-6 py-3 border-t bg-gray-50 flex flex-col sm:flex-row justify-between items-center gap-3">
                  <span className="text-sm text-gray-600">
                    Showing {((performancePage - 1) * performancePerPage) + 1} - {Math.min(performancePage * performancePerPage, paginatedPerformance.total)} of {paginatedPerformance.total}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setPerformancePage(1)}
                      disabled={performancePage === 1}
                      className="px-2 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      First
                    </button>
                    <button
                      onClick={() => setPerformancePage(p => Math.max(1, p - 1))}
                      disabled={performancePage === 1}
                      className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Prev
                    </button>
                    <span className="px-3 py-1 text-sm">
                      Page {performancePage} of {paginatedPerformance.totalPages}
                    </span>
                    <button
                      onClick={() => setPerformancePage(p => Math.min(paginatedPerformance.totalPages, p + 1))}
                      disabled={performancePage === paginatedPerformance.totalPages}
                      className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                    <button
                      onClick={() => setPerformancePage(paginatedPerformance.totalPages)}
                      disabled={performancePage === paginatedPerformance.totalPages}
                      className="px-2 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Last
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Breakdown Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* By Request Type */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">By Request Type</h3>
                {analytics.by_request_type.length > 0 ? (
                  <div className="space-y-3">
                    {analytics.by_request_type.map((stat) => (
                      <div key={stat.request_type}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700">{stat.display_name}</span>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-gray-500">{stat.count} tickets</span>
                            <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">
                              {stat.total_quantity || 0} qty
                            </span>
                          </div>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-indigo-500 h-2 rounded-full"
                            style={{
                              width: `${(stat.count / analytics.summary.total_tickets) * 100}%`
                            }}
                          />
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                          <span>{stat.completed} completed</span>
                          <span>Avg revisions: {stat.avg_revisions?.toFixed(1) || 0}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">No request type data available</p>
                )}
              </div>

              {/* By Department */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">By Department</h3>
                {analytics.by_department.length > 0 ? (
                  <div className="space-y-3">
                    {analytics.by_department.map((stat) => (
                      <div key={stat.department}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700">{stat.department}</span>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-gray-500">{stat.count} tickets</span>
                            <span className="text-xs bg-cyan-100 text-cyan-700 px-2 py-0.5 rounded-full">
                              {stat.total_quantity || 0} qty
                            </span>
                          </div>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-cyan-500 h-2 rounded-full"
                            style={{
                              width: `${(stat.count / analytics.summary.total_tickets) * 100}%`
                            }}
                          />
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                          <span>{stat.completed} completed ({stat.completed_quantity || 0} qty)</span>
                          <span>{stat.in_progress} in progress</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">No department data available</p>
                )}
              </div>

              {/* By Product */}
              <div className="bg-white rounded-lg shadow-sm p-6 lg:col-span-2">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">By Product</h3>
                {analytics.by_product.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {analytics.by_product.map((stat) => (
                      <div key={stat.product} className="border rounded-lg p-3">
                        <h4 className="font-medium text-gray-900 text-sm truncate">{stat.product}</h4>
                        <div className="mt-1 flex items-baseline space-x-2">
                          <span className="text-xl font-bold text-gray-900">{stat.total_quantity ?? 0}</span>
                          <span className="text-xs text-gray-500">creatives</span>
                          <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full">{stat.count} tickets</span>
                        </div>
                        <div className="mt-1 flex items-center justify-between text-xs">
                          <span className="text-green-600">{stat.completed_quantity ?? 0} done</span>
                          <span className="text-yellow-600">{stat.in_progress} active</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">No product data available</p>
                )}
              </div>

              {/* By Criteria (Image vs Video) */}
              {analytics.by_criteria && analytics.by_criteria.length > 0 && (
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">By Criteria (Image vs Video)</h3>
                  <div className="space-y-4">
                    {analytics.by_criteria.map((stat) => (
                      <div key={stat.criteria}>
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <span className={`w-3 h-3 rounded-full ${stat.criteria === 'image' ? 'bg-pink-500' : 'bg-blue-500'}`} />
                            <span className="text-sm font-medium text-gray-700">{stat.display_name}</span>
                          </div>
                          <div className="text-right">
                            <span className="text-sm text-gray-500">{stat.count} tickets</span>
                            <span className="text-xs text-gray-400 ml-2">({stat.total_quantity || 0} qty)</span>
                          </div>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-3">
                          <div
                            className={`h-3 rounded-full ${stat.criteria === 'image' ? 'bg-pink-500' : 'bg-blue-500'}`}
                            style={{ width: `${(stat.count / analytics.summary.total_tickets) * 100}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                          <span>{stat.completed} completed</span>
                          <span>{stat.completed_quantity || 0} qty completed</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Top N Leaderboard */}
              {analytics.rankings && (
                <div className="bg-white rounded-lg shadow-sm p-6 col-span-full">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                    <h3 className="text-lg font-semibold text-gray-900">Top Performers Leaderboard</h3>
                    <div className="flex flex-wrap items-center gap-3">
                      {/* Category Filter */}
                      <div className="flex items-center gap-2">
                        <label className="text-sm text-gray-600">Category:</label>
                        <select
                          value={leaderboardCategory}
                          onChange={(e) => setLeaderboardCategory(e.target.value)}
                          className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="total">All Output</option>
                          <option value="video">Video</option>
                          <option value="image">Image/Banner</option>
                          <option value="others">Others</option>
                        </select>
                      </div>
                      {/* Top N Filter */}
                      <div className="flex items-center gap-2">
                        <label className="text-sm text-gray-600">Show Top:</label>
                        <select
                          value={leaderboardTopN}
                          onChange={(e) => setLeaderboardTopN(Number(e.target.value))}
                          className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value={5}>5</option>
                          <option value={10}>10</option>
                          <option value={15}>15</option>
                          <option value={20}>20</option>
                          <option value={999}>All</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Leaderboard Table */}
                  {(() => {
                    const rankingKey = `by_${leaderboardCategory}`;
                    const rankingData = analytics.rankings[rankingKey] || [];
                    const displayData = rankingData.slice(0, leaderboardTopN);
                    const outputKey = leaderboardCategory === 'total' ? 'total_output' : `${leaderboardCategory}_output`;
                    const categoryLabel = {
                      total: 'Total Output',
                      video: 'Video Output',
                      image: 'Image/Banner Output',
                      others: 'Others Output'
                    }[leaderboardCategory];
                    const categoryStyles = {
                      total: { text: 'text-blue-600', bg: 'bg-blue-500' },
                      video: { text: 'text-purple-600', bg: 'bg-purple-500' },
                      image: { text: 'text-pink-600', bg: 'bg-pink-500' },
                      others: { text: 'text-amber-600', bg: 'bg-amber-500' }
                    }[leaderboardCategory];

                    if (displayData.length === 0) {
                      return (
                        <p className="text-gray-500 text-center py-8">No data available for this category</p>
                      );
                    }

                    const maxOutput = displayData[0]?.[outputKey] || 1;

                    return (
                      <div className="space-y-3">
                        {displayData.map((user, index) => {
                          const output = user[outputKey] || 0;
                          const percentage = (output / maxOutput) * 100;
                          const isTop3 = index < 3;
                          const medalColors = ['bg-yellow-400', 'bg-gray-300', 'bg-amber-600'];
                          const medalEmojis = ['🥇', '🥈', '🥉'];

                          return (
                            <div
                              key={user.user_id}
                              className={`flex items-center gap-4 p-3 rounded-lg ${
                                isTop3 ? 'bg-gradient-to-r from-gray-50 to-white border border-gray-200' : 'bg-gray-50'
                              }`}
                            >
                              {/* Rank */}
                              <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg ${
                                isTop3 ? `${medalColors[index]} text-white` : 'bg-gray-200 text-gray-600'
                              }`}>
                                {isTop3 ? medalEmojis[index] : user.rank}
                              </div>

                              {/* User Info */}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between mb-1">
                                  <div>
                                    <span className={`font-medium ${isTop3 ? 'text-gray-900' : 'text-gray-700'}`}>
                                      {user.full_name}
                                    </span>
                                    {user.department && (
                                      <span className="text-xs text-gray-400 ml-2">({user.department})</span>
                                    )}
                                  </div>
                                  <span className={`font-bold text-lg ${categoryStyles.text}`}>
                                    {output.toLocaleString()}
                                  </span>
                                </div>
                                {/* Progress Bar */}
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                  <div
                                    className={`h-2 rounded-full ${categoryStyles.bg} transition-all duration-300`}
                                    style={{ width: `${percentage}%` }}
                                  />
                                </div>
                                {/* Additional Stats */}
                                <div className="flex gap-4 mt-1 text-xs text-gray-500">
                                  <span>Completed: {user.completed}</span>
                                  <span>Rate: {user.completion_rate}%</span>
                                  {leaderboardCategory === 'total' && (
                                    <>
                                      <span className="text-purple-500">Video: {user.video_output || 0}</span>
                                      <span className="text-pink-500">Image: {user.image_output || 0}</span>
                                    </>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}

                        {/* Summary */}
                        <div className="mt-4 pt-4 border-t border-gray-200 flex justify-between text-sm text-gray-600">
                          <span>Showing {displayData.length} of {rankingData.length} agents</span>
                          <span className="font-medium">
                            Team Total: {rankingData.reduce((sum, u) => sum + (u[outputKey] || 0), 0).toLocaleString()} {categoryLabel.toLowerCase()}
                          </span>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* Ads Product Output */}
              {analytics.ads_product_output && analytics.ads_product_output.length > 0 && (
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Ads Product Output</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {analytics.ads_product_output.map((stat) => (
                      <div key={stat.product_name} className="border border-orange-200 bg-orange-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 text-sm truncate">{stat.product_name}</h4>
                        <div className="mt-2 flex items-baseline space-x-2">
                          <span className="text-2xl font-bold text-orange-600">{stat.total_quantity}</span>
                          <span className="text-xs text-gray-500">total qty</span>
                        </div>
                        <div className="mt-1 flex items-center justify-between text-xs">
                          <span className="text-green-600">{stat.completed_quantity} completed</span>
                          <span className="text-gray-500">{stat.ticket_count} tickets</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Telegram Product Output */}
              {analytics.telegram_product_output && analytics.telegram_product_output.length > 0 && (
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Telegram Product Output</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {analytics.telegram_product_output.map((stat) => (
                      <div key={stat.product_name} className="border border-sky-200 bg-sky-50 rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 text-sm truncate">{stat.product_name}</h4>
                        <div className="mt-2 flex items-baseline space-x-2">
                          <span className="text-2xl font-bold text-sky-600">{stat.total_quantity}</span>
                          <span className="text-xs text-gray-500">total qty</span>
                        </div>
                        <div className="mt-1 flex items-center justify-between text-xs">
                          <span className="text-green-600">{stat.completed_quantity} completed</span>
                          <span className="text-gray-500">{stat.ticket_count} tickets</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </Layout>
  );
};

export default Analytics;




