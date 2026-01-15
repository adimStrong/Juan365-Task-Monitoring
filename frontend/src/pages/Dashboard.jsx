import { useState, useEffect, lazy, Suspense } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { useDashboardStats, useMyTasks, usePendingApprovals } from '../hooks/useQueries';

// Lazy load charts to reduce initial bundle size (recharts is ~150KB)
const DashboardCharts = lazy(() => import('../components/DashboardCharts'));

// Chart loading skeleton
const ChartsSkeleton = () => (
  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
    {[1, 2, 3].map((i) => (
      <div key={i} className="bg-white shadow rounded-lg p-4 sm:p-6">
        <div className="h-6 bg-gray-200 rounded w-1/3 mb-4 animate-pulse"></div>
        <div className="h-48 bg-gray-100 rounded animate-pulse"></div>
      </div>
    ))}
  </div>
);

const StatCard = ({ title, value, color, icon, testId, to }) => {
  const content = (
    <div className={`bg-white overflow-hidden shadow rounded-lg ${to ? 'hover:shadow-md transition-shadow cursor-pointer' : ''}`} data-testid={testId}>
      <div className="p-3 sm:p-4">
        <div className="flex items-center">
          <div className={`flex-shrink-0 ${color} rounded-md p-2 sm:p-3`}>
            <span className="w-5 h-5 sm:w-6 sm:h-6 block">{icon}</span>
          </div>
          <div className="ml-3 sm:ml-4 flex-1 min-w-0">
            <dl>
              <dt className="text-xs sm:text-sm font-medium text-gray-500 truncate">{title}</dt>
              <dd className="text-lg sm:text-2xl font-semibold text-gray-900" data-testid={testId ? `${testId}-value` : undefined}>{value}</dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );

  if (to) {
    return <Link to={to}>{content}</Link>;
  }
  return content;
};

const Dashboard = () => {
  const { user, isManager } = useAuth();
  const [isMobile, setIsMobile] = useState(window.innerWidth < 640);

  // Use React Query hooks for caching and automatic refetching
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: myTasks = [], isLoading: tasksLoading } = useMyTasks();
  const { data: pendingApprovals = [] } = usePendingApprovals(isManager);

  const loading = statsLoading || tasksLoading;

  useEffect(() => {
    // Handle resize for responsive charts
    const handleResize = () => setIsMobile(window.innerWidth < 640);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

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

  if (loading) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-4"></div>
          <span className="text-gray-600">Loading data, please wait...</span>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="dashboard-stats">
        {/* Welcome */}
        <div className="bg-white shadow rounded-lg p-6">
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome back, {user?.first_name || user?.username}!
          </h1>
          <p className="mt-1 text-gray-500">Here's what's happening with your tickets.</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-2 sm:gap-3 md:gap-4 md:grid-cols-4">
          <StatCard
            title="Total"
            value={stats?.total_tickets || 0}
            color="bg-blue-500"
            testId="stat-total"
            to="/tickets"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
          />
          <StatCard
            title="Dept Approval"
            value={stats?.pending_approval || 0}
            color="bg-indigo-500"
            testId="stat-dept-approval"
            to="/tickets?status=requested"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <StatCard
            title="Creative Approval"
            value={stats?.pending_creative || 0}
            color="bg-purple-500"
            testId="stat-creative-approval"
            to="/tickets?status=pending_creative"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>}
          />
          <StatCard
            title="Not Yet Started"
            value={stats?.approved || 0}
            color="bg-cyan-500"
            testId="stat-approved"
            to="/tickets?status=approved"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <StatCard
            title="In Progress"
            value={stats?.in_progress || 0}
            color="bg-yellow-500"
            testId="stat-in-progress"
            to="/tickets?status=in_progress"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
          />
          <StatCard
            title="Completed"
            value={stats?.completed || 0}
            color="bg-green-500"
            testId="stat-completed"
            to="/tickets?status=completed"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>}
          />
          <StatCard
            title="Rejected"
            value={stats?.rejected || 0}
            color="bg-gray-500"
            testId="stat-rejected"
            to="/tickets?status=rejected"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>}
          />
          <StatCard
            title="Overdue"
            value={stats?.overdue || 0}
            color="bg-red-500"
            testId="stat-overdue"
            to="/tickets?overdue=true"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>}
          />
        </div>

        {/* Charts Row - Lazy Loaded */}
        <Suspense fallback={<ChartsSkeleton />}>
          <DashboardCharts stats={stats} isMobile={isMobile} />
        </Suspense>

        {/* Quick Actions & My Tasks */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Quick Actions */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h2>
            <div className="space-y-3">
              <Link
                to="/tickets/new"
                className="w-full flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
              >
                + Create New Ticket
              </Link>
              <Link
                to="/tickets"
                className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                View All Tickets
              </Link>
              {isManager && (
                <Link
                  to="/tickets?status=requested"
                  className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  Review Pending ({stats?.pending_approval || 0})
                </Link>
              )}
            </div>
          </div>

          {/* My Tasks */}
          <div className="lg:col-span-2 bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-gray-900">My Tasks</h2>
              <span className="text-sm text-gray-500">{myTasks.length} active</span>
            </div>

            {myTasks.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No tasks assigned to you.</p>
            ) : (
              <div className="space-y-3">
                {myTasks.slice(0, 5).map((ticket) => (
                  <Link
                    key={ticket.id}
                    to={`/tickets/${ticket.id}`}
                    className={`block p-4 border rounded-lg hover:bg-gray-50 transition-colors ${
                      ticket.task_type === 'needs_approval' ? 'border-purple-300 bg-purple-50' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            #{ticket.id} - {ticket.title}
                          </p>
                          {ticket.task_type === 'needs_approval' && (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-800 font-medium whitespace-nowrap">
                              Needs your approval
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-500">
                          From: {ticket.requester?.first_name || ticket.requester?.username}
                        </p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-1 text-xs rounded-full ${getPriorityColor(ticket.priority)}`}>
                          {ticket.priority}
                        </span>
                        <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(ticket.status)}`}>
                          {getStatusText(ticket.status)}
                        </span>
                      </div>
                    </div>
                    {ticket.is_overdue && (
                      <p className="mt-1 text-xs text-red-600 font-medium">Overdue!</p>
                    )}
                  </Link>
                ))}

                {myTasks.length > 5 && (
                  <Link
                    to="/tickets?my_tasks=true"
                    className="block text-center text-sm text-blue-600 hover:text-blue-800 pt-2"
                  >
                    View all {myTasks.length} tasks →
                  </Link>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Pending Approvals by Department (Managers only) */}
        {isManager && pendingApprovals.length > 0 && (
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-gray-900">Pending Approvals by Approver</h2>
              <span className="text-sm text-gray-500">
                {pendingApprovals.reduce((sum, item) => sum + item.pending_count, 0)} total
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {pendingApprovals.map((item) => (
                <div
                  key={item.department_id}
                  className={`p-4 border rounded-lg ${
                    item.is_creative ? 'border-purple-300 bg-purple-50' : 'border-blue-300 bg-blue-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{item.approver_name}</p>
                      <p className="text-sm text-gray-500">{item.department_name}</p>
                    </div>
                    <span className={`px-3 py-1 text-lg font-bold rounded-full ${
                      item.is_creative ? 'bg-purple-200 text-purple-800' : 'bg-blue-200 text-blue-800'
                    }`}>
                      {item.pending_count}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">
                    {item.is_creative ? 'Creative Approval' : 'Dept Approval'}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Dashboard;
