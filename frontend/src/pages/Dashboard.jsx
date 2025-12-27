import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { dashboardAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { DashboardSkeleton } from '../components/Skeleton';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  LineChart, Line, Legend, ResponsiveContainer
} from 'recharts';

const StatCard = ({ title, value, color, icon, testId }) => (
  <div className="bg-white overflow-hidden shadow rounded-lg" data-testid={testId}>
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

const Dashboard = () => {
  const { user, isManager } = useAuth();
  const [stats, setStats] = useState(null);
  const [myTasks, setMyTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 640);

  useEffect(() => {
    fetchData();

    // Handle resize for responsive charts
    const handleResize = () => setIsMobile(window.innerWidth < 640);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, tasksRes] = await Promise.all([
        dashboardAPI.getStats(),
        dashboardAPI.getMyTasks(),
      ]);
      setStats(statsRes.data);
      setMyTasks(tasksRes.data.results || tasksRes.data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

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
        <DashboardSkeleton />
      </Layout>
    );
  }

  // Filter out zero values for pie chart
  const statusChartData = stats?.status_chart?.filter(item => item.value > 0) || [];

  return (
    <Layout>
      <div className="space-y-6">
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
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
          />
          <StatCard
            title="Dept Approval"
            value={stats?.pending_approval || 0}
            color="bg-indigo-500"
            testId="stat-dept-approval"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <StatCard
            title="Creative Approval"
            value={stats?.pending_creative || 0}
            color="bg-purple-500"
            testId="stat-creative-approval"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>}
          />
          <StatCard
            title="Not Yet Started"
            value={stats?.approved || 0}
            color="bg-cyan-500"
            testId="stat-approved"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          />
          <StatCard
            title="In Progress"
            value={stats?.in_progress || 0}
            color="bg-yellow-500"
            testId="stat-in-progress"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
          />
          <StatCard
            title="Completed"
            value={stats?.completed || 0}
            color="bg-green-500"
            testId="stat-completed"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>}
          />
          <StatCard
            title="Rejected"
            value={stats?.rejected || 0}
            color="bg-gray-500"
            testId="stat-rejected"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>}
          />
          <StatCard
            title="Overdue"
            value={stats?.overdue || 0}
            color="bg-red-500"
            testId="stat-overdue"
            icon={<svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>}
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Status Pie Chart */}
          <div className="bg-white shadow rounded-lg p-4 sm:p-6">
            <h2 className="text-base sm:text-lg font-medium text-gray-900 mb-4">Tickets by Status</h2>
            {statusChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={isMobile ? 220 : 280}>
                <PieChart>
                  <Pie
                    data={statusChartData}
                    cx="50%"
                    cy="40%"
                    innerRadius={isMobile ? 25 : 35}
                    outerRadius={isMobile ? 50 : 65}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, value }) => `${value}`}
                    labelLine={false}
                  >
                    {statusChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value, name) => [value, name]} />
                  <Legend
                    layout="horizontal"
                    verticalAlign="bottom"
                    align="center"
                    wrapperStyle={{
                      paddingTop: '15px',
                      fontSize: isMobile ? '10px' : '11px'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-36 sm:h-48 text-gray-500">
                No tickets yet
              </div>
            )}
          </div>

          {/* Priority Bar Chart */}
          <div className="bg-white shadow rounded-lg p-4 sm:p-6">
            <h2 className="text-base sm:text-lg font-medium text-gray-900 mb-4">Tickets by Priority</h2>
            <ResponsiveContainer width="100%" height={isMobile ? 160 : 200}>
              <BarChart data={stats?.priority_chart || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: isMobile ? 10 : 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: isMobile ? 10 : 12 }} />
                <Tooltip />
                <Bar dataKey="count" name="Tickets">
                  {(stats?.priority_chart || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Weekly Trends Line Chart */}
          <div className="bg-white shadow rounded-lg p-4 sm:p-6">
            <h2 className="text-base sm:text-lg font-medium text-gray-900 mb-4">Weekly Trends</h2>
            <ResponsiveContainer width="100%" height={isMobile ? 160 : 200}>
              <LineChart data={stats?.weekly_chart || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" tick={{ fontSize: isMobile ? 10 : 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: isMobile ? 10 : 12 }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: isMobile ? '10px' : '12px' }} />
                <Line type="monotone" dataKey="created" stroke="#3B82F6" name="Created" strokeWidth={2} />
                <Line type="monotone" dataKey="completed" stroke="#10B981" name="Completed" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

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
                    className="block p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          #{ticket.id} - {ticket.title}
                        </p>
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
                    to="/tickets?assigned_to=me"
                    className="block text-center text-sm text-blue-600 hover:text-blue-800 pt-2"
                  >
                    View all {myTasks.length} tasks →
                  </Link>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;
