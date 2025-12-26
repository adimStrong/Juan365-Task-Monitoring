import { useState, useEffect } from 'react';
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
      navigate(`/tickets/${response.data.id}`);
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
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create Ticket'}
            </button>
          </div>
        </form>
      </div>
    </Layout>
  );
};

export default CreateTicket;
