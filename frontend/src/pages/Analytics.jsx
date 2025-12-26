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

  // Redirect non-managers
  useEffect(() => {
    if (!isManager) {
      navigate('/');
    }
  }, [isManager, navigate]);

  useEffect(() => {
    if (isManager) {
      fetchAnalytics();
    }
  }, [isManager]);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const response = await analyticsAPI.getAnalytics(params);
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
    if (!hours) return '-';
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    return `${hours}h`;
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
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
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
            {/* Summary Cards */}
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

              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">Avg Processing Time</p>
                    <p className="text-3xl font-bold text-purple-600">{formatHours(analytics.summary.avg_processing_hours)}</p>
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
                    <p className="text-3xl font-bold text-orange-600">{formatHours(analytics.summary.avg_acknowledge_hours)}</p>
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
                        <span className="text-gray-500">Avg: {formatHours(stat.avg_processing_hours)}</span>
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
                        Completed
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
                            {user.role}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                          {user.total_assigned}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-green-600 font-medium">
                          {user.completed}
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
                          {formatHours(user.avg_processing_hours)}
                        </td>
                      </tr>
                    ))}
                    {analytics.user_performance.filter(u => u.total_assigned > 0).length === 0 && (
                      <tr>
                        <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
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
                          <span className="text-sm text-gray-500">{stat.count} tickets</span>
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
            </div>
          </>
        ) : null}
      </div>
    </Layout>
  );
};

export default Analytics;
