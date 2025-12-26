import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ticketsAPI, departmentsAPI, productsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';

// Request type options
const REQUEST_TYPES = [
  { value: 'socmed_posting', label: 'Socmed Posting' },
  { value: 'website_banner', label: 'Website Banner (H5 & WEB)' },
  { value: 'photoshoot', label: 'Photoshoot' },
  { value: 'videoshoot', label: 'Videoshoot' },
  { value: 'live_production', label: 'Live Production' },
];

// File format options (only for Socmed Posting)
const FILE_FORMATS = [
  { value: 'still', label: 'Still' },
  { value: 'gif', label: 'Gif' },
  { value: 'video_landscape', label: 'Video (Landscape)' },
  { value: 'video_portrait', label: 'Video (Portrait)' },
];

// Priority descriptions with auto-deadline info
const PRIORITY_INFO = {
  urgent: { label: 'Urgent', deadline: '2-3 hours (2hrs still, 3hrs video)', color: 'text-red-600' },
  high: { label: 'High', deadline: '24 hours', color: 'text-orange-600' },
  medium: { label: 'Medium', deadline: '72 hours (3 days)', color: 'text-yellow-600' },
  low: { label: 'Low', deadline: '168 hours (7 days)', color: 'text-green-600' },
};

const CreateTicket = () => {
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const [loading, setLoading] = useState(false);
  const [dropdownLoading, setDropdownLoading] = useState(true);
  const [error, setError] = useState('');
  const [departments, setDepartments] = useState([]);
  const [products, setProducts] = useState([]);
  const [attachments, setAttachments] = useState([]);
  const [uploadingFiles, setUploadingFiles] = useState(false);
  const fileInputRef = useRef(null);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium',
    ticket_product: '',
    target_department: '',
    request_type: '',
    file_format: '',
  });

  // Check if user is in Social Media department
  const isSocialMediaUser = user?.user_department_info?.name?.toLowerCase().includes('social media');

  useEffect(() => {
    fetchDepartmentsAndProducts();
  }, []);

  // Auto-select user's department for Social Media users
  useEffect(() => {
    if (isSocialMediaUser && user?.user_department && !formData.target_department) {
      setFormData((prev) => ({ ...prev, target_department: user.user_department }));
    }
  }, [isSocialMediaUser, user, formData.target_department]);

  // Reset file_format when request_type changes away from socmed_posting
  useEffect(() => {
    if (formData.request_type !== 'socmed_posting' && formData.file_format) {
      setFormData((prev) => ({ ...prev, file_format: '' }));
    }
  }, [formData.request_type]);

  const fetchDepartmentsAndProducts = async () => {
    setDropdownLoading(true);
    try {
      const [deptRes, prodRes] = await Promise.all([
        departmentsAPI.list({ is_active: true }),
        productsAPI.list({ is_active: true }),
      ]);
      setDepartments(deptRes.data);
      setProducts(prodRes.data);
    } catch (err) {
      console.error('Failed to fetch departments/products', err);
    } finally {
      setDropdownLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Handle file selection
  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    const newAttachments = files.map((file) => ({
      file,
      name: file.name,
      size: file.size,
      type: file.type,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
    }));
    setAttachments((prev) => [...prev, ...newAttachments]);
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Remove attachment
  const removeAttachment = (index) => {
    setAttachments((prev) => {
      const updated = [...prev];
      // Revoke object URL to prevent memory leak
      if (updated[index].preview) {
        URL.revokeObjectURL(updated[index].preview);
      }
      updated.splice(index, 1);
      return updated;
    });
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  // Get file icon based on type
  const getFileIcon = (type) => {
    if (type.startsWith('image/')) return '🖼️';
    if (type.startsWith('video/')) return '🎬';
    if (type.includes('pdf')) return '📄';
    if (type.includes('word') || type.includes('document')) return '📝';
    if (type.includes('sheet') || type.includes('excel')) return '📊';
    return '📎';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = { ...formData };
      if (!data.ticket_product) delete data.ticket_product;
      if (!data.target_department) delete data.target_department;
      if (!data.request_type) delete data.request_type;
      if (!data.file_format) delete data.file_format;

      const response = await ticketsAPI.create(data);
      const ticketId = response.data.id;

      // Upload attachments if any
      if (attachments.length > 0) {
        setUploadingFiles(true);
        for (const attachment of attachments) {
          try {
            await ticketsAPI.addAttachment(ticketId, attachment.file);
          } catch (uploadErr) {
            console.error('Failed to upload attachment:', attachment.name, uploadErr);
          }
        }
        setUploadingFiles(false);
      }

      navigate(`/tickets/${ticketId}`);
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.file_format?.[0] || 'Failed to create ticket');
    } finally {
      setLoading(false);
    }
  };

  // Filter departments for Social Media users (only show their department unless admin)
  const getFilteredDepartments = () => {
    if (isAdmin) {
      return departments;
    }
    if (isSocialMediaUser) {
      return departments.filter((dept) => dept.id === user?.user_department);
    }
    return departments;
  };

  const filteredDepartments = getFilteredDepartments();

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <button
            onClick={() => navigate('/tickets')}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            &larr; Back to Tickets
          </button>
          <h1 className="text-2xl font-bold text-gray-900 mt-2">Create New Ticket</h1>
        </div>

        <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
              Title *
            </label>
            <input
              type="text"
              id="title"
              name="title"
              required
              value={formData.title}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="Brief description of the task"
            />
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
              Description *
            </label>
            <textarea
              id="description"
              name="description"
              required
              rows={5}
              value={formData.description}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="Detailed description of what needs to be done..."
            />
          </div>

          {/* Attachments Section - Trello Style */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Attachments
            </label>

            {/* Upload Area */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                accept="image/*,video/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
              />
              <svg className="mx-auto h-10 w-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="mt-2 text-sm text-gray-600">
                <span className="font-medium text-blue-600">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-gray-500">Images, videos, PDFs, documents up to 10MB</p>
            </div>

            {/* Attachment Previews - Trello Style Grid */}
            {attachments.length > 0 && (
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {attachments.map((attachment, index) => (
                  <div
                    key={index}
                    className="relative group bg-gray-100 rounded-lg overflow-hidden border border-gray-200"
                  >
                    {/* Preview */}
                    {attachment.preview ? (
                      <div className="aspect-square">
                        <img
                          src={attachment.preview}
                          alt={attachment.name}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    ) : (
                      <div className="aspect-square flex flex-col items-center justify-center bg-gray-50">
                        <span className="text-3xl">{getFileIcon(attachment.type)}</span>
                        <span className="text-xs text-gray-500 mt-1 uppercase">
                          {attachment.name.split('.').pop()}
                        </span>
                      </div>
                    )}

                    {/* File Info Overlay */}
                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2">
                      <p className="text-white text-xs truncate">{attachment.name}</p>
                      <p className="text-white/70 text-xs">{formatFileSize(attachment.size)}</p>
                    </div>

                    {/* Remove Button */}
                    <button
                      type="button"
                      onClick={() => removeAttachment(index)}
                      className="absolute top-1 right-1 w-6 h-6 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="target_department" className="block text-sm font-medium text-gray-700 mb-1">
                Department
              </label>
              <select
                id="target_department"
                name="target_department"
                value={formData.target_department}
                onChange={handleChange}
                disabled={dropdownLoading || (isSocialMediaUser && !isAdmin)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              >
                <option value="">{dropdownLoading ? 'Loading...' : 'Select Department'}</option>
                {filteredDepartments.map((dept) => (
                  <option key={dept.id} value={dept.id}>
                    {dept.name}
                  </option>
                ))}
              </select>
              {isSocialMediaUser && !isAdmin && (
                <p className="mt-1 text-xs text-gray-500">
                  Social Media users can only submit to their own department
                </p>
              )}
            </div>

            <div>
              <label htmlFor="ticket_product" className="block text-sm font-medium text-gray-700 mb-1">
                Product
              </label>
              <select
                id="ticket_product"
                name="ticket_product"
                value={formData.ticket_product}
                onChange={handleChange}
                disabled={dropdownLoading}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              >
                <option value="">{dropdownLoading ? 'Loading...' : 'Select Product'}</option>
                {products.map((prod) => (
                  <option key={prod.id} value={prod.id}>
                    {prod.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Type of Request and File Format */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="request_type" className="block text-sm font-medium text-gray-700 mb-1">
                Type of Request
              </label>
              <select
                id="request_type"
                name="request_type"
                value={formData.request_type}
                onChange={handleChange}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select Request Type</option>
                {REQUEST_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            {/* File Format - Only show for Socmed Posting */}
            {formData.request_type === 'socmed_posting' && (
              <div>
                <label htmlFor="file_format" className="block text-sm font-medium text-gray-700 mb-1">
                  File Format/Type
                </label>
                <select
                  id="file_format"
                  name="file_format"
                  value={formData.file_format}
                  onChange={handleChange}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Select File Format/Type</option>
                  {FILE_FORMATS.map((format) => (
                    <option key={format.value} value={format.value}>
                      {format.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Priority with auto-deadline info */}
          <div>
            <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <select
              id="priority"
              name="priority"
              value={formData.priority}
              onChange={handleChange}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              {Object.entries(PRIORITY_INFO).map(([value, info]) => (
                <option key={value} value={value}>
                  {info.label} - {info.deadline}
                </option>
              ))}
            </select>
            <p className={`mt-1 text-sm ${PRIORITY_INFO[formData.priority]?.color || 'text-gray-500'}`}>
              Deadline will be auto-calculated: <strong>{PRIORITY_INFO[formData.priority]?.deadline}</strong> from assignment
            </p>
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={() => navigate('/tickets')}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || uploadingFiles}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {(loading || uploadingFiles) && (
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              )}
              <span>
                {uploadingFiles ? 'Uploading files...' : loading ? 'Creating...' : `Create Ticket${attachments.length > 0 ? ` (${attachments.length} files)` : ''}`}
              </span>
            </button>
          </div>
        </form>
      </div>
    </Layout>
  );
};

export default CreateTicket;
