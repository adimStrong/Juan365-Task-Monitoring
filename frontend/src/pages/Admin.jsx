import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { departmentsAPI, productsAPI, usersAPI } from '../services/api';

const Admin = () => {
  const [activeTab, setActiveTab] = useState('departments');
  const [departments, setDepartments] = useState([]);
  const [products, setProducts] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({});

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [deptRes, prodRes, usersRes] = await Promise.all([
        departmentsAPI.list(),
        productsAPI.list(),
        usersAPI.list(),
      ]);
      setDepartments(deptRes.data);
      setProducts(prodRes.data);
      setUsers(usersRes.data);
    } catch (err) {
      setError('Failed to fetch data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const managers = users.filter(u => u.role === 'manager' || u.role === 'admin');

  const openAddModal = () => {
    setEditingItem(null);
    if (activeTab === 'departments') {
      setFormData({ name: '', description: '', manager: '', is_creative: false, is_active: true });
    } else {
      setFormData({ name: '', description: '', is_active: true });
    }
    setShowModal(true);
  };

  const openEditModal = (item) => {
    setEditingItem(item);
    if (activeTab === 'departments') {
      setFormData({
        name: item.name,
        description: item.description || '',
        manager: item.manager?.id || '',
        is_creative: item.is_creative || false,
        is_active: item.is_active,
      });
    } else {
      setFormData({
        name: item.name,
        description: item.description || '',
        is_active: item.is_active,
      });
    }
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      if (activeTab === 'departments') {
        const data = { ...formData };
        if (data.manager) { data.manager_id = data.manager; } delete data.manager;

        if (editingItem) {
          await departmentsAPI.update(editingItem.id, data);
        } else {
          await departmentsAPI.create(data);
        }
      } else {
        if (editingItem) {
          await productsAPI.update(editingItem.id, formData);
        } else {
          await productsAPI.create(formData);
        }
      }
      setShowModal(false);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.name?.[0] || 'Failed to save');
    }
  };

  const handleDelete = async (item) => {
    if (!confirm(`Are you sure you want to delete "${item.name}"?`)) return;

    try {
      if (activeTab === 'departments') {
        await departmentsAPI.delete(item.id);
      } else {
        await productsAPI.delete(item.id);
      }
      fetchData();
    } catch (err) {
      setError('Failed to delete');
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Admin Panel</h1>
          <p className="text-gray-600">Manage departments and products</p>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('departments')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'departments'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Departments ({departments.length})
            </button>
            <button
              onClick={() => setActiveTab('products')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'products'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Products ({products.length})
            </button>
          </nav>
        </div>

        {/* Add Button */}
        <div className="mb-4">
          <button
            onClick={openAddModal}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            + Add {activeTab === 'departments' ? 'Department' : 'Product'}
          </button>
        </div>

        {/* Departments Table */}
        {activeTab === 'departments' && (
          <div className="bg-white shadow rounded-lg overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="hidden md:table-cell px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase">Manager</th>
                  <th className="hidden sm:table-cell px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-3 py-2 sm:px-6 sm:py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {departments.map((dept) => (
                  <tr key={dept.id}>
                    <td className="px-3 py-3 sm:px-6 sm:py-4">
                      <div className="text-sm font-medium text-gray-900">{dept.name}</div>
                      {dept.description && (
                        <div className="text-xs sm:text-sm text-gray-500 truncate max-w-[150px] sm:max-w-none">{dept.description}</div>
                      )}
                      {/* Show manager on mobile */}
                      <div className="md:hidden text-xs text-gray-400 mt-0.5">
                        {dept.manager ? `${dept.manager.first_name} ${dept.manager.last_name || ''}` : 'No manager'}
                      </div>
                      {/* Show type badge on mobile */}
                      <div className="sm:hidden mt-1">
                        {dept.is_creative ? (
                          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 text-purple-800">Creative</span>
                        ) : (
                          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-800">Standard</span>
                        )}
                      </div>
                    </td>
                    <td className="hidden md:table-cell px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap text-sm text-gray-500">
                      {dept.manager ? (
                        <span>{dept.manager.first_name} {dept.manager.last_name || dept.manager.username}</span>
                      ) : (
                        <span className="text-gray-400">No manager</span>
                      )}
                    </td>
                    <td className="hidden sm:table-cell px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap">
                      {dept.is_creative ? (
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-purple-100 text-purple-800">
                          Creative
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
                          Standard
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        dept.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {dept.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end flex-wrap gap-1 sm:gap-0">
                        <button
                          onClick={() => openEditModal(dept)}
                          className="text-blue-600 hover:text-blue-900 sm:mr-3"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(dept)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {departments.length === 0 && (
                  <tr>
                    <td colSpan="5" className="px-3 py-6 sm:px-6 sm:py-8 text-center text-gray-500">
                      No departments found. Add one to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Products Table */}
        {activeTab === 'products' && (
          <div className="bg-white shadow rounded-lg overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="hidden sm:table-cell px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                  <th className="px-3 py-2 sm:px-6 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-3 py-2 sm:px-6 sm:py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {products.map((prod) => (
                  <tr key={prod.id}>
                    <td className="px-3 py-3 sm:px-6 sm:py-4">
                      <div className="text-sm font-medium text-gray-900">{prod.name}</div>
                      {/* Show description on mobile */}
                      {prod.description && (
                        <div className="sm:hidden text-xs text-gray-500 mt-0.5 truncate max-w-[150px]">
                          {prod.description}
                        </div>
                      )}
                    </td>
                    <td className="hidden sm:table-cell px-3 py-3 sm:px-6 sm:py-4 text-sm text-gray-500">
                      {prod.description || '-'}
                    </td>
                    <td className="px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        prod.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {prod.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-3 py-3 sm:px-6 sm:py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end flex-wrap gap-1 sm:gap-0">
                        <button
                          onClick={() => openEditModal(prod)}
                          className="text-blue-600 hover:text-blue-900 sm:mr-3"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(prod)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {products.length === 0 && (
                  <tr>
                    <td colSpan="4" className="px-3 py-6 sm:px-6 sm:py-8 text-center text-gray-500">
                      No products found. Add one to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Modal */}
        {showModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
              <div className="px-4 py-3 sm:px-6 sm:py-4 border-b border-gray-200">
                <h3 className="text-base sm:text-lg font-medium text-gray-900">
                  {editingItem ? 'Edit' : 'Add'} {activeTab === 'departments' ? 'Department' : 'Product'}
                </h3>
              </div>
              <form onSubmit={handleSubmit}>
                <div className="px-4 py-3 sm:px-6 sm:py-4 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Name *
                    </label>
                    <input
                      type="text"
                      name="name"
                      required
                      value={formData.name}
                      onChange={handleChange}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Description
                    </label>
                    <textarea
                      name="description"
                      rows={3}
                      value={formData.description}
                      onChange={handleChange}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  {activeTab === 'departments' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Manager / Approver
                        </label>
                        <select
                          name="manager"
                          value={formData.manager}
                          onChange={handleChange}
                          className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="">Select Manager</option>
                          {managers.map((user) => (
                            <option key={user.id} value={user.id}>
                              {user.first_name} {user.last_name || user.username} ({user.role})
                            </option>
                          ))}
                        </select>
                        <p className="mt-1 text-xs text-gray-500">
                          This person will approve tickets from this department
                        </p>
                      </div>
                      <div className="flex items-center">
                        <input
                          type="checkbox"
                          id="is_creative"
                          name="is_creative"
                          checked={formData.is_creative}
                          onChange={handleChange}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <label htmlFor="is_creative" className="ml-2 block text-sm text-gray-700">
                          Creative Department
                        </label>
                      </div>
                      <p className="text-xs text-gray-500 -mt-2 ml-6">
                        Mark this if this is the main creative/execution team
                      </p>
                    </>
                  )}

                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="is_active"
                      name="is_active"
                      checked={formData.is_active}
                      onChange={handleChange}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="is_active" className="ml-2 block text-sm text-gray-700">
                      Active
                    </label>
                  </div>
                </div>
                <div className="px-4 py-3 sm:px-6 sm:py-4 border-t border-gray-200 flex justify-end space-x-2 sm:space-x-3">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-3 py-2 sm:px-4 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-3 py-2 sm:px-4 bg-blue-600 text-sm text-white rounded-md hover:bg-blue-700"
                  >
                    {editingItem ? 'Save Changes' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Admin;
