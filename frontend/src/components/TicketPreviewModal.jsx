import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ticketsAPI } from '../services/api';

const TicketPreviewModal = ({ ticketId, onClose }) => {
  const navigate = useNavigate();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);

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
      rejected: 'bg-red-100 text-red-800',
      in_progress: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getStatusText = (status) => {
    const texts = {
      requested: 'For Dept Approval',
      pending_creative: 'For Creative Approval',
      approved: 'Approved',
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

                {/* Quick Info */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                  <div>
                    <dt className="text-xs text-gray-500">Requester</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {ticket.requester?.first_name || ticket.requester?.username}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-gray-500">Assigned To</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {ticket.assigned_to?.first_name || ticket.assigned_to?.username || 'Unassigned'}
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

                {/* Request Type and File Format */}
                {(ticket.request_type_display || ticket.file_format_display) && (
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
    </div>
  );
};

export default TicketPreviewModal;
