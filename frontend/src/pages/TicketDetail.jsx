import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ticketsAPI, usersAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import Layout from '../components/Layout';
import { SkeletonTicketDetail } from '../components/Skeleton';

const TicketDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isManager } = useAuth();
  const toast = useToast();

  const [ticket, setTicket] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [comment, setComment] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [assignUserId, setAssignUserId] = useState('');
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showCollaboratorModal, setShowCollaboratorModal] = useState(false);
  const [collaboratorUserId, setCollaboratorUserId] = useState('');
  const [replyingTo, setReplyingTo] = useState(null);
  const [replyText, setReplyText] = useState('');
  const [expandedReplies, setExpandedReplies] = useState({});
  const [history, setHistory] = useState([]);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [rollbackLoading, setRollbackLoading] = useState(false);
  const [showRevisionModal, setShowRevisionModal] = useState(false);
  const [revisionComments, setRevisionComments] = useState('');

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
      // Handle both array and paginated responses
      const usersData = usersRes.data;
      setUsers(Array.isArray(usersData) ? usersData : (usersData.results || []));
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
      toast.success(`Action "${action}" completed successfully!`);
    } catch (error) {
      toast.error(error.response?.data?.error || 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSoftDelete = async () => {
    setActionLoading(true);
    try {
      await ticketsAPI.softDelete(id);
      toast.success('Ticket moved to trash');
      setShowDeleteModal(false);
      navigate('/tickets');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to delete ticket');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!comment.trim()) return;

    try {
      const response = await ticketsAPI.addComment(id, comment);
      // Update state locally instead of full refresh
      setTicket(prev => ({
        ...prev,
        comments: [...(prev.comments || []), response.data]
      }));
      setComment('');
      toast.success('Comment added');
    } catch (error) {
      toast.error('Failed to add comment');
    }
  };

  const handleReply = async (parentId) => {
    if (!replyText.trim()) return;

    try {
      const response = await ticketsAPI.addComment(id, replyText, parentId);
      // Update state locally - add reply to parent comment
      setTicket(prev => ({
        ...prev,
        comments: prev.comments.map(c =>
          c.id === parentId
            ? { ...c, replies: [...(c.replies || []), response.data] }
            : c
        )
      }));
      setReplyText('');
      setReplyingTo(null);
      // Auto-expand replies after adding one
      setExpandedReplies(prev => ({ ...prev, [parentId]: true }));
      toast.success('Reply added');
    } catch (error) {
      toast.error('Failed to add reply');
    }
  };

  const toggleReplies = (commentId) => {
    setExpandedReplies(prev => ({ ...prev, [commentId]: !prev[commentId] }));
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadingFile(true);
    try {
      const response = await ticketsAPI.addAttachment(id, file);
      // Update state locally
      setTicket(prev => ({
        ...prev,
        attachments: [...(prev.attachments || []), response.data]
      }));
      toast.success('File uploaded successfully');
      e.target.value = ''; // Reset file input
    } catch (error) {
      toast.error('Failed to upload file: ' + (error.response?.data?.error || error.message));
    } finally {
      setUploadingFile(false);
    }
  };

  const handleDeleteAttachment = async (attachmentId) => {
    if (!window.confirm('Are you sure you want to delete this attachment?')) return;

    try {
      await ticketsAPI.deleteAttachment(attachmentId);
      // Update state locally - remove the deleted attachment
      setTicket(prev => ({
        ...prev,
        attachments: prev.attachments.filter(att => att.id !== attachmentId)
      }));
      toast.success('Attachment deleted');
    } catch (error) {
      toast.error('Failed to delete attachment');
    }
  };

  const handleConfirmComplete = async () => {
    if (actionLoading) return; // Prevent double-click
    setActionLoading(true);
    try {
      const response = await ticketsAPI.confirmComplete(id);
      setTicket(response.data);
      setShowConfirmModal(false);
      toast.success('Completion confirmed!');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to confirm. Please refresh and try again.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddCollaborator = async () => {
    if (!collaboratorUserId) return;
    setActionLoading(true);
    try {
      const response = await ticketsAPI.addCollaborator(id, collaboratorUserId);
      // Update state locally
      setTicket(prev => ({
        ...prev,
        collaborators: [...(prev.collaborators || []), response.data]
      }));
      setShowCollaboratorModal(false);
      setCollaboratorUserId('');
      toast.success('Collaborator added');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to add collaborator');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRemoveCollaborator = async (userId) => {
    if (!window.confirm('Remove this collaborator?')) return;
    try {
      await ticketsAPI.removeCollaborator(id, userId);
      // Update state locally - remove the collaborator
      setTicket(prev => ({
        ...prev,
        collaborators: prev.collaborators.filter(c => c.user?.id !== userId)
      }));
      toast.success('Collaborator removed');
    } catch (error) {
      toast.error('Failed to remove collaborator');
    }
  };

  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const response = await ticketsAPI.getHistory(id);
      setHistory(response.data);
      setShowHistoryModal(true);
    } catch (error) {
      toast.error('Failed to load history');
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleRollback = async (activityId) => {
    if (!window.confirm('Are you sure you want to restore the ticket to this state?')) return;
    setRollbackLoading(true);
    try {
      const response = await ticketsAPI.rollback(id, activityId);
      setTicket(response.data);
      setShowHistoryModal(false);
      toast.success('Ticket restored to previous state');
      // No fetchData() needed - response already has updated ticket
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to rollback');
    } finally {
      setRollbackLoading(false);
    }
  };

  const handleRequestRevision = async () => {
    if (!revisionComments.trim()) {
      toast.error('Please provide revision comments');
      return;
    }
    setActionLoading(true);
    try {
      const response = await ticketsAPI.requestRevision(id, revisionComments);
      setTicket(response.data);
      setShowRevisionModal(false);
      setRevisionComments('');
      toast.success('Revision requested successfully');
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to request revision');
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

  if (loading) {
    return (
      <Layout>
        <SkeletonTicketDetail />
      </Layout>
    );
  }

  if (!ticket) return null;

  const canApprove = isManager && ['requested', 'pending_creative'].includes(ticket.status);
  // Only the assigned person can start editing (must be assigned first)
  const canStart = ticket.assigned_to?.id === user?.id &&
                   ticket.status === 'approved';
  const canComplete = (ticket.assigned_to?.id === user?.id || isManager) &&
                      ticket.status === 'in_progress';
  const canConfirm = ticket.requester?.id === user?.id &&
                     ticket.status === 'completed' &&
                     !ticket.confirmed_by_requester;
  // Can request revision: requester or collaborator, ticket is completed, not yet confirmed
  const isCollaborator = ticket.collaborators?.some(c => c.user?.id === user?.id);
  const canRequestRevision = (ticket.requester?.id === user?.id || isCollaborator || isManager) &&
                             ticket.status === 'completed' &&
                             !ticket.confirmed_by_requester;

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <button
              onClick={() => navigate('/tickets')}
              className="text-sm text-gray-500 hover:text-gray-700 mb-2"
            >
              ← Back to Tickets
            </button>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
              #{ticket.id} - {ticket.title}
            </h1>
          </div>
          <div className="flex items-center space-x-2 flex-shrink-0">
            <span className={`px-2 sm:px-3 py-1 text-xs sm:text-sm rounded-full ${getStatusColor(ticket.status)}`}>
              {getStatusText(ticket.status)}
            </span>
            <span className={`px-2 sm:px-3 py-1 text-xs sm:text-sm rounded-full ${getPriorityColor(ticket.priority)}`}>
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
        {(canApprove || canStart || canComplete || canConfirm || isManager) && (
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
              {isManager && ticket.status === 'approved' && !ticket.assigned_to && (
                <button
                  onClick={() => setShowAssignModal(true)}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  Assign
                </button>
              )}
              {ticket.status !== 'completed' && ticket.status !== 'rejected' && (
                <button
                  onClick={() => setShowCollaboratorModal(true)}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                >
                  Add Collaborator
                </button>
              )}
              {canStart && (
                <button
                  onClick={() => handleAction('start')}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50"
                >
                  Start Editing
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
              {canConfirm && (
                <button
                  onClick={() => setShowConfirmModal(true)}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50"
                >
                  Confirm Completion
                </button>
              )}
              {canRequestRevision && (
                <button
                  onClick={() => setShowRevisionModal(true)}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50"
                >
                  Request Revision
                </button>
              )}
              {isManager && ticket.status !== 'completed' && (
                <button
                  onClick={() => setShowDeleteModal(true)}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
                >
                  Move to Trash
                </button>
              )}
            </div>
          </div>
        )}

        {/* Confirmation Status */}
        {ticket.status === 'completed' && (
          <div className={`p-4 rounded-lg ${ticket.confirmed_by_requester ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'}`}>
            {ticket.confirmed_by_requester ? (
              <div className="flex items-center text-green-700">
                <svg className="h-5 w-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span className="font-medium">Completion confirmed by requester</span>
              </div>
            ) : (
              <div className="flex items-center text-yellow-700">
                <svg className="h-5 w-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3.586L7.707 9.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 10.586V7z" clipRule="evenodd" />
                </svg>
                <span className="font-medium">Awaiting confirmation from requester</span>
              </div>
            )}
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
                      <button
                        onClick={() => setReplyingTo(replyingTo === c.id ? null : c.id)}
                        className="mt-2 text-sm text-blue-600 hover:text-blue-800"
                      >
                        {replyingTo === c.id ? 'Cancel' : 'Reply'}
                      </button>

                      {/* Reply Form */}
                      {replyingTo === c.id && (
                        <div className="mt-3 ml-4 pl-4 border-l-2 border-gray-200">
                          <textarea
                            value={replyText}
                            onChange={(e) => setReplyText(e.target.value)}
                            rows={2}
                            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            placeholder="Write a reply..."
                          />
                          <div className="mt-2 flex justify-end">
                            <button
                              onClick={() => handleReply(c.id)}
                              disabled={!replyText.trim()}
                              className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                            >
                              Reply
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Replies */}
                      {c.replies?.length > 0 && (
                        <div className="mt-3">
                          {!expandedReplies[c.id] ? (
                            <button
                              onClick={() => toggleReplies(c.id)}
                              className="text-sm text-blue-600 hover:text-blue-800 flex items-center"
                            >
                              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                              </svg>
                              View {c.replies.length} {c.replies.length === 1 ? 'reply' : 'replies'}
                            </button>
                          ) : (
                            <>
                              <button
                                onClick={() => toggleReplies(c.id)}
                                className="text-sm text-gray-500 hover:text-gray-700 mb-2"
                              >
                                Hide replies
                              </button>
                              <div className="ml-4 pl-4 border-l-2 border-gray-200 space-y-3">
                                {c.replies.map((reply) => (
                                  <div key={reply.id} className="bg-gray-50 p-3 rounded">
                                    <div className="flex items-center justify-between mb-1">
                                      <span className="font-medium text-sm text-gray-900">
                                        {reply.user?.first_name || reply.user?.username}
                                      </span>
                                      <span className="text-xs text-gray-500">{formatDate(reply.created_at)}</span>
                                    </div>
                                    <p className="text-sm text-gray-700">{reply.comment}</p>
                                  </div>
                                ))}
                              </div>
                            </>
                          )}
                        </div>
                      )}
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

            {/* Attachments */}
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Attachments ({ticket.attachments?.length || 0})
              </h3>

              {ticket.attachments?.length > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 mb-6">
                  {ticket.attachments.map((att) => {
                    const isImage = att.file_name?.match(/\.(jpg|jpeg|png|gif|webp|bmp)$/i);
                    const isVideo = att.file_name?.match(/\.(mp4|webm|mov|avi)$/i);
                    const isPdf = att.file_name?.match(/\.pdf$/i);
                    const apiBaseUrl = import.meta.env.VITE_API_URL || 'https://juan365-task-monitoring-production.up.railway.app';
                    const fileUrl = att.file?.startsWith('http') ? att.file : `${apiBaseUrl}${att.file}`;

                    return (
                      <div key={att.id} className="group relative">
                        <a
                          href={fileUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block aspect-square rounded-lg overflow-hidden bg-gray-100 hover:ring-2 hover:ring-blue-500 transition-all"
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
                              <svg className="w-12 h-12 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                            ) : isPdf ? (
                              <svg className="w-12 h-12 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                              </svg>
                            ) : (
                              <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                            )}
                            <span className="text-xs text-gray-500 mt-1 px-2 text-center truncate max-w-full">
                              {att.file_name?.split('.').pop()?.toUpperCase()}
                            </span>
                          </div>
                        </a>
                        {/* Overlay with file name and actions */}
                        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-2 rounded-b-lg opacity-0 group-hover:opacity-100 transition-opacity">
                          <p className="text-xs text-white truncate" title={att.file_name}>
                            {att.file_name}
                          </p>
                        </div>
                        {/* Delete button */}
                        {(att.user?.id === user?.id || isManager) && (
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              handleDeleteAttachment(att.id);
                            }}
                            className="absolute top-1 right-1 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                            title="Delete attachment"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-gray-500 mb-6">No attachments yet.</p>
              )}

              {/* Upload Attachment */}
              <div className="border-t pt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Upload New File
                </label>
                <input
                  type="file"
                  onChange={handleFileUpload}
                  disabled={uploadingFile}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
                />
                {uploadingFile && (
                  <p className="mt-2 text-sm text-blue-600">Uploading file...</p>
                )}
              </div>
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
                  <dt className="text-sm text-gray-500">Department</dt>
                  <dd className="text-sm font-medium text-gray-900">
                    {ticket.target_department?.name || ticket.department || '-'}
                  </dd>
                </div>
                {(ticket.ticket_product || ticket.product) && (
                  <div>
                    <dt className="text-sm text-gray-500">Product</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {ticket.ticket_product?.name || ticket.product}
                    </dd>
                  </div>
                )}
                {ticket.request_type_display && (
                  <div>
                    <dt className="text-sm text-gray-500">Request Type</dt>
                    <dd className="text-sm font-medium text-gray-900">{ticket.request_type_display}</dd>
                  </div>
                )}
                {ticket.file_format_display && (
                  <div>
                    <dt className="text-sm text-gray-500">File Format</dt>
                    <dd className="text-sm font-medium text-gray-900">{ticket.file_format_display}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-sm text-gray-500">Deadline</dt>
                  <dd className={`text-sm font-medium ${ticket.is_overdue ? 'text-red-600' : 'text-gray-900'}`}>
                    {ticket.deadline ? formatDate(ticket.deadline) : 'Set on assignment'}
                  </dd>
                </div>
                {ticket.revision_count > 0 && (
                  <div>
                    <dt className="text-sm text-gray-500">Revisions</dt>
                    <dd className="text-sm font-medium text-orange-600">
                      {ticket.revision_count} revision{ticket.revision_count > 1 ? 's' : ''} requested
                    </dd>
                  </div>
                )}
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

            {/* Collaborators */}
            <div className="bg-white shadow rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Collaborators ({ticket.collaborators?.length || 0})
              </h3>
              {ticket.collaborators?.length > 0 ? (
                <div className="space-y-2">
                  {ticket.collaborators.map((collab) => (
                    <div key={collab.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {collab.user?.first_name || collab.user?.username}
                        </p>
                        <p className="text-xs text-gray-500">@{collab.user?.username}</p>
                      </div>
                      {(isManager || user?.id === collab.added_by?.id) && ticket.status !== 'completed' && (
                        <button
                          onClick={() => handleRemoveCollaborator(collab.user?.id)}
                          className="text-red-500 hover:text-red-700 text-sm"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">No collaborators added yet.</p>
              )}
            </div>

            {/* History & Rollback (Managers only) */}
            {isManager && (
              <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900">History & Rollback</h3>
                  <button
                    onClick={fetchHistory}
                    disabled={historyLoading}
                    className="px-3 py-1 text-sm bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
                  >
                    {historyLoading ? 'Loading...' : 'View History'}
                  </button>
                </div>
                <p className="text-sm text-gray-500">
                  View ticket activity history and restore to a previous state if needed.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* History Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 sm:p-6 w-full max-w-2xl mx-4 max-h-[80vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Ticket History</h3>
              <button
                onClick={() => setShowHistoryModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              {history.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No history available</p>
              ) : (
                <div className="space-y-3">
                  {history.map((activity, index) => (
                    <div key={activity.id} className="border rounded-lg p-3 hover:bg-gray-50">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <span className={`px-2 py-1 text-xs rounded-full ${
                              activity.action === 'created' ? 'bg-green-100 text-green-800' :
                              activity.action === 'approved' || activity.action === 'dept_approved' ? 'bg-cyan-100 text-cyan-800' :
                              activity.action === 'rejected' ? 'bg-red-100 text-red-800' :
                              activity.action === 'assigned' ? 'bg-blue-100 text-blue-800' :
                              activity.action === 'completed' ? 'bg-green-100 text-green-800' :
                              activity.action === 'rollback' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {activity.action_display}
                            </span>
                            <span className="text-sm text-gray-600">
                              by {activity.user?.first_name || activity.user?.username || 'System'}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            {new Date(activity.created_at).toLocaleString()}
                          </p>
                          {activity.details && (
                            <p className="text-sm text-gray-700 mt-1">{activity.details}</p>
                          )}
                        </div>
                        {activity.snapshot && index > 0 && (
                          <button
                            onClick={() => handleRollback(activity.id)}
                            disabled={rollbackLoading}
                            className="ml-3 px-3 py-1 text-xs bg-yellow-500 text-white rounded hover:bg-yellow-600 disabled:opacity-50"
                            title="Restore ticket to this state"
                          >
                            {rollbackLoading ? '...' : 'Restore'}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="mt-4 pt-4 border-t flex justify-end">
              <button
                onClick={() => setShowHistoryModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 sm:p-6 w-full max-w-md mx-4">
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
          <div className="bg-white rounded-lg p-4 sm:p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Assign Ticket</h3>
            <p className="text-sm text-gray-600 mb-4">
              <span className="text-blue-600 font-medium">Note:</span> Tickets can only be assigned to Creative department members.
            </p>
            {(() => {
              // Filter only Creative department members
              const creativeUsers = users?.filter(u => u.user_department_info?.is_creative) || [];
              return creativeUsers.length > 0 ? (
                <select
                  value={assignUserId}
                  onChange={(e) => setAssignUserId(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Select Creative member...</option>
                  {creativeUsers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.first_name || u.username} ({u.username}) - {u.user_department_info?.name || 'Creative'}
                    </option>
                  ))}
                </select>
              ) : (
                <p className="text-gray-500 text-sm">No Creative department members available for assignment.</p>
              );
            })()}
            <div className="mt-4 flex justify-end space-x-2">
              <button
                onClick={() => setShowAssignModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAction('assign')}
                disabled={actionLoading || !assignUserId || !users?.some(u => u.user_department_info?.is_creative)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                Assign
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirm Completion Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 sm:p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Confirm Task Completion</h3>
            <p className="text-gray-600 mb-4">
              Are you satisfied with the completed work on this ticket? By confirming, you acknowledge that the task has been completed to your satisfaction.
            </p>
            <div className="mt-4 flex justify-end space-x-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Not Yet
              </button>
              <button
                onClick={handleConfirmComplete}
                disabled={actionLoading}
                className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50"
              >
                {actionLoading ? 'Confirming...' : 'Yes, Confirm Completion'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Collaborator Modal */}
      {showCollaboratorModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 sm:p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Add Collaborator</h3>
            <p className="text-gray-600 text-sm mb-4">
              Add a team member to collaborate on this ticket. They will be notified and can work on this task.
            </p>
            {users && users.length > 0 ? (
              <select
                value={collaboratorUserId}
                onChange={(e) => setCollaboratorUserId(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">Select a collaborator...</option>
                {users
                  .filter(u =>
                    u.id !== ticket?.assigned_to?.id &&
                    u.id !== ticket?.requester?.id &&
                    !ticket?.collaborators?.some(c => c.user?.id === u.id)
                  )
                  .map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.first_name || u.username} (@{u.username})
                    </option>
                  ))}
              </select>
            ) : (
              <p className="text-gray-500 text-sm">No users available.</p>
            )}
            <div className="mt-4 flex justify-end space-x-2">
              <button
                onClick={() => {
                  setShowCollaboratorModal(false);
                  setCollaboratorUserId('');
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleAddCollaborator}
                disabled={actionLoading || !collaboratorUserId}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {actionLoading ? 'Adding...' : 'Add Collaborator'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 sm:p-6 w-full max-w-md mx-4">
            <div className="flex items-center space-x-3 mb-4">
              <div className="flex-shrink-0 bg-red-100 rounded-full p-2">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900">Move to Trash</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Are you sure you want to move ticket <strong>#{ticket?.id} - {ticket?.title}</strong> to trash?
            </p>
            <p className="text-sm text-gray-500 mb-4">
              The ticket can be restored from the Trash page by managers.
            </p>
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSoftDelete}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                {actionLoading ? 'Deleting...' : 'Move to Trash'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Request Revision Modal */}
      {showRevisionModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 sm:p-6 w-full max-w-md mx-4">
            <div className="flex items-center space-x-3 mb-4">
              <div className="flex-shrink-0 bg-orange-100 rounded-full p-2">
                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900">Request Revision</h3>
            </div>
            {ticket.revision_count > 0 && (
              <p className="text-sm text-orange-600 mb-3">
                This will be revision #{ticket.revision_count + 1}
              </p>
            )}
            <p className="text-gray-600 text-sm mb-4">
              Please describe what changes or corrections are needed. The designer will be notified and the ticket will return to In Progress status.
            </p>
            <textarea
              value={revisionComments}
              onChange={(e) => setRevisionComments(e.target.value)}
              rows={4}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-orange-500 focus:border-orange-500"
              placeholder="Describe the changes needed..."
            />
            <div className="mt-4 flex justify-end space-x-2">
              <button
                onClick={() => {
                  setShowRevisionModal(false);
                  setRevisionComments('');
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleRequestRevision}
                disabled={actionLoading || !revisionComments.trim()}
                className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50"
              >
                {actionLoading ? 'Submitting...' : 'Request Revision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default TicketDetail;
