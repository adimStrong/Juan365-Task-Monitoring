import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import Layout from '../components/Layout';
import { useMonthlyReport } from '../hooks/useQueries';

const MonthlyReport = () => {
  const navigate = useNavigate();
  const { isManager } = useAuth();
  const { showToast } = useToast();

  // Date selector state
  const now = new Date();
  const [selectedYear, setSelectedYear] = useState(now.getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth() + 1);

  // Leaderboard sorting
  const [sortColumn, setSortColumn] = useState('total_output');
  const [sortDirection, setSortDirection] = useState('desc');

  // Fetch report data
  const {
    data: report,
    isLoading,
    error,
    isFetching,
  } = useMonthlyReport(selectedYear, selectedMonth);

  // Redirect non-managers
  useEffect(() => {
    if (!isManager) {
      navigate('/');
    }
  }, [isManager, navigate]);

  // Generate year options (last 3 years)
  const yearOptions = useMemo(() => {
    const currentYear = now.getFullYear();
    return [currentYear, currentYear - 1, currentYear - 2];
  }, []);

  // Month options
  const monthOptions = [
    { value: 1, label: 'January' },
    { value: 2, label: 'February' },
    { value: 3, label: 'March' },
    { value: 4, label: 'April' },
    { value: 5, label: 'May' },
    { value: 6, label: 'June' },
    { value: 7, label: 'July' },
    { value: 8, label: 'August' },
    { value: 9, label: 'September' },
    { value: 10, label: 'October' },
    { value: 11, label: 'November' },
    { value: 12, label: 'December' },
  ];

  // Format numbers with commas or abbreviations (1k, 1M)
  const formatNumber = (num, abbreviate = false) => {
    if (num === null || num === undefined) return 'N/A';
    if (typeof num !== 'number') return num;

    if (abbreviate) {
      if (num >= 1000000) {
        return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
      }
      if (num >= 1000) {
        return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
      }
    }
    return num.toLocaleString();
  };

  // RAG status colors
  const getRagColor = (status) => {
    switch (status) {
      case 'green':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'amber':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'red':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'blue':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      default:
        return 'bg-gray-100 text-gray-600 border-gray-300';
    }
  };

  const getRagIcon = (status) => {
    switch (status) {
      case 'green':
        return (
          <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        );
      case 'amber':
        return (
          <svg className="w-5 h-5 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      case 'red':
        return (
          <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  // Sort leaderboard
  const sortedLeaderboard = useMemo(() => {
    if (!report?.team_leaderboard) return [];
    return [...report.team_leaderboard].sort((a, b) => {
      const aVal = a[sortColumn] ?? 0;
      const bVal = b[sortColumn] ?? 0;
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    });
  }, [report?.team_leaderboard, sortColumn, sortDirection]);

  const handleSort = (column) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  const SortIcon = ({ column }) => {
    if (sortColumn !== column) {
      return (
        <svg className="w-4 h-4 text-gray-400 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    return sortDirection === 'asc' ? (
      <svg className="w-4 h-4 text-blue-600 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    ) : (
      <svg className="w-4 h-4 text-blue-600 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  // Copy Telegram summary to clipboard
  const copyTelegramSummary = () => {
    if (!report) return;

    const kpi = report.executive_summary.kpi_summary;
    const mom = report.mom_comparison;
    const insights = report.insights;

    let text = `*CREATIVE TEAM MONTHLY REPORT*\n`;
    text += `*${report.report_period.month_name} ${report.report_period.year}*\n\n`;

    text += `*EXECUTIVE SUMMARY*\n`;
    text += `Total Tickets: *${formatNumber(report.executive_summary.total_tickets)}*\n`;
    text += `Completed: *${formatNumber(report.executive_summary.completed_tickets)}*\n`;
    text += `Total Output: *${formatNumber(report.executive_summary.total_output)}* creatives\n`;
    text += `  Video: ${formatNumber(report.executive_summary.video_quantity)} | Image: ${formatNumber(report.executive_summary.image_quantity)}\n\n`;

    text += `*KEY METRICS*\n`;
    const ragEmojis = { green: '\u2705', amber: '\u26A0\uFE0F', red: '\u274C', blue: '\u2139\uFE0F', grey: '\u2B55' };
    Object.entries(kpi).forEach(([key, data]) => {
      const emoji = ragEmojis[data.rag.status] || '\u2B55';
      const value = data.value !== null ? `${data.value}${data.unit}` : 'N/A';
      text += `${emoji} ${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}: *${value}*\n`;
    });
    text += '\n';

    text += `*TOP 5 PERFORMERS*\n`;
    const medals = ['\uD83E\uDD47', '\uD83E\uDD48', '\uD83E\uDD49', '4.', '5.'];
    sortedLeaderboard.slice(0, 5).forEach((member, i) => {
      text += `${medals[i]} ${member.full_name}: *${formatNumber(member.total_output)}* output\n`;
    });
    text += '\n';

    if (insights.wins.length > 0) {
      text += `*WINS*\n`;
      insights.wins.forEach(win => {
        text += `\u2705 ${win}\n`;
      });
      text += '\n';
    }

    if (insights.improvements.length > 0) {
      text += `*AREAS FOR IMPROVEMENT*\n`;
      insights.improvements.forEach(imp => {
        text += `\u26A0\uFE0F ${imp}\n`;
      });
      text += '\n';
    }

    text += `*VS PREVIOUS MONTH*\n`;
    const outputChange = mom.metrics.total_output.change;
    if (outputChange !== null) {
      const arrow = outputChange > 0 ? '\uD83D\uDCC8' : '\uD83D\uDCC9';
      text += `${arrow} Output: ${outputChange > 0 ? '+' : ''}${outputChange}%\n`;
    }

    navigator.clipboard.writeText(text).then(() => {
      showToast('Copied to clipboard!', 'success');
    }).catch(() => {
      showToast('Failed to copy', 'error');
    });
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
            <h1 className="text-2xl font-bold text-gray-900">Monthly Report</h1>
            <p className="text-gray-500 mt-1">Comprehensive KPI report for management review</p>
          </div>
          <button
            onClick={copyTelegramSummary}
            disabled={!report}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
            </svg>
            Copy for Telegram
          </button>
        </div>

        {/* Month/Year Selector */}
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Month</label>
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(Number(e.target.value))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {monthOptions.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Year</label>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(Number(e.target.value))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {yearOptions.map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            {isFetching && (
              <span className="text-sm text-blue-600 flex items-center gap-1">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Loading...
              </span>
            )}
          </div>
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-64 space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            <div className="text-center">
              <p className="text-gray-600 font-medium">Generating Report...</p>
              <p className="text-sm text-gray-400 mt-1">Calculating KPIs and metrics</p>
            </div>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            Failed to load report data. Please try again.
          </div>
        ) : report ? (
          <>
            {/* Executive Summary KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {Object.entries(report.executive_summary.kpi_summary).map(([key, data]) => (
                <div
                  key={key}
                  className={`rounded-lg border-2 p-4 ${getRagColor(data.rag.status)}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium uppercase tracking-wide opacity-75">
                      {key.replace(/_/g, ' ')}
                    </span>
                    {getRagIcon(data.rag.status)}
                  </div>
                  <p className="text-3xl font-bold">
                    {data.value !== null ? `${typeof data.value === 'number' ? formatNumber(data.value) : data.value}${data.unit}` : 'N/A'}
                  </p>
                  <div className="flex items-center justify-between mt-2 text-xs">
                    <span className="opacity-75">Target: {data.target !== null ? `${data.target}${data.unit}` : '-'}</span>
                    <span className="font-medium">{data.rag.label}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow-sm p-4">
                <p className="text-sm text-gray-500">Total Tickets</p>
                <p className="text-2xl font-bold text-gray-900">{formatNumber(report.executive_summary.total_tickets)}</p>
              </div>
              <div className="bg-white rounded-lg shadow-sm p-4">
                <p className="text-sm text-gray-500">Completed</p>
                <p className="text-2xl font-bold text-green-600">{formatNumber(report.executive_summary.completed_tickets)}</p>
              </div>
              <div className="bg-white rounded-lg shadow-sm p-4">
                <p className="text-sm text-gray-500">Video Output</p>
                <p className="text-2xl font-bold text-blue-600">{formatNumber(report.executive_summary.video_quantity)}</p>
              </div>
              <div className="bg-white rounded-lg shadow-sm p-4">
                <p className="text-sm text-gray-500">Image Output</p>
                <p className="text-2xl font-bold text-pink-600">{formatNumber(report.executive_summary.image_quantity)}</p>
              </div>
            </div>

            {/* Insights */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {report.insights.wins.length > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-green-800 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Wins
                  </h3>
                  <ul className="space-y-2">
                    {report.insights.wins.map((win, i) => (
                      <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                        <span className="text-green-500 mt-0.5">+</span>
                        {win}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {report.insights.improvements.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-amber-800 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    Areas for Improvement
                  </h3>
                  <ul className="space-y-2">
                    {report.insights.improvements.map((imp, i) => (
                      <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                        <span className="text-amber-500 mt-0.5">-</span>
                        {imp}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {report.insights.action_items.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-blue-800 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                    </svg>
                    Action Items
                  </h3>
                  <ul className="space-y-2">
                    {report.insights.action_items.map((item, i) => (
                      <li key={i} className="text-sm text-blue-700 flex items-start gap-2">
                        <span className="text-blue-500 mt-0.5">&bull;</span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Team Leaderboard */}
            <div className="bg-white rounded-lg shadow-sm">
              <div className="px-6 py-4 border-b">
                <h3 className="text-lg font-semibold text-gray-900">Team Leaderboard</h3>
                <p className="text-sm text-gray-500">Click column headers to sort</p>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rank</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Designer</th>
                      <th
                        className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort('tickets_completed')}
                      >
                        <div className="flex items-center justify-center">
                          Tickets
                          <SortIcon column="tickets_completed" />
                        </div>
                      </th>
                      <th
                        className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort('total_output')}
                      >
                        <div className="flex items-center justify-center">
                          Output
                          <SortIcon column="total_output" />
                        </div>
                      </th>
                      <th
                        className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort('on_time_rate')}
                      >
                        <div className="flex items-center justify-center">
                          On-Time %
                          <SortIcon column="on_time_rate" />
                        </div>
                      </th>
                      <th
                        className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort('avg_revisions')}
                      >
                        <div className="flex items-center justify-center">
                          Avg Rev
                          <SortIcon column="avg_revisions" />
                        </div>
                      </th>
                      <th
                        className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                        onClick={() => handleSort('completion_rate')}
                      >
                        <div className="flex items-center justify-center">
                          Completion %
                          <SortIcon column="completion_rate" />
                        </div>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {sortedLeaderboard.map((member, index) => {
                      const isTop3 = member.rank <= 3;
                      const medals = { 1: '\uD83E\uDD47', 2: '\uD83E\uDD48', 3: '\uD83E\uDD49' };
                      return (
                        <tr key={member.user_id} className={isTop3 ? 'bg-yellow-50' : 'hover:bg-gray-50'}>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className={`font-bold ${isTop3 ? 'text-lg' : 'text-gray-600'}`}>
                              {medals[member.rank] || member.rank}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <div className="flex items-center">
                              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                                {member.full_name?.[0]?.toUpperCase()}
                              </div>
                              <div className="ml-3">
                                <div className="text-sm font-medium text-gray-900">{member.full_name}</div>
                                <div className="text-xs text-gray-500">{member.department}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-center text-sm text-gray-900">
                            {formatNumber(member.tickets_completed)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-center text-sm font-semibold text-blue-600">
                            {formatNumber(member.total_output)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-center">
                            <span className={`text-sm font-medium ${
                              member.on_time_rate === null ? 'text-gray-400' :
                              member.on_time_rate >= 80 ? 'text-green-600' :
                              member.on_time_rate >= 70 ? 'text-amber-600' : 'text-red-600'
                            }`}>
                              {member.on_time_rate !== null ? `${member.on_time_rate}%` : 'N/A'}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-center">
                            <span className={`text-sm font-medium ${
                              member.avg_revisions <= 2 ? 'text-green-600' :
                              member.avg_revisions <= 3 ? 'text-amber-600' : 'text-red-600'
                            }`}>
                              {member.avg_revisions}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-center">
                            <span className={`text-sm font-medium ${
                              member.completion_rate >= 80 ? 'text-green-600' :
                              member.completion_rate >= 70 ? 'text-amber-600' : 'text-red-600'
                            }`}>
                              {member.completion_rate}%
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                    {sortedLeaderboard.length === 0 && (
                      <tr>
                        <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                          No data available for this period
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Breakdowns */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* By Product */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">By Product</h3>
                {report.breakdowns.by_product.length > 0 ? (
                  <div className="space-y-3">
                    {report.breakdowns.by_product.map((item) => (
                      <div key={item.product}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700">{item.product}</span>
                          <div className="flex items-center gap-3 text-sm">
                            <span className="text-gray-500">{formatNumber(item.count)} tickets</span>
                            <span className="font-semibold text-blue-600">{formatNumber(item.output)} output</span>
                          </div>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{
                              width: `${Math.min((item.output / (report.executive_summary.total_output || 1)) * 100, 100)}%`
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">No product data available</p>
                )}
              </div>

              {/* By Department */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">By Department</h3>
                {report.breakdowns.by_department.length > 0 ? (
                  <div className="space-y-3">
                    {report.breakdowns.by_department.map((item) => (
                      <div key={item.department}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700">{item.department}</span>
                          <div className="flex items-center gap-3 text-sm">
                            <span className="text-gray-500">{formatNumber(item.count)} tickets</span>
                            <span className="text-green-600">{formatNumber(item.completed)} completed</span>
                          </div>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-green-500 h-2 rounded-full"
                            style={{
                              width: `${item.count > 0 ? (item.completed / item.count) * 100 : 0}%`
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">No department data available</p>
                )}
              </div>

              {/* By Request Type */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">By Request Type</h3>
                {report.breakdowns.by_request_type.length > 0 ? (
                  <div className="space-y-3">
                    {report.breakdowns.by_request_type.map((item) => (
                      <div key={item.request_type}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700">{item.display_name}</span>
                          <div className="flex items-center gap-3 text-sm">
                            <span className="text-gray-500">{formatNumber(item.count)} tickets</span>
                            <span className="text-purple-600">Avg rev: {item.avg_revisions}</span>
                          </div>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-purple-500 h-2 rounded-full"
                            style={{
                              width: `${(item.count / (report.executive_summary.total_tickets || 1)) * 100}%`
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">No request type data available</p>
                )}
              </div>

              {/* Quality Metrics */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Revision Distribution</h3>
                <div className="space-y-3">
                  {Object.entries(report.quality_metrics.revision_distribution).map(([key, count]) => (
                    <div key={key} className="flex items-center gap-4">
                      <span className="w-16 text-sm font-medium text-gray-700">
                        {key === '4+' ? '4+ revisions' : `${key} revisions`}
                      </span>
                      <div className="flex-1 bg-gray-200 rounded-full h-4">
                        <div
                          className={`h-4 rounded-full ${
                            key === '0' ? 'bg-green-500' :
                            key === '1' || key === '2' ? 'bg-amber-500' : 'bg-red-500'
                          }`}
                          style={{
                            width: `${report.executive_summary.completed_tickets > 0 ? (count / report.executive_summary.completed_tickets) * 100 : 0}%`
                          }}
                        />
                      </div>
                      <span className="w-12 text-right text-sm text-gray-600">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* MoM Comparison */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Month-over-Month Comparison
                <span className="ml-2 text-sm font-normal text-gray-500">
                  vs {report.mom_comparison.previous_month}
                </span>
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {Object.entries(report.mom_comparison.metrics).map(([key, data]) => {
                  const isPositive = data.change && data.change > 0;
                  const isNeutral = data.change === null || data.change === 0;
                  return (
                    <div key={key} className="border rounded-lg p-4">
                      <p className="text-sm text-gray-500 capitalize">{key.replace(/_/g, ' ')}</p>
                      <p className="text-2xl font-bold text-gray-900">{formatNumber(data.current)}</p>
                      <div className="flex items-center gap-1 mt-1">
                        {!isNeutral && (
                          <svg
                            className={`w-4 h-4 ${isPositive ? 'text-green-500' : 'text-red-500'}`}
                            fill="currentColor"
                            viewBox="0 0 20 20"
                          >
                            <path
                              fillRule="evenodd"
                              d={isPositive
                                ? "M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z"
                                : "M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z"
                              }
                              clipRule="evenodd"
                            />
                          </svg>
                        )}
                        <span className={`text-sm font-medium ${
                          isNeutral ? 'text-gray-500' : isPositive ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {data.change !== null ? `${isPositive ? '+' : ''}${data.change}%` : '-'}
                        </span>
                        <span className="text-xs text-gray-400">
                          (was {formatNumber(data.previous)})
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Overdue Tickets */}
            {report.overdue_metrics.overdue_count > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-red-800 mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                  </svg>
                  Overdue Tickets ({report.overdue_metrics.overdue_count})
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-red-600">{report.overdue_metrics.overdue_by_priority.urgent}</p>
                    <p className="text-xs text-red-500">Urgent</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-orange-600">{report.overdue_metrics.overdue_by_priority.high}</p>
                    <p className="text-xs text-orange-500">High</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-yellow-600">{report.overdue_metrics.overdue_by_priority.medium}</p>
                    <p className="text-xs text-yellow-600">Medium</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-600">{report.overdue_metrics.overdue_by_priority.low}</p>
                    <p className="text-xs text-gray-500">Low</p>
                  </div>
                </div>
                {report.overdue_metrics.overdue_tickets?.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-medium text-red-700 mb-2">Top overdue tickets:</p>
                    <div className="space-y-2">
                      {report.overdue_metrics.overdue_tickets.slice(0, 5).map((ticket) => (
                        <div key={ticket.id} className="flex items-center justify-between bg-white rounded p-2 text-sm">
                          <span className="font-medium text-gray-800">#{ticket.id} - {ticket.title}</span>
                          <div className="flex items-center gap-3">
                            <span className={`px-2 py-0.5 rounded text-xs ${
                              ticket.priority === 'urgent' ? 'bg-red-100 text-red-700' :
                              ticket.priority === 'high' ? 'bg-orange-100 text-orange-700' :
                              'bg-gray-100 text-gray-600'
                            }`}>
                              {ticket.priority}
                            </span>
                            <span className="text-gray-500">{ticket.assigned_to || 'Unassigned'}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* High Revision Tickets */}
            {report.quality_metrics.high_revision_tickets?.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-amber-800 mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                  </svg>
                  High Revision Tickets ({report.quality_metrics.high_revision_tickets.length})
                </h3>
                <p className="text-sm text-amber-700 mb-3">Tickets with more than 3 revision rounds - consider reviewing for process improvement</p>
                <div className="space-y-2">
                  {report.quality_metrics.high_revision_tickets.map((ticket) => (
                    <div key={ticket.id} className="flex items-center justify-between bg-white rounded p-2 text-sm">
                      <span className="font-medium text-gray-800">#{ticket.id} - {ticket.title}</span>
                      <div className="flex items-center gap-3">
                        <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs">
                          {ticket.revision_count} revisions
                        </span>
                        <span className="text-gray-500">{ticket.assigned_to || 'Unassigned'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : null}
      </div>
    </Layout>
  );
};

export default MonthlyReport;
