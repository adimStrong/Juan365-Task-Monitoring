import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ticketsAPI } from '../services/api';

const TicketPreviewModal = ({ ticketId, onClose, currentUser, isManager, users, onAction }) => {
  const navigate = useNavigate();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [assignUserIds, setAssignUserIds] = useState([]);

  useEffect(() => {
    if (ticketId) {
      fetchTicket();
    }
  }, [ticketId]);

  const fetchTicket = async () => {
    setLoading(true);
    try {
      const response = await ticketsAPI.get(ticketId);
      setTicket(response.data);
    } catch (error) {
      console.error('Failed to fetch ticket:', error);
    } finally {
      setLoading(false);
    }
  };

  // Permission checks
  const isRequester = currentUser?.id === ticket?.requester?.id;
  const isAssigned = currentUser?.id === ticket?.assigned_to?.id;
  const isCollaborator = ticket?.collaborators?.some(c => c.user?.id === currentUser?.id);

  const canApprove = isManager && ['requested', 'pending_creative'].includes(ticket?.status);
  const canReject = isManager && ['requested', 'pending_creative'].includes(ticket?.status);
  const canAssign = isManager && ticket?.status === 'approved';
  const canStart = (isAssigned || isCollaborator) && ticket?.status === 'approved';
  const canComplete = (isAssigned || isCollaborator || isManager) && ticket?.status === 'in_progress';
  const canRequestRevision = (isRequester || isManager) && ticket?.status === 'completed' && !ticket?.confirmed_by_requester;

  const hasAnyAction = canApprove || canReject || canAssign || canStart || canComplete || canRequestRevision;

  const handleAction = async (action, data = {}) => {
    setActionLoading(true);
    try {
      let response;
      switch (action) {
        case 'approve':
          response = await ticketsAPI.approve(ticketId);
          break;
        case 'reject':
          response = await ticketsAPI.reject(ticketId, rejectReason);
          setShowRejectModal(false);
          setRejectReason('');
          break;
        case 'assign':
          if (assignUserIds.length > 0) {
            response = await ticketsAPI.assign(ticketId, assignUserIds[0]);
            // Add remaining users as collaborators
            for (let i = 1; i < assignUserIds.length; i++) {
              try {
                await ticketsAPI.addCollaborator(ticketId, assignUserIds[i]);
              } catch (collabErr) {
                console.error('Failed to add collaborator:', collabErr);
              }
            }
          }
          setShowAssignModal(false);
          setAssignUserIds([]);
          break;
        case 'start':
          response = await ticketsAPI.start(ticketId);
          break;
        case 'complete':
          response = await ticketsAPI.complete(ticketId);
          break;
        case 'request_revision':
          response = await ticketsAPI.requestRevision(ticketId, 'Revision requested from quick action');
          break;
        default:
          return;
      }
      // Refresh ticket data
      await fetchTicket();
      // Notify parent to refresh list
      if (onAction) {
        onAction(action, ticketId);
      }
    } catch (error) {
      console.error(`Action ${action} failed:`, error);
      alert(error.response?.data?.error || `Failed to ${action}`);
    } finally {
      setActionLoading(false);
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

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString();
  };

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!ticketId) return null;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : ticket ? (
          <>
            {/* Header */}
            <div className="px-6 py-4 border-b flex items-center justify-between bg-gray-50">
              <div className="flex items-center space-x-3">
                <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(ticket.status)}`}>
                  {getStatusText(ticket.status)}
                </span>
                <span className={`px-2 py-1 text-xs rounded-full ${getPriorityColor(ticket.priority)}`}>
                  {ticket.priority}
                </span>
                {ticket.is_overdue && (
                  <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">
                    Overdue
                  </span>
                )}
              </div>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              <div className="p-6">
                {/* Title */}
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  #{ticket.id} - {ticket.title}
                </h2>

                {/* Quick Info - Row 1 */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
                  <div>
                    <dt className="text-xs text-gray-500">Requester</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {ticket.requester?.first_name || ticket.requester?.username}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Assigned To</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {ticket.assigned_to
                        ? (() => {
                            const totalUsers = (ticket.assigned_to ? 1 : 0) + (ticket.collaborators?.length || 0);
                            return totalUsers === 1
                              ? (ticket.assigned_to?.first_name || ticket.assigned_to?.username)
                              : `${totalUsers} users`;
                          })()
                        : 'Unassigned'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Deadline</dt>
                    <dd className={`text-sm font-medium ${ticket.is_overdue ? 'text-red-600' : 'text-gray-900'}`}>
                      {ticket.deadline ? formatDate(ticket.deadline) : 'Not set'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Created</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {formatDate(ticket.created_at)}
                    </dd>
                  </div>
                </div>

                {/* Quick Info - Row 2: Department, Product, Quantity, Criteria */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                  <div>
                    <dt className="text-xs text-gray-500">Department</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {ticket.target_department?.name || ticket.department || '-'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Product</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {ticket.ticket_product?.name || ticket.product || '-'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Quantity</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {ticket.quantity || 1}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Criteria</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      <span className={`inline-flex items-center ${
                        ticket.criteria_display === 'Image' ? 'text-pink-600' : 'text-blue-600'
                      }`}>
                        {ticket.criteria_display === 'Image' ? (
                          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        )}
                        {ticket.criteria_display || 'Video'}
                      </span>
                    </dd>
                  </div>
                </div>

                {/* Request Type and File Format Tags */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {ticket.request_type_display && (
                    <span className="px-2 py-1 text-xs bg-indigo-100 text-indigo-800 rounded">
                      {ticket.request_type_display}
                    </span>
                  )}
                  {ticket.file_format_display && (
                    <span className="px-2 py-1 text-xs bg-pink-100 text-pink-800 rounded">
                      {ticket.file_format_display}
                    </span>
                  )}
                  {ticket.revision_count > 0 && (
                    <span className="px-2 py-1 text-xs bg-orange-100 text-orange-800 rounded">
                      {ticket.revision_count} revision{ticket.revision_count > 1 ? 's' : ''}
                    </span>
                  )}
                </div>

                {/* Product Items for Ads/Telegram */}
                {ticket.product_items && ticket.product_items.length > 0 && (
                  <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Products</h3>
                    <div className="grid grid-cols-2 gap-2">
                      {ticket.product_items.map((item) => (
                        <div key={item.id} className="flex items-center justify-between bg-white p-2 rounded border text-sm">
                          <span className="font-medium text-gray-900 truncate">{item.product_name}</span>
                          <span className="text-gray-600 ml-2">x{item.quantity}</span>
                        </div>
                      ))}
                    </div>
                    <div className="text-xs text-gray-500 mt-2">
                      Total: {ticket.product_items.reduce((sum, item) => sum + item.quantity, 0)} items
                    </div>
                  </div>
                )}

                {/* Description */}
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Description</h3>
                  <p className="text-gray-600 whitespace-pre-wrap text-sm bg-gray-50 p-3 rounded">
                    {ticket.description}
                  </p>
                </div>

                {/* Attachments */}
                {ticket.attachments?.length > 0 && (
                  <div className="mb-6">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">
                      Attachments ({ticket.attachments.length})
                    </h3>
                    <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                      {ticket.attachments.map((att) => {
                        const isImage = att.file_name?.match(/\.(jpg|jpeg|png|gif|webp|bmp)$/i);
                        const isVideo = att.file_name?.match(/\.(mp4|webm|mov|avi)$/i);
                        const isPdf = att.file_name?.match(/\.pdf$/i);
                        const apiBaseUrl = import.meta.env.VITE_API_URL || 'https://juan365-task-monitoring-production.up.railway.app';
                        const fileUrl = att.file?.startsWith('http') ? att.file : `${apiBaseUrl}${att.file}`;

                        return (
                          <a
                            key={att.id}
                            href={fileUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="group relative aspect-square rounded-lg overflow-hidden bg-gray-100 hover:ring-2 hover:ring-blue-500 transition-all"
                          >
                            {isImage ? (
                              <img
                                src={fileUrl}
                                alt={att.file_name}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  e.target.style.display = 'none';
                                  e.target.nextSibling.style.display = 'flex';
                                }}
                              />
                            ) : null}
                            <div
                              className={`w-full h-full flex flex-col items-center justify-center ${isImage ? 'hidden' : 'flex'}`}
                            >
                              {isVideo ? (
                                <svg className="w-8 h-8 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                </svg>
                              ) : isPdf ? (
                                <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                </svg>
                              ) : (
                                <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                              )}
                              <span className="text-xs text-gray-500 mt-1 px-1 text-center truncate max-w-full">
                                {att.file_name?.split('.').pop()?.toUpperCase()}
                              </span>
                            </div>
                            {/* Hover overlay with filename */}
                            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              <p className="text-xs text-white truncate" title={att.file_name}>
                                {att.file_name}
                              </p>
                            </div>
                          </a>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Recent Activity */}
                {ticket.comments?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">
                      Recent Comments ({ticket.comments.length})
                    </h3>
                    <div className="space-y-3 max-h-48 overflow-y-auto">
                      {ticket.comments.slice(0, 5).map((comment) => (
                        <div key={comment.id} className="bg-gray-50 p-3 rounded text-sm">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-gray-900">
                              {comment.user?.first_name || comment.user?.username}
                            </span>
                            <span className="text-xs text-gray-500">
                              {formatDate(comment.created_at)}
                            </span>
                          </div>
                          <p className="text-gray-600">{comment.comment}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Actions */}
            {hasAnyAction && (
              <div className="px-6 py-3 border-t bg-blue-50">
                <div className="flex flex-wrap gap-2 justify-center">
                  {canApprove && (
                    <button
                      onClick={() => handleAction('approve')}
                      disabled={actionLoading}
                      className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center text-sm font-medium"
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Approve
                    </button>
                  )}
                  {canReject && (
                    <button
                      onClick={() => setShowRejectModal(true)}
                      disabled={actionLoading}
                      className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center text-sm font-medium"
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      Reject
                    </button>
                  )}
                  {canAssign && (
                    <button
                      onClick={() => setShowAssignModal(true)}
                      disabled={actionLoading}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center text-sm font-medium"
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                      Assign
                    </button>
                  )}
                  {canStart && (
                    <button
                      onClick={() => handleAction('start')}
                      disabled={actionLoading}
                      className="px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 disabled:opacity-50 flex items-center text-sm font-medium"
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Start
                    </button>
                  )}
                  {canComplete && (
                    <button
                      onClick={() => handleAction('complete')}
                      disabled={actionLoading}
                      className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center text-sm font-medium"
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Complete
                    </button>
                  )}
                  {canRequestRevision && (
                    <button
                      onClick={() => handleAction('request_revision')}
                      disabled={actionLoading}
                      className="px-4 py-2 bg-orange-500 text-white rounded-md hover:bg-orange-600 disabled:opacity-50 flex items-center text-sm font-medium"
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      Revision
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Footer */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-between">
              <button
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-100"
              >
                Close
              </button>
              <button
                onClick={() => navigate(`/tickets/${ticket.id}`)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                View Full Details
              </button>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            Ticket not found
          </div>
        )}
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Reject Ticket</h3>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Enter rejection reason..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md mb-4 h-24"
              required
            />
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => {
                  setShowRejectModal(false);
                  setRejectReason('');
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAction('reject')}
                disabled={!rejectReason.trim() || actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                {actionLoading ? 'Rejecting...' : 'Reject'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Assign Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4 max-h-[80vh] overflow-hidden flex flex-col">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Assign Ticket</h3>
            <p className="text-sm text-gray-600 mb-2">
              <span className="text-blue-600 font-medium">Note:</span> Select one or more Creative members to assign.
            </p>
            {assignUserIds.length > 0 && (
              <p className="text-xs text-green-600 mb-2">
                {assignUserIds.length} member{assignUserIds.length > 1 ? 's' : ''} selected
              </p>
            )}
            {(() => {
              const creativeUsers = users?.filter(u => u.user_department_info?.is_creative) || [];
              return creativeUsers.length > 0 ? (
                <div className="overflow-y-auto max-h-60 border border-gray-200 rounded-md">
                  {creativeUsers.map((u) => (
                    <label
                      key={u.id}
                      className={`flex items-center p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0 ${
                        assignUserIds.includes(u.id) ? 'bg-blue-50' : ''
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={assignUserIds.includes(u.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setAssignUserIds([...assignUserIds, u.id]);
                          } else {
                            setAssignUserIds(assignUserIds.filter(id => id !== u.id));
                          }
                        }}
                        className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                      />
                      <div className="ml-3 flex-1">
                        <span className="text-sm font-medium text-gray-900">
                          {u.first_name || u.username} {u.last_name || ''}
                        </span>
                        <span className="text-xs text-gray-500 ml-2">@{u.username}</span>
                      </div>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No Creative department members available.</p>
              );
            })()}
            <div className="mt-4 flex justify-end space-x-2">
              <button
                onClick={() => {
                  setShowAssignModal(false);
                  setAssignUserIds([]);
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAction('assign')}
                disabled={assignUserIds.length === 0 || actionLoading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {actionLoading ? 'Assigning...' : `Assign (${assignUserIds.length})`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TicketPreviewModal;
