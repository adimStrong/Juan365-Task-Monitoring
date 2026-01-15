import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  LineChart, Line, Legend, ResponsiveContainer
} from 'recharts';

/**
 * Dashboard charts component - lazy loaded to reduce initial bundle size
 * Contains: Status Pie Chart, Priority Bar Chart, Weekly Trends Line Chart
 */
const DashboardCharts = ({ stats, isMobile }) => {
  // Filter out zero values for pie chart
  const statusChartData = stats?.status_chart?.filter(item => item.value > 0) || [];

  return (
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
                label={({ value }) => `${value}`}
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
  );
};

export default DashboardCharts;
