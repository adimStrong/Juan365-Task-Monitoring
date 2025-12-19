import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { activitiesAPI } from '../services/api';
import Layout from '../components/Layout';

const ActivityLog = () => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchActivities();
  }, []);

  const fetchActivities = async () => {
    try {
      const response = await activitiesAPI.list();
      setActivities(response.data.results || response.data);
    } catch (error) {
      console.error('Failed to fetch activities:', error);
    } finally {
      setLoading(false);
    }
  };

  const getActionIcon = (action) => {
    const icons = {
      created: '🆕',
      updated: '📝',
      approved: '✅',
      rejected: '❌',
      assigned: '👤',
      started: '▶️',
      completed: '🏁',
      commented: '💬',
      deleted: '🗑️',
    };
    return icons[action] || '📋';
  };

  const getActionColor = (action) => {
    const colors = {
      created: 'bg-blue-100 text-blue-800',
      updated: 'bg-gray-100 text-gray-800',
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
      assigned: 'bg-purple-100 text-purple-800',
      started: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
      commented: 'bg-blue-100 text-blue-800',
      deleted: 'bg-red-100 text-red-800',
    };
    return colors[action] || 'bg-gray-100 text-gray-800';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Activity Log</h1>
          <p className="text-sm text-gray-500">Recent activities on tickets</p>
        </div>

        {activities.length === 0 ? (
          <div className="bg-white shadow rounded-lg p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No activity yet</h3>
            <p className="mt-1 text-sm text-gray-500">Start working on tickets to see activity here.</p>
          </div>
        ) : (
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <div className="flow-root">
              <ul className="divide-y divide-gray-200">
                {activities.map((activity) => (
                  <li key={activity.id} className="p-4 hover:bg-gray-50">
                    <div className="flex items-start space-x-4">
                      <div className="flex-shrink-0 text-2xl">
                        {getActionIcon(activity.action)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-medium text-gray-900">
                            {activity.user?.first_name || activity.user?.username || 'System'}
                          </span>
                          <span className={`px-2 py-0.5 text-xs rounded-full ${getActionColor(activity.action)}`}>
                            {activity.action_display}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700 mt-1">
                          <Link
                            to={`/tickets/${activity.ticket}`}
                            className="text-blue-600 hover:text-blue-800"
                          >
                            #{activity.ticket} - {activity.ticket_title}
                          </Link>
                        </p>
                        {activity.details && (
                          <p className="text-sm text-gray-500 mt-1 italic">
                            "{activity.details}"
                          </p>
                        )}
                        <p className="text-xs text-gray-400 mt-1">
                          {formatDate(activity.created_at)}
                        </p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default ActivityLog;
