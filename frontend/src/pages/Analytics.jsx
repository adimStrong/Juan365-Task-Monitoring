import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { analyticsAPI } from '../services/api';

const Analytics = () => {
  const navigate = useNavigate();
  const { user, isManager } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [minDate, setMinDate] = useState('');
  const [maxDate, setMaxDate] = useState('');

  // Redirect non-managers
  useEffect(() => {
    if (!isManager) {
      navigate('/');
    }
  }, [isManager, navigate]);

  useEffect(() => {
    if (isManager) {
      fetchAnalytics(true); // Initial load - set default dates
    }
  }, [isManager]);

  const fetchAnalytics = async (isInitialLoad = false) => {
    setLoading(true);
    setError(null);
    try {
      // First fetch to get date range (without filters on initial load)
      const params = {};
      if (!isInitialLoad) {
        if (dateFrom) params.date_from = dateFrom;
        if (dateTo) params.date_to = dateTo;
      }

      const response = await analyticsAPI.getAnalytics(params);

      // Set min/max date constraints from API response
      if (response.data.date_range) {
        const newMinDate = response.data.date_range.min_date || '';
        const newMaxDate = response.data.date_range.max_date || '';
        setMinDate(newMinDate);
        setMaxDate(newMaxDate);

        // On initial load, default both date pickers to the latest date and refetch
        if (isInitialLoad && newMaxDate) {
          setDateFrom(newMaxDate);
          setDateTo(newMaxDate);
          // Fetch again with the latest date filter
          const filteredResponse = await analyticsAPI.getAnalytics({
            date_from: newMaxDate,
            date_to: newMaxDate
          });
          setAnalytics(filteredResponse.data);
          setLoading(false);
          return;
        }
      }

      setAnalytics(response.data);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
      setError('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const handleFilter = (e) => {
    e.preventDefault();
    fetchAnalytics();
  };

  const clearFilters = () => {
    setDateFrom('');
    setDateTo('');
    fetchAnalytics();
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
              disabled={!minDate}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Apply Filter
            </button>
            {(dateFrom || dateTo) && (
              <button
                type="button"
                onClick={clearFilters}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Clear
              </button>
            )}
          </form>
          {minDate && maxDate && (
            <p className="mt-2 text-xs text-gray-500">
              Data available from <span className="font-medium">{minDate}</span> to <span className="font-medium">{maxDate}</span>
            </p>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            {error}
          </div>
        ) : analytics ? (
          <>
            {/* Summary Cards - Row 1 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Total Tickets</p>
                    <p className="text-3xl font-bold text-gray-900">{analytics.summary.total_tickets}</p>
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
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Avg Processing Time</p>
                    <p className="text-3xl font-bold text-purple-600">{formatSeconds(analytics.summary.avg_processing_seconds)}</p>
                  </div>
                  <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  From start to completion
                </div>
              </div>

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
                  From assignment to start editing
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
              <div className="px-6 py-4 border-b">
                <h3 className="text-lg font-semibold text-gray-900">Team Performance</h3>
                <p className="text-sm text-gray-500">Designer productivity metrics</p>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        User
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Role
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Assigned
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Assigned Qty
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Completed
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Output
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        In Progress
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Completion Rate
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Avg Processing
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Avg Ack Time
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {analytics.user_performance.filter(u => u.total_assigned > 0).map((user) => (
                      <tr key={user.user_id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                              {user.full_name?.[0]?.toUpperCase() || user.username?.[0]?.toUpperCase()}
                            </div>
                            <div className="ml-3">
                              <div className="text-sm font-medium text-gray-900">{user.full_name || user.username}</div>
                              <div className="text-xs text-gray-500">{user.department}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            user.role === 'admin' ? 'bg-red-100 text-red-800' :
                            user.role === 'manager' ? 'bg-purple-100 text-purple-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {user.role === 'manager' ? 'Approver' : user.role}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                          {user.total_assigned}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-blue-600">
                          {user.assigned_output || 0}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-green-600 font-medium">
                          {user.completed}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-indigo-600 font-medium">
                          {user.total_output || 0}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-yellow-600">
                          {user.in_progress}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                          <div className="flex items-center justify-center">
                            <span className={`text-sm font-medium ${
                              user.completion_rate >= 80 ? 'text-green-600' :
                              user.completion_rate >= 50 ? 'text-yellow-600' : 'text-red-600'
                            }`}>
                              {user.completion_rate}%
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                          {formatSeconds(user.avg_processing_seconds)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-orange-600">
                          {formatSeconds(user.avg_acknowledge_seconds)}
                        </td>
                      </tr>
                    ))}
                    {analytics.user_performance.filter(u => u.total_assigned > 0).length === 0 && (
                      <tr>
                        <td colSpan="10" className="px-6 py-8 text-center text-gray-500">
                          No user performance data available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
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
                          <span className="text-sm text-gray-500">{stat.count} tickets</span>
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
                          <span>{stat.completed} completed</span>
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
                      <div key={stat.product} className="border rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 truncate">{stat.product}</h4>
                        <div className="mt-2 flex items-baseline space-x-2">
                          <span className="text-2xl font-bold text-gray-900">{stat.count}</span>
                          <span className="text-sm text-gray-500">tickets</span>
                        </div>
                        <div className="mt-2 flex items-center justify-between text-sm">
                          <span className="text-green-600">{stat.completed} done</span>
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
