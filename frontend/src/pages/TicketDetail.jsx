import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ticketsAPI, usersAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';

const TicketDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isManager } = useAuth();

  const [ticket, setTicket] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [comment, setComment] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [assignUserId, setAssignUserId] = useState('');
  const [showAssignModal, setShowAssignModal] = useState(false);

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      const [ticketRes, usersRes] = await Promise.all([
        ticketsAPI.get(id),
        usersAPI.list(),
      ]);
      setTicket(ticketRes.data);
      setUsers(usersRes.data);
    } catch (error) {
      console.error('Failed to fetch ticket:', error);
      navigate('/tickets');
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action, data = {}) => {
    setActionLoading(true);
    try {
      let response;
      switch (action) {
        case 'approve':
          response = await ticketsAPI.approve(id);
          break;
        case 'reject':
          response = await ticketsAPI.reject(id, rejectReason);
          setShowRejectModal(false);
          break;
        case 'assign':
          response = await ticketsAPI.assign(id, assignUserId);
          setShowAssignModal(false);
          break;
        case 'start':
          response = await ticketsAPI.start(id);
          break;
        case 'complete':
          response = await ticketsAPI.complete(id);
          break;
        default:
          return;
      }
      setTicket(response.data);
    } catch (error) {
      alert(error.response?.data?.error || 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!comment.trim()) return;

    try {
      await ticketsAPI.addComment(id, comment);
      setComment('');
      fetchData(); // Refresh to show new comment
    } catch (error) {
      alert('Failed to add comment');
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
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
      in_progress: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-gray-100 text-gray-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString();
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

  if (!ticket) return null;

  const canApprove = isManager && ticket.status === 'requested';
  const canStart = (ticket.assigned_to?.id === user?.id || isManager) &&
                   ['requested', 'approved'].includes(ticket.status);
  const canComplete = (ticket.assigned_to?.id === user?.id || isManager) &&
                      ticket.status === 'in_progress';

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <button
              onClick={() => navigate('/tickets')}
              className="text-sm text-gray-500 hover:text-gray-700 mb-2"
            >
              ← Back to Tickets
            </button>
            <h1 className="text-2xl font-bold text-gray-900">
              #{ticket.id} - {ticket.title}
            </h1>
          </div>
          <div className="flex items-center space-x-2">
            <span className={`px-3 py-1 text-sm rounded-full ${getStatusColor(ticket.status)}`}>
              {ticket.status.replace('_', ' ')}
            </span>
            <span className={`px-3 py-1 text-sm rounded-full ${getPriorityColor(ticket.priority)}`}>
              {ticket.priority}
            </span>
          </div>
        </div>

        {/* Overdue Warning */}
        {ticket.is_overdue && (
          <div className="bg-red-50 border-l-4 border-red-400 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">This ticket is overdue!</p>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        {(canApprove || canStart || canComplete || isManager) && (
          <div className="bg-white shadow rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Actions</h3>
            <div className="flex flex-wrap gap-2">
              {canApprove && (
                <>
                  <button
                    onClick={() => handleAction('approve')}
                    disabled={actionLoading}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => setShowRejectModal(true)}
                    disabled={actionLoading}
                    className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                  >
                    Reject
                  </button>
                </>
              )}
              {isManager && ticket.status !== 'completed' && ticket.status !== 'rejected' && (
                <button
                  onClick={() => setShowAssignModal(true)}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  Assign
                </button>
              )}
              {canStart && (
                <button
                  onClick={() => handleAction('start')}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50"
                >
                  Start Work
                </button>
              )}
              {canComplete && (
                <button
                  onClick={() => handleAction('complete')}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                >
                  Mark Complete
                </button>
              )}
            </div>
          </div>
        )}

        {/* Details */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Description */}
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Description</h3>
              <p className="text-gray-700 whitespace-pre-wrap">{ticket.description}</p>
            </div>

            {/* Comments */}
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Comments ({ticket.comments?.length || 0})
              </h3>

              {ticket.comments?.length > 0 ? (
                <div className="space-y-4 mb-6">
                  {ticket.comments.map((c) => (
                    <div key={c.id} className="border-b pb-4 last:border-b-0">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-gray-900">
                          {c.user?.first_name || c.user?.username}
                        </span>
                        <span className="text-sm text-gray-500">{formatDate(c.created_at)}</span>
                      </div>
                      <p className="text-gray-700">{c.comment}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 mb-6">No comments yet.</p>
              )}

              {/* Add Comment */}
              <form onSubmit={handleAddComment}>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  rows={3}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Add a comment..."
                />
                <div className="mt-2 flex justify-end">
                  <button
                    type="submit"
                    disabled={!comment.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Add Comment
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Info */}
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Details</h3>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm text-gray-500">Requester</dt>
                  <dd className="text-sm font-medium text-gray-900">
                    {ticket.requester?.first_name || ticket.requester?.username}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Assigned To</dt>
                  <dd className="text-sm font-medium text-gray-900">
                    {ticket.assigned_to?.first_name || ticket.assigned_to?.username || 'Unassigned'}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Approver</dt>
                  <dd className="text-sm font-medium text-gray-900">
                    {ticket.approver?.first_name || ticket.approver?.username || '-'}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Deadline</dt>
                  <dd className="text-sm font-medium text-gray-900">{formatDate(ticket.deadline)}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Created</dt>
                  <dd className="text-sm font-medium text-gray-900">{formatDate(ticket.created_at)}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Updated</dt>
                  <dd className="text-sm font-medium text-gray-900">{formatDate(ticket.updated_at)}</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Reject Ticket</h3>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={3}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="Reason for rejection (optional)"
            />
            <div className="mt-4 flex justify-end space-x-2">
              <button
                onClick={() => setShowRejectModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAction('reject')}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Assign Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Assign Ticket</h3>
            <select
              value={assignUserId}
              onChange={(e) => setAssignUserId(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select user...</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.first_name || u.username} ({u.username})
                </option>
              ))}
            </select>
            <div className="mt-4 flex justify-end space-x-2">
              <button
                onClick={() => setShowAssignModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAction('assign')}
                disabled={actionLoading || !assignUserId}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                Assign
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default TicketDetail;
