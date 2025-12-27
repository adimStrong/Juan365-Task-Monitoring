import { useState } from 'react';

const TicketCard = ({ ticket, onClick }) => {
  const getPriorityColor = (priority) => {
    const colors = {
      urgent: 'bg-red-500',
      high: 'bg-orange-500',
      medium: 'bg-yellow-500',
      low: 'bg-green-500',
    };
    return colors[priority] || 'bg-gray-500';
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
      pending_creative: 'For Creative',
      approved: 'Not Yet Started',
      rejected: 'Rejected',
      in_progress: 'In Progress',
      completed: 'Completed',
    };
    return texts[status] || status?.replace('_', ' ');
  };

  const formatDate = (dateString) => {
    if (!dateString) return null;
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const isOverdue = ticket.is_overdue;

  return (
    <div
      onClick={() => onClick(ticket)}
      className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow cursor-pointer overflow-hidden"
    >
      {/* Priority bar */}
      <div className={`h-1 ${getPriorityColor(ticket.priority)}`} />

      <div className="p-4">
        {/* Title and ID */}
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-medium text-gray-900 text-sm line-clamp-2 flex-1">
            #{ticket.id} - {ticket.title}
          </h3>
          {isOverdue && (
            <span className="ml-2 flex-shrink-0">
              <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </span>
          )}
        </div>

        {/* Status badge */}
        <div className="mb-3">
          <span className={`inline-block px-2 py-1 text-xs rounded-full ${getStatusColor(ticket.status)}`}>
            {getStatusText(ticket.status)}
          </span>
        </div>

        {/* Request type and other details */}
        <div className="flex flex-wrap gap-1 mb-2">
          {ticket.request_type_display && (
            <span className="text-xs text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
              {ticket.request_type_display}
            </span>
          )}
          {ticket.criteria_display && (
            <span className={`text-xs px-2 py-0.5 rounded ${
              ticket.criteria_display === 'Image' ? 'bg-pink-50 text-pink-700' : 'bg-blue-50 text-blue-700'
            }`}>
              {ticket.criteria_display}
            </span>
          )}
          {ticket.quantity > 1 && (
            <span className="text-xs bg-teal-50 text-teal-700 px-2 py-0.5 rounded">
              Qty: {ticket.quantity}
            </span>
          )}
        </div>

        {/* Department and Product */}
        <div className="text-xs text-gray-500 mb-2 space-y-1">
          {(ticket.target_department?.name || ticket.department) && (
            <div className="flex items-center space-x-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
              <span className="truncate">{ticket.target_department?.name || ticket.department}</span>
            </div>
          )}
          {(ticket.ticket_product?.name || ticket.product) && (
            <div className="flex items-center space-x-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              <span className="truncate">{ticket.ticket_product?.name || ticket.product}</span>
            </div>
          )}
        </div>

        {/* Icons row */}
        <div className="flex items-center justify-between text-gray-500 text-xs mt-3 pt-3 border-t">
          <div className="flex items-center space-x-3">
            {/* Comments count */}
            {ticket.comment_count > 0 && (
              <div className="flex items-center space-x-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span>{ticket.comment_count}</span>
              </div>
            )}

            {/* Attachments count */}
            {ticket.attachment_count > 0 && (
              <div className="flex items-center space-x-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
                <span>{ticket.attachment_count}</span>
              </div>
            )}

            {/* Revision count */}
            {ticket.revision_count > 0 && (
              <div className="flex items-center space-x-1 text-orange-500">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>{ticket.revision_count}</span>
              </div>
            )}
          </div>

          {/* Deadline */}
          {ticket.deadline && (
            <div className={`flex items-center space-x-1 ${isOverdue ? 'text-red-500' : ''}`}>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span>{formatDate(ticket.deadline)}</span>
            </div>
          )}
        </div>

        {/* Assignee and Requester */}
        <div className="flex items-center justify-between mt-3 pt-2 border-t">
          <div className="flex items-center space-x-1">
            <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs">
              {ticket.requester?.first_name?.[0] || ticket.requester?.username?.[0] || '?'}
            </div>
            <span className="text-xs text-gray-500 truncate max-w-[60px]">
              {ticket.requester?.first_name || ticket.requester?.username}
            </span>
          </div>

          {ticket.assigned_to && (
            <div className="flex items-center space-x-1">
              <span className="text-xs text-gray-400">to</span>
              <div className="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center text-white text-xs">
                {ticket.assigned_to?.first_name?.[0] || ticket.assigned_to?.username?.[0] || '?'}
              </div>
              <span className="text-xs text-gray-500 truncate max-w-[60px]">
                {ticket.assigned_to?.first_name || ticket.assigned_to?.username}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TicketCard;
