import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ticketsAPI, departmentsAPI, productsAPI } from '../services/api';
import Layout from '../components/Layout';

const CreateTicket = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [departments, setDepartments] = useState([]);
  const [products, setProducts] = useState([]);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium',
    deadline: '',
    ticket_product: '',
    target_department: '',
  });

  // Get today's date in YYYY-MM-DDTHH:MM format for min attribute
  const getMinDateTime = () => {
    const now = new Date();
    return now.toISOString().slice(0, 16);
  };

  // Get end of today for urgent priority max date
  const getMaxDateTimeForUrgent = () => {
    const today = new Date();
    today.setHours(23, 59, 59, 999);
    return today.toISOString().slice(0, 16);
  };

  useEffect(() => {
    fetchDepartmentsAndProducts();
  }, []);

  // Reset deadline when priority changes to urgent if deadline is not same day
  useEffect(() => {
    if (formData.priority === 'urgent' && formData.deadline) {
      const deadlineDate = new Date(formData.deadline);
      const today = new Date();
      if (deadlineDate.toDateString() !== today.toDateString()) {
        setFormData((prev) => ({ ...prev, deadline: '' }));
      }
    }
  }, [formData.priority]);

  const fetchDepartmentsAndProducts = async () => {
    try {
      const [deptRes, prodRes] = await Promise.all([
        departmentsAPI.list({ is_active: true }),
        productsAPI.list({ is_active: true }),
      ]);
      setDepartments(deptRes.data);
      setProducts(prodRes.data);
    } catch (err) {
      console.error('Failed to fetch departments/products', err);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  
  const validateDeadline = () => {
    if (!formData.deadline) {
      return 'Deadline is required';
    }
    const deadlineDate = new Date(formData.deadline);
    const now = new Date();
    if (deadlineDate < now) {
      return 'Deadline cannot be in the past';
    }
    if (formData.priority === 'urgent') {
      const today = new Date();
      if (deadlineDate.toDateString() !== today.toDateString()) {
        return 'Urgent tickets must have a same-day deadline';
      }
    }
    return null;
  };

const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validate deadline
    const deadlineError = validateDeadline();
    if (deadlineError) {
      setError(deadlineError);
      return;
    }

    setLoading(true);

    try {
      const data = { ...formData };
      if (!data.ticket_product) delete data.ticket_product;
      if (!data.target_department) delete data.target_department;

      const response = await ticketsAPI.create(data);
      navigate(`/tickets/${response.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create ticket');
    } finally {
      setLoading(false);
    }
  };

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
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select Department</option>
                {departments.map((dept) => (
                  <option key={dept.id} value={dept.id}>
                    {dept.name}
                  </option>
                ))}
              </select>
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
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select Product</option>
                {products.map((prod) => (
                  <option key={prod.id} value={prod.id}>
                    {prod.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
              {formData.priority === 'urgent' && (
                <p className="mt-1 text-xs text-orange-600">
                  Urgent tickets require same-day deadline
                </p>
              )}
            </div>

            <div>
              <label htmlFor="deadline" className="block text-sm font-medium text-gray-700 mb-1">
                Deadline *
              </label>
              <input
                type="datetime-local"
                id="deadline"
                name="deadline"
                required
                value={formData.deadline}
                onChange={handleChange}
                min={getMinDateTime()}
                max={formData.priority === 'urgent' ? getMaxDateTimeForUrgent() : undefined}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              {formData.priority === 'urgent' && (
                <p className="mt-1 text-xs text-orange-600">
                  Must be today
                </p>
              )}
            </div>
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
