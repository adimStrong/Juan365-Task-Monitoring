import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ticketsAPI, departmentsAPI, productsAPI, usersAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';

// Request type options
const REQUEST_TYPES = [
  { value: 'socmed_posting', label: 'Socmed Posting' },
  { value: 'website_banner', label: 'Website Banner (H5 & WEB)' },
  { value: 'photoshoot', label: 'Photoshoot' },
  { value: 'videoshoot', label: 'Videoshoot' },
  { value: 'live_production', label: 'Live Production' },
  { value: 'ads', label: 'Ads' },
  { value: 'telegram_channel', label: 'Telegram Official Channel' },
];

// File format options (only for Socmed Posting)
const FILE_FORMATS = [
  { value: 'still', label: 'Still' },
  { value: 'gif', label: 'Gif' },
  { value: 'video_landscape', label: 'Video (Landscape)' },
  { value: 'video_portrait', label: 'Video (Portrait)' },
];

// Criteria options (for manual selection)
const CRITERIA_OPTIONS = [
  { value: 'image', label: 'Image' },
  { value: 'video', label: 'Video' },
];

// Request types that require manual criteria selection
const MANUAL_CRITERIA_TYPES = ['website_banner', 'photoshoot', 'videoshoot', 'live_production', 'telegram_channel'];

// Request types that use product items (Ads, Telegram)
const PRODUCT_ITEM_TYPES = ['ads', 'telegram_channel'];

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
  const [creativeUsers, setCreativeUsers] = useState([]);
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
    quantity: 1,
    criteria: '',
    assigned_to: '',
  });
  const [productItems, setProductItems] = useState([]);

  // Check if user has a department assigned
  const hasUserDepartment = !!user?.user_department;
  // Only admins can select any department
  const canSelectAnyDepartment = isAdmin;

  useEffect(() => {
    fetchDepartmentsAndProducts();
  }, []);

  // Auto-select user's department for regular members (not admins or managers)
  useEffect(() => {
    if (!canSelectAnyDepartment && hasUserDepartment && !formData.target_department) {
      setFormData((prev) => ({ ...prev, target_department: user.user_department }));
    }
  }, [canSelectAnyDepartment, hasUserDepartment, user, formData.target_department]);

  // Reset fields when request_type changes
  useEffect(() => {
    // Reset file_format when not socmed_posting
    if (formData.request_type !== 'socmed_posting' && formData.file_format) {
      setFormData((prev) => ({ ...prev, file_format: '' }));
    }
    // Reset criteria when changing to type that doesn't need manual selection
    if (!MANUAL_CRITERIA_TYPES.includes(formData.request_type) && formData.criteria) {
      setFormData((prev) => ({ ...prev, criteria: '' }));
    }
    // Reset product_items when changing away from Ads/Telegram
    if (!PRODUCT_ITEM_TYPES.includes(formData.request_type) && productItems.length > 0) {
      setProductItems([]);
    }
    // Reset ticket_product when switching to Ads/Telegram
    if (PRODUCT_ITEM_TYPES.includes(formData.request_type) && formData.ticket_product) {
      setFormData((prev) => ({ ...prev, ticket_product: '' }));
    }
  }, [formData.request_type]);

  const fetchDepartmentsAndProducts = async () => {
    setDropdownLoading(true);
    try {
      const [deptRes, prodRes, usersRes] = await Promise.all([
        departmentsAPI.list({ is_active: true }),
        productsAPI.list({ is_active: true }),
        usersAPI.list(),
      ]);
      setDepartments(deptRes.data);
      setProducts(prodRes.data);
      // Filter to only Creative department members
      const creative = (usersRes.data || []).filter(
        (u) => u.user_department_info?.is_creative && u.is_active && u.is_approved
      );
      setCreativeUsers(creative);
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

  // Filter products by category
  const getProductsByCategory = (category) => {
    return products.filter((p) => p.category === category);
  };

  // Get general products (for standard request types)
  const generalProducts = products.filter((p) => p.category === 'general' || !p.category);
  // Get Ads products
  const adsProducts = getProductsByCategory('ads');
  // Get Telegram products
  const telegramProducts = getProductsByCategory('telegram');

  // Product items handlers
  const addProductItem = () => {
    const availableProducts =
      formData.request_type === 'ads' ? adsProducts : telegramProducts;
    if (availableProducts.length === 0) return;
    // Find first product not already added
    const usedProductIds = productItems.map((item) => item.product);
    const nextProduct = availableProducts.find((p) => !usedProductIds.includes(p.id));
    if (nextProduct) {
      setProductItems([...productItems, { product: nextProduct.id, quantity: 1 }]);
    }
  };

  const removeProductItem = (index) => {
    setProductItems(productItems.filter((_, i) => i !== index));
  };

  const updateProductItem = (index, field, value) => {
    const updated = [...productItems];
    updated[index][field] = field === 'quantity' ? Math.min(1000, Math.max(1, parseInt(value) || 1)) : value;
    setProductItems(updated);
  };

  // Get available products for selection (exclude already added ones)
  const getAvailableProducts = (currentProductId) => {
    const categoryProducts =
      formData.request_type === 'ads' ? adsProducts : telegramProducts;
    const usedProductIds = productItems.map((item) => item.product);
    return categoryProducts.filter((p) => p.id === currentProductId || !usedProductIds.includes(p.id));
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
      if (!data.criteria) delete data.criteria;
      if (!data.assigned_to) delete data.assigned_to;

      // For Ads/Telegram, include product_items
      if (PRODUCT_ITEM_TYPES.includes(formData.request_type) && productItems.length > 0) {
        data.product_items = productItems;
        // Don't send quantity for Ads/Telegram (it's per product item)
        delete data.quantity;
      }

      const response = await ticketsAPI.create(data);
      const ticketId = response.data.id;

      // Upload attachments in parallel for better performance
      if (attachments.length > 0) {
        setUploadingFiles(true);
        await Promise.all(
          attachments.map(async (attachment) => {
            try {
              await ticketsAPI.addAttachment(ticketId, attachment.file);
            } catch (uploadErr) {
              console.error('Failed to upload attachment:', attachment.name, uploadErr);
            }
          })
        );
        setUploadingFiles(false);
      }

      navigate(`/tickets/${ticketId}`);
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.file_format?.[0] || 'Failed to create ticket');
    } finally {
      setLoading(false);
    }
  };

  // Filter departments - admins and managers can see all, others only their own
  const getFilteredDepartments = () => {
    if (canSelectAnyDepartment) {
      return departments;
    }
    // Regular members can only select their own department
    if (hasUserDepartment) {
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
                disabled={dropdownLoading || (hasUserDepartment && !canSelectAnyDepartment)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              >
                <option value="">{dropdownLoading ? 'Loading...' : 'Select Department'}</option>
                {filteredDepartments.map((dept) => (
                  <option key={dept.id} value={dept.id}>
                    {dept.name}
                  </option>
                ))}
              </select>
              {hasUserDepartment && !canSelectAnyDepartment && (
                <p className="mt-1 text-xs text-gray-500">
                  You can only submit tickets to your own department
                </p>
              )}
            </div>

            {/* Product dropdown - hide for Ads/Telegram */}
            {!PRODUCT_ITEM_TYPES.includes(formData.request_type) && (
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
                  {generalProducts.map((prod) => (
                    <option key={prod.id} value={prod.id}>
                      {prod.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
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

            {/* Criteria - Manual selection for certain types */}
            {MANUAL_CRITERIA_TYPES.includes(formData.request_type) && (
              <div>
                <label htmlFor="criteria" className="block text-sm font-medium text-gray-700 mb-1">
                  Criteria (Image/Video)
                </label>
                <select
                  id="criteria"
                  name="criteria"
                  value={formData.criteria}
                  onChange={handleChange}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Select Criteria</option>
                  {CRITERIA_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Quantity - Show for non-Ads/Telegram types */}
          {formData.request_type && !PRODUCT_ITEM_TYPES.includes(formData.request_type) && (
            <div>
              <label htmlFor="quantity" className="block text-sm font-medium text-gray-700 mb-1">
                Quantity (max 1000)
              </label>
              <input
                type="number"
                id="quantity"
                name="quantity"
                min="1"
                max="1000"
                value={formData.quantity}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    quantity: Math.min(1000, Math.max(1, parseInt(e.target.value) || 1)),
                  }))
                }
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">Number of creatives needed for this request</p>
            </div>
          )}

          {/* Product Items - For Ads and Telegram */}
          {PRODUCT_ITEM_TYPES.includes(formData.request_type) && (
            <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <div className="flex items-center justify-between mb-3">
                <label className="block text-sm font-medium text-gray-700">
                  {formData.request_type === 'ads' ? 'Ads Products' : 'Telegram Products'}
                </label>
                <button
                  type="button"
                  onClick={addProductItem}
                  disabled={
                    (formData.request_type === 'ads' ? adsProducts : telegramProducts).length ===
                    productItems.length
                  }
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  + Add Product
                </button>
              </div>

              {productItems.length === 0 ? (
                <p className="text-sm text-gray-500 italic">
                  Click &quot;Add Product&quot; to add products to this request.
                </p>
              ) : (
                <div className="space-y-3">
                  {productItems.map((item, index) => (
                    <div key={index} className="flex items-center gap-3 bg-white p-3 rounded-md border border-gray-200">
                      <select
                        value={item.product}
                        onChange={(e) => updateProductItem(index, 'product', parseInt(e.target.value))}
                        className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      >
                        {getAvailableProducts(item.product).map((prod) => (
                          <option key={prod.id} value={prod.id}>
                            {prod.name}
                          </option>
                        ))}
                      </select>
                      <div className="flex items-center gap-2">
                        <label className="text-sm text-gray-600">Qty:</label>
                        <input
                          type="number"
                          min="1"
                          max="1000"
                          value={item.quantity}
                          onChange={(e) => updateProductItem(index, 'quantity', e.target.value)}
                          className="w-20 border border-gray-300 rounded-md px-2 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => removeProductItem(index)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-md"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  ))}
                  <p className="text-xs text-gray-500">
                    Total quantity: {productItems.reduce((sum, item) => sum + item.quantity, 0)} / 1000 max
                  </p>
                </div>
              )}
            </div>
          )}

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

          {/* Assign To (Optional) - Pre-assign to Creative member */}
          <div>
            <label htmlFor="assigned_to" className="block text-sm font-medium text-gray-700 mb-1">
              Assign To (Optional)
            </label>
            <select
              id="assigned_to"
              name="assigned_to"
              value={formData.assigned_to}
              onChange={handleChange}
              disabled={dropdownLoading}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
            >
              <option value="">{dropdownLoading ? 'Loading...' : 'Select Creative Member (Optional)'}</option>
              {creativeUsers.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.first_name || u.username} {u.last_name || ''}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
              Optionally pre-assign this ticket to a Creative team member. You can also assign later.
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
