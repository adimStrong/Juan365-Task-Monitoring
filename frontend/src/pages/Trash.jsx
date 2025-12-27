import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ticketsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import Layout from '../components/Layout';

const Trash = () => {
  const navigate = useNavigate();
  const { isManager, user } = useAuth();
  const toast = useToast();

  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [ticketToDelete, setTicketToDelete] = useState(null);

  useEffect(() => {
    if (!isManager) {
      toast.error('Access denied. Managers only.');
      navigate('/');
      return;
    }
    fetchTrash();
  }, [isManager, navigate]);

  const fetchTrash = async () => {
    try {
      const res = await ticketsAPI.getTrash();
      setTickets(res.data);
    } catch (error) {
      console.error('Failed to fetch trash:', error);
      toast.error('Failed to load trash');
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async (ticketId) => {
    setActionLoading(ticketId);
    try {
      await ticketsAPI.restore(ticketId);
      toast.success('Ticket restored successfully!');
      setTickets(prev => prev.filter(t => t.id !== ticketId));
    } catch (error) {
      console.error('Failed to restore ticket:', error);
      toast.error(error.response?.data?.error || 'Failed to restore ticket');
    } finally {
      setActionLoading(null);
    }
  };

  const handlePermanentDelete = async () => {
    if (!ticketToDelete) return;

    setActionLoading(ticketToDelete.id);
    try {
      await ticketsAPI.permanentDelete(ticketToDelete.id);
      toast.success('Ticket permanently deleted!');
      setTickets(prev => prev.filter(t => t.id !== ticketToDelete.id));
      setShowDeleteModal(false);
      setTicketToDelete(null);
    } catch (error) {
      console.error('Failed to delete ticket:', error);
      toast.error(error.response?.data?.error || 'Failed to delete ticket');
    } finally {
      setActionLoading(null);
    }
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

  const getPriorityColor = (priority) => {
    const colors = {
      low: 'text-green-600',
      medium: 'text-yellow-600',
      high: 'text-orange-600',
      urgent: 'text-red-600',
    };
    return colors[priority] || 'text-gray-600';
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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-3">
            <svg className="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            <h1 className="text-2xl font-bold text-gray-900">Trash</h1>
          </div>
          <p className="mt-2 text-gray-600">
            Deleted tickets can be restored or permanently removed.
          </p>
        </div>

        {/* Tickets */}
        {tickets.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">Trash is empty</h3>
            <p className="mt-1 text-sm text-gray-500">No deleted tickets found.</p>
          </div>
        ) : (
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <ul className="divide-y divide-gray-200">
              {tickets.map((ticket) => (
                <li key={ticket.id} className="p-6 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-3">
                        <span className="text-sm font-medium text-gray-500">#{ticket.id}</span>
                        <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(ticket.status)}`}>
                          {ticket.status.replace('_', ' ')}
                        </span>
                        <span className={`text-xs font-medium ${getPriorityColor(ticket.priority)}`}>
                          {ticket.priority}
                        </span>
                      </div>
                      <h3 className="mt-1 text-lg font-medium text-gray-900 truncate">
                        {ticket.title}
                      </h3>
                      <div className="mt-2 flex items-center text-sm text-gray-500 space-x-4">
                        <span>
                          By: {ticket.requester?.first_name || ticket.requester?.username}
                        </span>
                        <span>
                          Deleted: {new Date(ticket.deleted_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleRestore(ticket.id)}
                        disabled={actionLoading === ticket.id}
                        className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 disabled:opacity-50"
                      >
                        {actionLoading === ticket.id ? 'Restoring...' : 'Restore'}
                      </button>
                      {user?.role === 'admin' && (
                        <button
                          onClick={() => {
                            setTicketToDelete(ticket);
                            setShowDeleteModal(true);
                          }}
                          disabled={actionLoading === ticket.id}
                          className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 disabled:opacity-50"
                        >
                          Delete Forever
                        </button>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Permanent Delete Confirmation Modal */}
      {showDeleteModal && ticketToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center space-x-3 mb-4">
              <div className="flex-shrink-0 bg-red-100 rounded-full p-2">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900">Permanently Delete Ticket</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Are you sure you want to permanently delete <strong>#{ticketToDelete.id} - {ticketToDelete.title}</strong>?
            </p>
            <p className="text-red-600 text-sm mb-4">
              This action cannot be undone. All comments, attachments, and history will be lost.
            </p>
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setTicketToDelete(null);
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handlePermanentDelete}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                {actionLoading ? 'Deleting...' : 'Delete Forever'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default Trash;
