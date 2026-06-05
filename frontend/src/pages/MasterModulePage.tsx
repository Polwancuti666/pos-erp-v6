import { useState, useEffect, useRef } from 'react';
import { fetchJSON } from '../api/client';
import { useNavigate } from 'react-router-dom';

// Generic interfaces
interface BaseItem {
  id: string;
  [key: string]: any;
}

// Spinner component
function Spinner() {
  return (
    <div className="flex justify-center py-8">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#C9A96E]"></div>
    </div>
  );
}

// Bulk Upload Modal
function BulkUploadModal({ module, apiPath, onClose, onSuccess }: { module: string; apiPath: string; onClose: () => void; onSuccess: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ inserted?: number; errors?: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const text = await file.text();
      const items = JSON.parse(text);
      if (!Array.isArray(items)) throw new Error('File must contain a JSON array');
      const res = await fetchJSON(`/master/${apiPath}/bulk-upload`, {
        method: 'POST',
        body: JSON.stringify({ items }),
      });
      setResult(res);
      onSuccess();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md">
        <h3 className="text-lg font-bold text-gray-800 mb-4">📥 Bulk Upload — {module}</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Select JSON file</label>
            <input
              ref={fileRef}
              type="file"
              accept=".json"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          {error && <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{error}</div>}
          {result && (
            <div className="bg-green-50 text-green-700 p-3 rounded-lg text-sm">
              <p>✅ Inserted: {result.inserted ?? 0}</p>
              {result.errors && result.errors.length > 0 && (
                <div className="mt-2">
                  <p className="font-semibold">Errors:</p>
                  <ul className="list-disc list-inside">
                    {result.errors.map((e, i) => <li key={i}>{e}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium">Close</button>
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="px-6 py-2 bg-[#C9A96E] text-white rounded-lg hover:bg-[#8B6914] font-medium disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </div>
    </div>
  );
}

// Download template
async function downloadTemplate(apiPath: string, moduleName: string) {
  try {
    const res = await fetchJSON(`/master/${apiPath}/template`);
    const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${moduleName}-template.json`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err: any) {
    alert('Failed to download template: ' + err.message);
  }
}

// Export to CSV
async function exportToCSV(apiPath: string, moduleName: string) {
  try {
    const res = await fetchJSON(`/master/${apiPath}/export/csv`);
    const blob = new Blob([res], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${moduleName}-export.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err: any) {
    alert('Failed to export: ' + err.message);
  }
}

// Master data module configurations
const MODULE_CONFIG: Record<string, {
  title: string;
  icon: string;
  apiPath: string;
  columns: { key: string; label: string; render?: (item: BaseItem) => React.ReactNode }[];
  formFields: { key: string; label: string; type: 'text' | 'number' | 'select' | 'textarea'; options?: { value: string; label: string }[]; required?: boolean }[];
  searchFields: string[];
}> = {
  treatment: {
    title: 'Treatments',
    icon: '💆',
    apiPath: 'treatment',
    columns: [
      { key: 'name', label: 'Name' },
      { key: 'category', label: 'Category' },
      { key: 'duration', label: 'Duration (min)', render: (item) => `${item.duration || item.duration_minutes || 0} min` },
      { key: 'price', label: 'Price', render: (item) => `Rp ${(item.price || 0).toLocaleString()}` },
      { key: 'commission_rate', label: 'Commission', render: (item) => item.commission_rate ? `${item.commission_rate}%` : '-' },
    ],
    formFields: [
      { key: 'name', label: 'Treatment Name', type: 'text', required: true },
      { key: 'category_id', label: 'Category', type: 'select', required: true },
      { key: 'duration_minutes', label: 'Duration (minutes)', type: 'number', required: true },
      { key: 'price', label: 'Price', type: 'number', required: true },
      { key: 'commission_rate', label: 'Commission Rate (%)', type: 'number' },
      { key: 'description', label: 'Description', type: 'textarea' },
    ],
    searchFields: ['name', 'category'],
  },
  product: {
    title: 'Products',
    icon: '🧴',
    apiPath: 'product',
    columns: [
      { key: 'sku', label: 'SKU' },
      { key: 'name', label: 'Name' },
      { key: 'category_name', label: 'Category', render: (item) => item.category_name || item.category || '-' },
      { key: 'price', label: 'Price', render: (item) => `Rp ${(item.price || 0).toLocaleString()}` },
      { key: 'qty', label: 'Stock', render: (item) => item.qty || item.stock || 0 },
      { key: 'unit', label: 'Unit', render: (item) => item.unit || '-' },
    ],
    formFields: [
      { key: 'name', label: 'Product Name', type: 'text', required: true },
      { key: 'sku', label: 'SKU', type: 'text', required: true },
      { key: 'category_id', label: 'Category', type: 'select', required: true },
      { key: 'subcategory_id', label: 'Subcategory', type: 'select' },
      { key: 'price', label: 'Price', type: 'number', required: true },
      { key: 'unit', label: 'Unit', type: 'text' },
      { key: 'barcode', label: 'Barcode', type: 'text' },
      { key: 'description', label: 'Description', type: 'textarea' },
    ],
    searchFields: ['name', 'sku', 'barcode'],
  },
  branch: {
    title: 'Branches',
    icon: '🏢',
    apiPath: 'branch',
    columns: [
      { key: 'code', label: 'Code' },
      { key: 'name', label: 'Name' },
      { key: 'address', label: 'Address' },
      { key: 'phone', label: 'Phone' },
    ],
    formFields: [
      { key: 'code', label: 'Branch Code', type: 'text', required: true },
      { key: 'name', label: 'Branch Name', type: 'text', required: true },
      { key: 'address', label: 'Address', type: 'textarea', required: true },
      { key: 'phone', label: 'Phone', type: 'text' },
    ],
    searchFields: ['code', 'name'],
  },
  user: {
    title: 'Users',
    icon: '👩',
    apiPath: 'user',
    columns: [
      { key: 'user_code', label: 'Code', render: (item) => item.user_code || '-' },
      { key: 'full_name', label: 'Name', render: (item) => item.full_name || item.name || '-' },
      { key: 'username', label: 'Username' },
      { key: 'email', label: 'Email' },
      { key: 'role', label: 'Role' },
      { key: 'branch_name', label: 'Branch', render: (item) => item.branch_name || item.branch || '-' },
    ],
    formFields: [
      { key: 'full_name', label: 'Full Name', type: 'text', required: true },
      { key: 'username', label: 'Username', type: 'text', required: true },
      { key: 'email', label: 'Email', type: 'text', required: true },
      { key: 'role', label: 'Role', type: 'select', required: true, options: [
        { value: 'admin', label: 'Admin' },
        { value: 'manager', label: 'Manager' },
        { value: 'cashier', label: 'Cashier' },
        { value: 'therapist', label: 'Therapist' },
      ]},
      { key: 'branch_id', label: 'Branch', type: 'select', required: true },
      { key: 'pin', label: 'PIN', type: 'text' },
    ],
    searchFields: ['full_name', 'username', 'email'],
  },
  customer: {
    title: 'Customers',
    icon: '👥',
    apiPath: 'customer',
    columns: [
      { key: 'name', label: 'Name' },
      { key: 'phone', label: 'Phone' },
      { key: 'email', label: 'Email' },
      { key: 'notes', label: 'Notes' },
      { key: 'created_at', label: 'Created', render: (item) => item.created_at ? new Date(item.created_at).toLocaleDateString() : '-' },
    ],
    formFields: [
      { key: 'name', label: 'Customer Name', type: 'text', required: true },
      { key: 'phone', label: 'Phone', type: 'text' },
      { key: 'email', label: 'Email', type: 'text' },
      { key: 'notes', label: 'Notes', type: 'textarea' },
    ],
    searchFields: ['name', 'phone', 'email'],
  },
  coa: {
    title: 'Chart of Accounts',
    icon: '📒',
    apiPath: 'coa',
    columns: [
      { key: 'account_code', label: 'Code', render: (item) => item.account_code || item.code || '-' },
      { key: 'account_name', label: 'Name', render: (item) => item.account_name || item.name || '-' },
      { key: 'account_type', label: 'Type', render: (item) => item.account_type || item.type || '-' },
      { key: 'parent_code', label: 'Parent', render: (item) => item.parent_code || '-' },
      { key: 'level', label: 'Level', render: (item) => item.level || '-' },
    ],
    formFields: [
      { key: 'code', label: 'Account Code', type: 'text', required: true },
      { key: 'name', label: 'Account Name', type: 'text', required: true },
      { key: 'type', label: 'Account Type', type: 'select', required: true, options: [
        { value: 'asset', label: 'Asset' },
        { value: 'liability', label: 'Liability' },
        { value: 'equity', label: 'Equity' },
        { value: 'revenue', label: 'Revenue' },
        { value: 'expense', label: 'Expense' },
      ]},
      { key: 'parent_code', label: 'Parent Code', type: 'text' },
    ],
    searchFields: ['code', 'name', 'account_code', 'account_name'],
  },
  voucher: {
    title: 'Vouchers',
    icon: '🎫',
    apiPath: 'voucher',
    columns: [
      { key: 'code', label: 'Code' },
      { key: 'name', label: 'Name' },
      { key: 'type', label: 'Type' },
      { key: 'value', label: 'Value', render: (item) => item.type === 'percentage' ? `${item.value}%` : `Rp ${(item.value || 0).toLocaleString()}` },
      { key: 'start_date', label: 'Start', render: (item) => item.start_date ? new Date(item.start_date).toLocaleDateString() : '-' },
      { key: 'end_date', label: 'End', render: (item) => item.end_date ? new Date(item.end_date).toLocaleDateString() : '-' },
    ],
    formFields: [
      { key: 'code', label: 'Voucher Code', type: 'text', required: true },
      { key: 'name', label: 'Voucher Name', type: 'text', required: true },
      { key: 'type', label: 'Type', type: 'select', required: true, options: [
        { value: 'fixed', label: 'Fixed Amount' },
        { value: 'percentage', label: 'Percentage' },
      ]},
      { key: 'value', label: 'Value', type: 'number', required: true },
      { key: 'min_purchase', label: 'Min Purchase', type: 'number' },
      { key: 'start_date', label: 'Start Date', type: 'text' },
      { key: 'end_date', label: 'End Date', type: 'text' },
    ],
    searchFields: ['code', 'name'],
  },
  promo: {
    title: 'Promos',
    icon: '🏷️',
    apiPath: 'promotion',
    columns: [
      { key: 'name', label: 'Name' },
      { key: 'type', label: 'Type' },
      { key: 'value', label: 'Value', render: (item) => item.type === 'percentage' ? `${item.value}%` : `Rp ${(item.value || 0).toLocaleString()}` },
      { key: 'min_purchase', label: 'Min Purchase', render: (item) => item.min_purchase ? `Rp ${item.min_purchase.toLocaleString()}` : '-' },
      { key: 'start_date', label: 'Start', render: (item) => item.start_date ? new Date(item.start_date).toLocaleDateString() : '-' },
      { key: 'end_date', label: 'End', render: (item) => item.end_date ? new Date(item.end_date).toLocaleDateString() : '-' },
    ],
    formFields: [
      { key: 'name', label: 'Promo Name', type: 'text', required: true },
      { key: 'type', label: 'Type', type: 'select', required: true, options: [
        { value: 'fixed', label: 'Fixed Amount' },
        { value: 'percentage', label: 'Percentage' },
      ]},
      { key: 'value', label: 'Value', type: 'number', required: true },
      { key: 'min_purchase', label: 'Min Purchase', type: 'number' },
      { key: 'start_date', label: 'Start Date', type: 'text' },
      { key: 'end_date', label: 'End Date', type: 'text' },
      { key: 'applicable_to', label: 'Applicable To', type: 'select', options: [
        { value: 'all', label: 'All' },
        { value: 'treatment', label: 'Treatments' },
        { value: 'product', label: 'Products' },
      ]},
    ],
    searchFields: ['name'],
  },
  'treatment-category': {
    title: 'Treatment Categories',
    icon: '📂',
    apiPath: 'treatment-category',
    columns: [
      { key: 'name', label: 'Name' },
      { key: 'coa_code', label: 'COA Code', render: (item) => item.coa_code || '-' },
      { key: 'coa_name', label: 'COA Name', render: (item) => item.coa_name || '-' },
    ],
    formFields: [
      { key: 'name', label: 'Category Name', type: 'text', required: true },
      { key: 'coa_id', label: 'Chart of Account', type: 'select' },
    ],
    searchFields: ['name'],
  },
  'treatment-subcategory': {
    title: 'Treatment Subcategories',
    icon: '📂',
    apiPath: 'treatment-subcategory',
    columns: [
      { key: 'name', label: 'Name' },
      { key: 'category_id', label: 'Category ID' },
    ],
    formFields: [
      { key: 'name', label: 'Subcategory Name', type: 'text', required: true },
      { key: 'category_id', label: 'Parent Category', type: 'select', required: true },
    ],
    searchFields: ['name'],
  },
  'product-category': {
    title: 'Product Categories',
    icon: '📦',
    apiPath: 'product-category',
    columns: [
      { key: 'name', label: 'Name' },
      { key: 'coa_code', label: 'COA Code', render: (item) => item.coa_code || '-' },
      { key: 'coa_name', label: 'COA Name', render: (item) => item.coa_name || '-' },
    ],
    formFields: [
      { key: 'name', label: 'Category Name', type: 'text', required: true },
      { key: 'coa_id', label: 'Chart of Account', type: 'select' },
    ],
    searchFields: ['name'],
  },
  'product-subcategory': {
    title: 'Product Subcategories',
    icon: '📦',
    apiPath: 'product-subcategory',
    columns: [
      { key: 'name', label: 'Name' },
      { key: 'category_id', label: 'Category ID' },
    ],
    formFields: [
      { key: 'name', label: 'Subcategory Name', type: 'text', required: true },
      { key: 'category_id', label: 'Parent Category', type: 'select', required: true },
    ],
    searchFields: ['name'],
  },
};

export default function MasterModulePage({ module }: { module: string }) {
  const navigate = useNavigate();
  const config = MODULE_CONFIG[module];
  
  const [items, setItems] = useState<BaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<BaseItem | null>(null);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const [showBulkUpload, setShowBulkUpload] = useState(false);
  const [selectOptions, setSelectOptions] = useState<Record<string, { value: string; label: string }[]>>({});

  if (!config) {
    return (
      <div className="p-6">
        <div className="text-center text-gray-500">
          <p className="text-5xl mb-4">⚠️</p>
          <p className="text-lg">Module "{module}" not found</p>
          <button onClick={() => navigate('/master')} className="mt-4 text-[#C9A96E] hover:underline">
            ← Back to Master Data
          </button>
        </div>
      </div>
    );
  }

  // Fetch items
  const fetchItems = async () => {
    setLoading(true);
    try {
      const data = await fetchJSON(`/master/${config.apiPath}`);
      setItems(Array.isArray(data) ? data : data.items || data.data || []);
    } catch (err: any) {
      console.error(`Failed to fetch ${module}:`, err);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, [module]);

  // Fetch select options for dropdowns
  useEffect(() => {
    const fetchOptions = async () => {
      const options: Record<string, { value: string; label: string }[]> = {};
      
      for (const field of config.formFields) {
        if (field.type === 'select' && !field.options) {
          try {
            let endpoint = '';
            if (field.key === 'category_id') {
              endpoint = module.includes('treatment') ? '/master/treatment-category' : '/master/product-category';
            } else if (field.key === 'subcategory_id') {
              endpoint = module.includes('treatment') ? '/master/treatment-subcategory' : '/master/product-subcategory';
            } else if (field.key === 'branch_id') {
              endpoint = '/master/branch';
            } else if (field.key === 'coa_id') {
              endpoint = '/master/coa';
            }
            
            if (endpoint) {
              const data = await fetchJSON(endpoint);
              const items = Array.isArray(data) ? data : data.items || data.data || [];
              options[field.key] = items.map((item: BaseItem) => ({
                value: item.id,
                label: item.name || item.code || item.account_name || item.full_name || item.id,
              }));
            }
          } catch (err) {
            console.error(`Failed to fetch options for ${field.key}:`, err);
          }
        }
      }
      
      setSelectOptions(options);
    };
    
    fetchOptions();
  }, [module]);

  // Filter items
  const filteredItems = items.filter(item => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return config.searchFields.some(field => {
      const value = item[field];
      return value && String(value).toLowerCase().includes(searchLower);
    });
  });

  // Handle form submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingItem) {
        await fetchJSON(`/master/${config.apiPath}/${editingItem.id}`, {
          method: 'PUT',
          body: JSON.stringify(formData),
        });
      } else {
        await fetchJSON(`/master/${config.apiPath}`, {
          method: 'POST',
          body: JSON.stringify(formData),
        });
      }
      setShowForm(false);
      setEditingItem(null);
      setFormData({});
      fetchItems();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  // Handle delete
  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this item?')) return;
    try {
      await fetchJSON(`/master/${config.apiPath}/${id}`, { method: 'DELETE' });
      fetchItems();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    }
  };

  // Open edit form
  const openEdit = (item: BaseItem) => {
    setEditingItem(item);
    setFormData({ ...item });
    setShowForm(true);
  };

  // Open create form
  const openCreate = () => {
    setEditingItem(null);
    setFormData({});
    setShowForm(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <span className="text-3xl">{config.icon}</span>
            {config.title}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{filteredItems.length} items</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => exportToCSV(config.apiPath, module)}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            📤 Export CSV
          </button>
          <button
            onClick={() => downloadTemplate(config.apiPath, module)}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            📥 Template
          </button>
          <button
            onClick={() => setShowBulkUpload(true)}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            📤 Bulk Upload
          </button>
          <button
            onClick={openCreate}
            className="px-4 py-2 bg-[#C9A96E] text-white rounded-lg text-sm font-medium hover:bg-[#8B6914]"
          >
            + Add {config.title.replace(/s$/, '')}
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <input
          type="text"
          placeholder={`Search ${config.title.toLowerCase()}...`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#C9A96E] focus:border-transparent"
        />
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {loading ? (
          <Spinner />
        ) : filteredItems.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-5xl mb-4">{config.icon}</p>
            <p className="text-lg">No {config.title.toLowerCase()} found</p>
            <button onClick={openCreate} className="mt-4 text-[#C9A96E] hover:underline">
              + Add your first {config.title.replace(/s$/, '').toLowerCase()}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {config.columns.map(col => (
                    <th key={col.key} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {col.label}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredItems.map(item => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    {config.columns.map(col => (
                      <td key={col.key} className="px-4 py-3 text-sm text-gray-900">
                        {col.render ? col.render(item) : (item[col.key] || '-')}
                      </td>
                    ))}
                    <td className="px-4 py-3 text-right text-sm">
                      <button
                        onClick={() => openEdit(item)}
                        className="text-[#C9A96E] hover:text-[#8B6914] font-medium mr-3"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(item.id)}
                        className="text-red-600 hover:text-red-800 font-medium"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-gray-800 mb-4">
              {editingItem ? `Edit ${config.title.replace(/s$/, '')}` : `Add ${config.title.replace(/s$/, '')}`}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              {config.formFields.map(field => (
                <div key={field.key}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {field.label}
                    {field.required && <span className="text-red-500">*</span>}
                  </label>
                  {field.type === 'textarea' ? (
                    <textarea
                      value={formData[field.key] || ''}
                      onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                      required={field.required}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#C9A96E] focus:border-transparent"
                      rows={3}
                    />
                  ) : field.type === 'select' ? (
                    <select
                      value={formData[field.key] || ''}
                      onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                      required={field.required}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#C9A96E] focus:border-transparent"
                    >
                      <option value="">Select {field.label}</option>
                      {(field.options || selectOptions[field.key] || []).map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={field.type}
                      value={formData[field.key] || ''}
                      onChange={(e) => setFormData({ ...formData, [field.key]: field.type === 'number' ? Number(e.target.value) : e.target.value })}
                      required={field.required}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#C9A96E] focus:border-transparent"
                    />
                  )}
                </div>
              ))}
              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => { setShowForm(false); setEditingItem(null); }}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-6 py-2 bg-[#C9A96E] text-white rounded-lg hover:bg-[#8B6914] font-medium disabled:opacity-50"
                >
                  {saving ? 'Saving...' : (editingItem ? 'Update' : 'Create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bulk Upload Modal */}
      {showBulkUpload && (
        <BulkUploadModal
          module={config.title}
          apiPath={config.apiPath}
          onClose={() => setShowBulkUpload(false)}
          onSuccess={() => { setShowBulkUpload(false); fetchItems(); }}
        />
      )}
    </div>
  );
}
