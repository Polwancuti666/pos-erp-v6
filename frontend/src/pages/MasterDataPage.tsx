import { useState, useEffect, useRef } from 'react';
import { api, fetchJSON } from '../api/client';

type Tab = 'treatment' | 'product' | 'coa' | 'user' | 'branch' | 'customer' | 'voucher' | 'promo' | 'loyalty' | 'treatment-category' | 'treatment-subcategory' | 'product-category' | 'product-subcategory';

interface Treatment { id: string; name: string; category: string; category_id?: string; duration: number; duration_minutes?: number; price: number; description?: string; commission_rate?: number; }
interface Product { id: string; name: string; sku: string; category: string; category_id?: string; category_name?: string; subcategory_id?: string; subcategory_name?: string; bom_name?: string; unit?: string; price: number; stock: number; qty?: number; barcode?: string; receipt_tolerance?: number; status_uom?: string; description?: string; min_stock_threshold?: number; }
interface COA { id: string; code: string; account_code?: string; name: string; account_name?: string; type: string; account_type?: string; parent_code?: string; level?: number; }
interface User { id: string; user_code?: string; name: string; username?: string; full_name?: string; email: string; role: string; branch: string; branch_id?: string; branch_name?: string; pin?: string; }
interface Branch { id: string; code: string; name: string; address: string; phone: string; }
interface Customer { id: string; name: string; phone: string; email: string; notes: string; created_at: string; }
interface Voucher { id: string; code: string; name: string; type: string; value: number; min_purchase?: number; max_discount?: number; start_date?: string; end_date?: string; usage_limit?: number; }
interface Promo { id: string; name: string; type: string; value: number; min_purchase?: number; start_date?: string; end_date?: string; applicable_to?: string; }
interface TreatmentCategory { id: string; name: string; coa_id?: string; coa_code?: string; coa_name?: string; }
interface ProductCategory { id: string; name: string; coa_id?: string; coa_code?: string; coa_name?: string; }
interface ProductSubcategory { id: string; name: string; category_id: string; }
interface TreatmentSubcategory { id: string; name: string; category_id: string; }

const tabs: { key: Tab; label: string }[] = [
  { key: 'treatment', label: 'Treatments' },
  { key: 'product', label: 'Products' },
  { key: 'coa', label: 'Chart of Accounts' },
  { key: 'user', label: 'Users' },
  { key: 'branch', label: 'Branches' },
  { key: 'customer', label: 'Customers' },
  { key: 'voucher', label: '🎫 Vouchers' },
  { key: 'promo', label: '🏷️ Promos' },
  { key: 'loyalty', label: '⭐ Loyalty' },
  { key: 'treatment-category', label: '📂 Treatment Category' },
  { key: 'treatment-subcategory', label: '📂 Treatment Subcategory' },
  { key: 'product-category', label: '📦 Product Category' },
  { key: 'product-subcategory', label: '📦 Product Subcategory' },
];

const moduleApiMap: Record<string, string> = {
  treatment: 'treatment',
  product: 'product',
  coa: 'coa',
  user: 'user',
  branch: 'branch',
  customer: 'customer',
  voucher: 'voucher',
  promo: 'promotion',
  'treatment-category': 'treatment-category',
  'treatment-subcategory': 'treatment-subcategory',
  'product-category': 'product-category',
  'product-subcategory': 'product-subcategory',
};

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

// Export products to CSV
async function exportProducts(format: string) {
  const base = '/master/product/export';
  const urls: Record<string, string> = {
    csv: `${base}/csv`,
    xlsx: `${base}/xlsx`,
    pdf: `${base}/pdf`,
    json: `${base}`,
  };
  const url = urls[format];
  if (!url) return;
  try {
    if (format === 'json') {
      const res = await fetchJSON(url);
      const blob = new Blob([JSON.stringify(res.items || [], null, 2)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `products-export.json`;
      a.click();
      URL.revokeObjectURL(a.href);
    } else if (format === 'csv') {
      const res = await fetchJSON(url);
      // Server returns StreamingResponse; for CSV we use fetch + blob
      const token = localStorage.getItem('erp_token') || localStorage.getItem('pos_token') || '';
      const branchId = localStorage.getItem('erp_branch_id') || '';
      const fullUrl = `/api${url}${branchId && branchId !== 'all' ? '?branch_id=' + encodeURIComponent(branchId) : ''}`;
      const resp = await fetch(fullUrl, { headers: { 'Authorization': token ? `Bearer ${token}` : '' } });
      const blob = await resp.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `products-export.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    } else {
      // XLSX & PDF — direct download via fetch
      const token = localStorage.getItem('erp_token') || localStorage.getItem('pos_token') || '';
      const branchId = localStorage.getItem('erp_branch_id') || '';
      const fullUrl = `/api${url}${branchId && branchId !== 'all' ? '?branch_id=' + encodeURIComponent(branchId) : ''}`;
      const resp = await fetch(fullUrl, { headers: { 'Authorization': token ? `Bearer ${token}` : '' } });
      const blob = await resp.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `products-export.${format}`;
      a.click();
      URL.revokeObjectURL(a.href);
    }
  } catch (err: any) {
    alert('Export failed: ' + err.message);
  }
}

function LoyaltySection() {
  const [summary, setSummary] = useState<any>(null);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);
  const [customerHistory, setCustomerHistory] = useState<any[]>([]);
  const [earnPoints, setEarnPoints] = useState('');
  const [redeemPoints, setRedeemPoints] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    Promise.all([api.getLoyaltySummary(), api.getLoyaltyLeaderboard()])
      .then(([s, l]) => { setSummary(s); setLeaderboard(l.items || []); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const loadCustomer = async (id: string) => {
    try {
      const res = await api.getCustomerLoyalty(id);
      setSelectedCustomer(res.customer);
      setCustomerHistory(res.history || []);
    } catch (err: any) { alert('Error: ' + err.message); }
  };

  const handleEarn = async () => {
    if (!selectedCustomer || !earnPoints) return;
    setActionLoading(true);
    try {
      await api.earnLoyaltyPoints(selectedCustomer.id, { points: parseInt(earnPoints), description: 'Manual add by admin' });
      setEarnPoints('');
      await loadCustomer(selectedCustomer.id);
      const [s, l] = await Promise.all([api.getLoyaltySummary(), api.getLoyaltyLeaderboard()]);
      setSummary(s); setLeaderboard(l.items || []);
    } catch (err: any) { alert('Error: ' + err.message); }
    finally { setActionLoading(false); }
  };

  const handleRedeem = async () => {
    if (!selectedCustomer || !redeemPoints) return;
    setActionLoading(true);
    try {
      await api.redeemLoyaltyPoints(selectedCustomer.id, { points: parseInt(redeemPoints), description: 'Manual redeem by admin' });
      setRedeemPoints('');
      await loadCustomer(selectedCustomer.id);
      const [s, l] = await Promise.all([api.getLoyaltySummary(), api.getLoyaltyLeaderboard()]);
      setSummary(s); setLeaderboard(l.items || []);
    } catch (err: any) { alert('Error: ' + err.message); }
    finally { setActionLoading(false); }
  };

  if (loading) return <Spinner />;

  const tierColors: Record<string, string> = {
    Platinum: 'bg-purple-100 text-purple-700 border-purple-300',
    Gold: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    Silver: 'bg-gray-100 text-gray-700 border-gray-300',
    Bronze: 'bg-orange-100 text-orange-700 border-orange-300',
  };

  return (
    <div className="p-4 space-y-6">
      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
            <p className="text-xs text-gray-500">Total Members</p>
            <p className="text-2xl font-bold">{summary.total_customers}</p>
          </div>
          <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
            <p className="text-xs text-gray-500">Points Outstanding</p>
            <p className="text-2xl font-bold text-[#C9A96E]">{(summary.total_points_outstanding || 0).toLocaleString()}</p>
          </div>
          {(summary.tiers || []).map((t: any, i: number) => (
            <div key={i} className={`rounded-lg p-4 border ${tierColors[t.loyalty_tier] || 'bg-gray-50'}`}>
              <p className="text-xs opacity-70">{t.loyalty_tier}</p>
              <p className="text-xl font-bold">{t.count} members</p>
              <p className="text-xs opacity-60">{(Number(t.total_points) || 0).toLocaleString()} pts</p>
            </div>
          ))}
        </div>
      )}

      {/* Tier Info */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="font-semibold text-gray-700 mb-3">💎 Tier Benefits</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div className="text-center p-3 rounded-lg bg-orange-50 border border-orange-200">
            <p className="font-bold text-orange-700">🥉 Bronze</p>
            <p className="text-xs text-gray-500 mt-1">Rp 0+</p>
            <p className="text-xs text-gray-500">1 pt / Rp 10rb</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-gray-50 border border-gray-200">
            <p className="font-bold text-gray-700">🥈 Silver</p>
            <p className="text-xs text-gray-500 mt-1">Rp 2jt+</p>
            <p className="text-xs text-gray-500">1 pt / Rp 10rb</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-yellow-50 border border-yellow-200">
            <p className="font-bold text-yellow-700">🥇 Gold</p>
            <p className="text-xs text-gray-500 mt-1">Rp 5jt+</p>
            <p className="text-xs text-gray-500">1 pt / Rp 10rb</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-purple-50 border border-purple-200">
            <p className="font-bold text-purple-700">💎 Platinum</p>
            <p className="text-xs text-gray-500 mt-1">Rp 10jt+</p>
            <p className="text-xs text-gray-500">1 pt / Rp 10rb</p>
          </div>
        </div>
      </div>

      {/* Leaderboard + Customer Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Leaderboard */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="bg-[#C9A96E] text-white px-4 py-3 font-semibold">🏆 Top Loyalty Members</div>
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs text-gray-500">#</th>
                <th className="px-3 py-2 text-left text-xs text-gray-500">Name</th>
                <th className="px-3 py-2 text-left text-xs text-gray-500">Tier</th>
                <th className="px-3 py-2 text-right text-xs text-gray-500">Points</th>
                <th className="px-3 py-2 text-right text-xs text-gray-500">Spent</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {leaderboard.map((c: any, i: number) => (
                <tr key={c.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => loadCustomer(c.id)}>
                  <td className="px-3 py-2 text-sm">{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}</td>
                  <td className="px-3 py-2 text-sm font-medium">{c.name}</td>
                  <td className="px-3 py-2"><span className={`px-2 py-0.5 rounded-full text-xs ${tierColors[c.loyalty_tier] || ''}`}>{c.loyalty_tier}</span></td>
                  <td className="px-3 py-2 text-right text-sm font-semibold">{(c.loyalty_points || 0).toLocaleString()}</td>
                  <td className="px-3 py-2 text-right text-sm text-gray-500">{new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(c.total_spent || 0)}</td>
                </tr>
              ))}
              {leaderboard.length === 0 && (
                <tr><td colSpan={5} className="px-3 py-6 text-center text-gray-400">No loyalty members yet</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Customer Detail */}
        <div className="bg-white rounded-lg border border-gray-200">
          {selectedCustomer ? (
            <div>
              <div className="bg-[#C9A96E] text-white px-4 py-3 flex justify-between items-center">
                <span className="font-semibold">👤 {selectedCustomer.name}</span>
                <button onClick={() => { setSelectedCustomer(null); setCustomerHistory([]); }} className="text-white/80 hover:text-white">✕</button>
              </div>
              <div className="p-4 space-y-4">
                {/* Info */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center p-3 bg-[#C9A96E]/10 rounded-lg">
                    <p className="text-xs text-gray-500">Tier</p>
                    <p className="font-bold">{selectedCustomer.loyalty_tier}</p>
                  </div>
                  <div className="text-center p-3 bg-[#C9A96E]/10 rounded-lg">
                    <p className="text-xs text-gray-500">Points</p>
                    <p className="font-bold text-[#C9A96E]">{(selectedCustomer.loyalty_points || 0).toLocaleString()}</p>
                  </div>
                  <div className="text-center p-3 bg-[#C9A96E]/10 rounded-lg">
                    <p className="text-xs text-gray-500">Total Spent</p>
                    <p className="font-bold">{new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(selectedCustomer.total_spent || 0)}</p>
                  </div>
                </div>
                {/* Actions */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex gap-2">
                    <input type="number" value={earnPoints} onChange={e => setEarnPoints(e.target.value)} placeholder="Points" className="flex-1 border rounded px-2 py-1 text-sm" />
                    <button onClick={handleEarn} disabled={actionLoading || !earnPoints} className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 disabled:opacity-50">+ Earn</button>
                  </div>
                  <div className="flex gap-2">
                    <input type="number" value={redeemPoints} onChange={e => setRedeemPoints(e.target.value)} placeholder="Points" className="flex-1 border rounded px-2 py-1 text-sm" />
                    <button onClick={handleRedeem} disabled={actionLoading || !redeemPoints} className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 disabled:opacity-50">- Redeem</button>
                  </div>
                </div>
                {/* History */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-600 mb-2">Transaction History</h4>
                  <div className="max-h-48 overflow-y-auto space-y-1">
                    {customerHistory.map((h: any, i: number) => (
                      <div key={i} className="flex justify-between items-center text-sm py-1 px-2 rounded hover:bg-gray-50">
                        <div>
                          <span className={`font-mono ${h.reason === 'earn' ? 'text-green-600' : 'text-red-600'}`}>
                            {h.reason === 'earn' ? '+' : ''}{h.points_change} pts
                          </span>
                          <span className="text-gray-400 ml-2">{h.description}</span>
                        </div>
                        <span className="text-xs text-gray-400">{new Date(h.created_at).toLocaleDateString('id-ID')}</span>
                      </div>
                    ))}
                    {customerHistory.length === 0 && <p className="text-gray-400 text-sm">No history</p>}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-400">
              <p>👈 Click a customer to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


export default function MasterDataPage() {
  const [activeTab, setActiveTab] = useState<Tab>('treatment');
  const [data, setData] = useState<Record<Tab, any[]>>({
    treatment: [], product: [], coa: [], user: [], branch: [], customer: [], voucher: [], promo: [], loyalty: [],
    'treatment-category': [], 'treatment-subcategory': [], 'product-category': [], 'product-subcategory': [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Categories for dropdowns
  const [treatmentCategories, setTreatmentCategories] = useState<any[]>([]);
  const [productCategories, setProductCategories] = useState<any[]>([]);
  const [productSubcategories, setProductSubcategories] = useState<any[]>([]);
  const [treatmentSubcategories, setTreatmentSubcategories] = useState<any[]>([]);
  const [coaList, setCoaList] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);

  // Generic modal state
  const [editingItem, setEditingItem] = useState<any | null>(null);
  const [isNewItem, setIsNewItem] = useState(false);
  const [saving, setSaving] = useState(false);

  // Bulk upload modal
  const [showBulkUpload, setShowBulkUpload] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);

  // Customer search
  const [customerSearch, setCustomerSearch] = useState('');

  // Load categories on mount
  useEffect(() => {
    api.getTreatmentCategories().then(res => {
      setTreatmentCategories(Array.isArray(res) ? res : res.items || res.data || []);
    }).catch(() => {});
    api.getProductCategories().then(res => {
      setProductCategories(Array.isArray(res) ? res : res.items || res.data || []);
    }).catch(() => {});
    fetchJSON('/master/product-subcategory').then(res => {
      setProductSubcategories(Array.isArray(res) ? res : res.items || res.data || []);
    }).catch(() => {});
    fetchJSON('/master/treatment-subcategory').then(res => {
      setTreatmentSubcategories(Array.isArray(res) ? res : res.items || res.data || []);
    }).catch(() => {});
    fetchJSON('/master/coa').then(res => {
      setCoaList(Array.isArray(res) ? res : res.items || res.data || []);
    }).catch(() => {});
    fetchJSON('/master/branch').then(res => {
      setBranches(Array.isArray(res) ? res : res.items || res.data || []);
    }).catch(() => {});
  }, []);

  // Fetch data for active tab
  useEffect(() => {
    setLoading(true);
    setError(null);
    const fetchers: Record<Tab, () => Promise<any>> = {
      treatment: api.getTreatments,
      product: api.getProducts,
      coa: api.getCOA,
      user: api.getUsers,
      branch: api.getBranches,
      customer: () => api.getCustomers(customerSearch || undefined),
      voucher: () => fetchJSON('/master/voucher'),
      promo: () => fetchJSON('/master/promotion'),
      loyalty: api.getLoyaltyLeaderboard,
      'treatment-category': () => fetchJSON('/master/treatment-category'),
      'treatment-subcategory': () => fetchJSON('/master/treatment-subcategory'),
      'product-category': () => fetchJSON('/master/product-category'),
      'product-subcategory': () => fetchJSON('/master/product-subcategory'),
    };
    fetchers[activeTab]()
      .then((res) => setData((prev) => ({ ...prev, [activeTab]: Array.isArray(res) ? res : res.items || res.data || [] })))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [activeTab, customerSearch]);

  // Reload helper for current tab
  const reload = async () => {
    setLoading(true);
    try {
      const fetchers: Record<Tab, () => Promise<any>> = {
        treatment: api.getTreatments,
        product: api.getProducts,
        coa: api.getCOA,
        user: api.getUsers,
        branch: api.getBranches,
        customer: () => api.getCustomers(customerSearch || undefined),
        voucher: () => fetchJSON('/master/voucher'),
        promo: () => fetchJSON('/master/promotion'),
        loyalty: api.getLoyaltyLeaderboard,
        'treatment-category': () => fetchJSON('/master/treatment-category'),
        'treatment-subcategory': () => fetchJSON('/master/treatment-subcategory'),
        'product-category': () => fetchJSON('/master/product-category'),
        'product-subcategory': () => fetchJSON('/master/product-subcategory'),
      };
      const res = await fetchers[activeTab]();
      setData((prev) => ({ ...prev, [activeTab]: Array.isArray(res) ? res : res.items || res.data || [] }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Delete handler
  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this record?')) return;
    try {
      const apiPath = moduleApiMap[activeTab];
      await fetchJSON(`/master/${apiPath}/${id}`, { method: 'DELETE' });
      await reload();
    } catch (err: any) {
      alert('Delete failed: ' + err.message);
    }
  };

  // Save handler (create or update)
  const handleSave = async (formData: any) => {
    setSaving(true);
    try {
      const apiPath = moduleApiMap[activeTab];
      if (isNewItem) {
        await fetchJSON(`/master/${apiPath}`, { method: 'POST', body: JSON.stringify(formData) });
      } else {
        await fetchJSON(`/master/${apiPath}/${editingItem.id}`, { method: 'PUT', body: JSON.stringify(formData) });
      }
      await reload();
      setEditingItem(null);
    } catch (err: any) {
      alert('Save failed: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  // Open add modal
  const openAdd = () => {
    setIsNewItem(true);
    switch (activeTab) {
      case 'treatment':
        setEditingItem({ id: '', name: '', category_id: '', duration_minutes: 60, price: 0, description: '', commission_rate: 0 });
        break;
      case 'product':
        setEditingItem({ id: '', name: '', category_id: '', subcategory_id: '', sku: '', unit: 'pcs', barcode: '', receipt_tolerance: 0, status_uom: 'active', price: 0, description: '', min_stock_threshold: 10 });
        break;
      case 'coa':
        setEditingItem({ id: '', account_code: '', account_name: '', account_type: 'Asset', parent_code: '', level: 1 });
        break;
      case 'user':
        setEditingItem({ id: '', user_code: '', username: '', password: '', pin: '', full_name: '', role: 'staff', branch_id: '' });
        break;
      case 'branch':
        setEditingItem({ id: '', code: '', name: '', address: '', phone: '' });
        break;
      case 'customer':
        setEditingItem({ id: '', name: '', phone: '', email: '', notes: '', created_at: '' });
        break;
      case 'voucher':
        setEditingItem({ id: '', code: '', name: '', type: 'percentage', value: 0, min_purchase: 0, max_discount: 0, start_date: '', end_date: '', usage_limit: 0 });
        break;
      case 'promo':
        setEditingItem({ id: '', name: '', type: 'percentage', value: 0, min_purchase: 0, start_date: '', end_date: '', applicable_to: '' });
        break;
      case 'treatment-category':
        setEditingItem({ id: '', name: '', coa_id: '' });
        break;
      case 'product-category':
        setEditingItem({ id: '', name: '', coa_id: '' });
        break;
      case 'product-subcategory':
        setEditingItem({ id: '', name: '', category_id: '' });
        break;
      case 'treatment-subcategory':
        setEditingItem({ id: '', name: '', category_id: '' });
        break;
    }
  };

  // Open edit modal
  const openEdit = (item: any) => {
    setIsNewItem(false);
    setEditingItem({ ...item });
  };

  // Action toolbar (Add, Bulk Upload, Template)
  const renderToolbar = () => {
    if (activeTab === 'loyalty') return null;
    const apiPath = moduleApiMap[activeTab];
    const tabLabel = tabs.find(t => t.key === activeTab)?.label || activeTab;
    return (
      <div className="p-4 flex items-center gap-3 border-b border-gray-100">
        {activeTab === 'customer' && (
          <input
            type="text"
            placeholder="🔍 Cari nama atau no HP..."
            value={customerSearch}
            onChange={(e) => setCustomerSearch(e.target.value)}
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[#C9A96E] focus:border-transparent"
          />
        )}
        <div className="flex gap-2 ml-auto">
          <button
            onClick={openAdd}
            className="bg-[#C9A96E] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#8B6914] whitespace-nowrap"
          >+ Add</button>
          <button
            onClick={() => setShowBulkUpload(true)}
            className="bg-white border border-[#C9A96E] text-[#C9A96E] px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#C9A96E]/10 whitespace-nowrap"
          >📥 Bulk Upload</button>
          <button
            onClick={() => downloadTemplate(apiPath, tabLabel)}
            className="bg-white border border-gray-300 text-gray-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 whitespace-nowrap"
          >📄 Template</button>
          {activeTab === 'product' && (
            <div className="relative">
              <button
                onClick={() => setShowExportMenu(!showExportMenu)}
                className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 whitespace-nowrap flex items-center gap-1"
              >📊 Export to ▾</button>
              {showExportMenu && (
                <div className="absolute right-0 mt-1 w-44 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
                  {['CSV', 'XLSX', 'PDF', 'JSON'].map(fmt => (
                    <button
                      key={fmt}
                      onClick={() => { exportProducts(fmt.toLowerCase()); setShowExportMenu(false); }}
                      className="w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg flex items-center gap-2"
                    >
                      <span>{fmt === 'CSV' ? '📄' : fmt === 'XLSX' ? '📊' : fmt === 'PDF' ? '📕' : '🔧'}</span>
                      Export {fmt}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Edit/Add Modal
  const renderModal = () => {
    if (!editingItem) return null;
    const title = isNewItem ? `➕ Add ${activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}` : `✏️ Edit ${activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}`;

    const set = (key: string, val: any) => setEditingItem((prev: any) => ({ ...prev, [key]: val }));

    const inputCls = "w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-[#C9A96E] focus:border-transparent";
    const labelCls = "block text-sm font-medium text-gray-700 mb-1";

    const getFormData = (): any => {
      switch (activeTab) {
        case 'treatment':
          return {
            name: editingItem.name,
            category_id: editingItem.category_id,
            duration_minutes: Number(editingItem.duration_minutes) || 0,
            price: Number(editingItem.price) || 0,
            description: editingItem.description || '',
            commission_rate: Number(editingItem.commission_rate) || 0,
          };
        case 'product':
          return {
            name: editingItem.name,
            category_id: editingItem.category_id,
            subcategory_id: editingItem.subcategory_id,
            sku: editingItem.sku,
            unit: editingItem.unit || 'pcs',
            barcode: editingItem.barcode || '',
            receipt_tolerance: Number(editingItem.receipt_tolerance) || 0,
            status_uom: editingItem.status_uom || 'active',
            min_stock_threshold: Number(editingItem.min_stock_threshold) || 10,
            description: editingItem.description || '',
          };
        case 'coa':
          return {
            account_code: editingItem.account_code || editingItem.code,
            account_name: editingItem.account_name || editingItem.name,
            account_type: editingItem.account_type || editingItem.type,
            parent_code: editingItem.parent_code || '',
            level: Number(editingItem.level) || 1,
          };
        case 'user':
          const userPayload: any = {
            user_code: editingItem.user_code,
            username: editingItem.username,
            full_name: editingItem.full_name || editingItem.name,
            role: editingItem.role,
            branch_id: editingItem.branch_id,
          };
          if (isNewItem || editingItem.password) {
            userPayload.password = editingItem.password;
          }
          if (editingItem.pin) {
            userPayload.pin = editingItem.pin;
          }
          return userPayload;
        case 'branch':
          return {
            code: editingItem.code,
            name: editingItem.name,
            address: editingItem.address || '',
            phone: editingItem.phone || '',
          };
        case 'customer':
          return {
            name: editingItem.name,
            phone: editingItem.phone || '',
            email: editingItem.email || '',
            notes: editingItem.notes || '',
          };
        case 'voucher':
          return {
            code: editingItem.code,
            name: editingItem.name,
            type: editingItem.type,
            value: Number(editingItem.value) || 0,
            min_purchase: Number(editingItem.min_purchase) || 0,
            max_discount: Number(editingItem.max_discount) || 0,
            start_date: editingItem.start_date || '',
            end_date: editingItem.end_date || '',
            usage_limit: Number(editingItem.usage_limit) || 0,
          };
        case 'promo':
          return {
            name: editingItem.name,
            type: editingItem.type,
            value: Number(editingItem.value) || 0,
            min_purchase: Number(editingItem.min_purchase) || 0,
            start_date: editingItem.start_date || '',
            end_date: editingItem.end_date || '',
            applicable_to: editingItem.applicable_to || '',
          };
        case 'treatment-category':
          return { name: editingItem.name, coa_id: editingItem.coa_id || null };
        case 'product-category':
          return { name: editingItem.name, coa_id: editingItem.coa_id || null };
        case 'product-subcategory':
          return { name: editingItem.name, category_id: editingItem.category_id };
        case 'treatment-subcategory':
          return { name: editingItem.name, category_id: editingItem.category_id };
        default:
          return editingItem;
      }
    };

    const renderFields = () => {
      switch (activeTab) {
        case 'treatment':
          return (
            <>
              <div>
                <label className={labelCls}>Name *</label>
                <input type="text" value={editingItem.name || ''} onChange={e => set('name', e.target.value)} className={inputCls} placeholder="Treatment name" />
              </div>
              <div>
                <label className={labelCls}>Category</label>
                <select value={editingItem.category_id || ''} onChange={e => set('category_id', e.target.value)} className={inputCls}>
                  <option value="">-- Select Category --</option>
                  {treatmentCategories.map((c: any) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelCls}>Duration (minutes)</label>
                <input type="number" value={editingItem.duration_minutes || ''} onChange={e => set('duration_minutes', e.target.value)} className={inputCls} placeholder="60" />
              </div>
              <div>
                <label className={labelCls}>Price (Rp)</label>
                <input type="number" value={editingItem.price || ''} onChange={e => set('price', e.target.value)} className={inputCls} placeholder="0" />
              </div>
              <div>
                <label className={labelCls}>Description</label>
                <textarea value={editingItem.description || ''} onChange={e => set('description', e.target.value)} className={inputCls} rows={2} placeholder="Description" />
              </div>
              <div>
                <label className={labelCls}>Commission Rate (%)</label>
                <input type="number" step="0.01" value={editingItem.commission_rate || ''} onChange={e => set('commission_rate', e.target.value)} className={inputCls} placeholder="0" />
              </div>
            </>
          );
        case 'product':
          return (
            <>
              <div>
                <label className={labelCls}>Name *</label>
                <input type="text" value={editingItem.name || ''} onChange={e => set('name', e.target.value)} className={inputCls} placeholder="Product name" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelCls}>Category</label>
                  <select value={editingItem.category_id || ''} onChange={e => set('category_id', e.target.value)} className={inputCls}>
                    <option value="">-- Select Category --</option>
                    {productCategories.map((c: any) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Sub Category</label>
                  <select value={editingItem.subcategory_id || ''} onChange={e => set('subcategory_id', e.target.value)} className={inputCls}>
                    <option value="">-- Select Sub Category --</option>
                    {productSubcategories.filter((s: any) => !editingItem.category_id || s.category_id === editingItem.category_id).map((s: any) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelCls}>SKU</label>
                  <input type="text" value={editingItem.sku || ''} onChange={e => set('sku', e.target.value)} className={inputCls} placeholder="SKU-001" />
                </div>
                <div>
                  <label className={labelCls}>Unit</label>
                  <input type="text" value={editingItem.unit || ''} onChange={e => set('unit', e.target.value)} className={inputCls} placeholder="pcs" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelCls}>Barcode</label>
                  <input type="text" value={editingItem.barcode || ''} onChange={e => set('barcode', e.target.value)} className={inputCls} placeholder="Barcode" />
                </div>
                <div>
                  <label className={labelCls}>Receipt Tolerance (%)</label>
                  <input type="number" step="0.01" value={editingItem.receipt_tolerance || ''} onChange={e => set('receipt_tolerance', e.target.value)} className={inputCls} placeholder="0" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelCls}>Status UOM</label>
                  <select value={editingItem.status_uom || 'active'} onChange={e => set('status_uom', e.target.value)} className={inputCls}>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Min Stock Threshold</label>
                  <input type="number" value={editingItem.min_stock_threshold || ''} onChange={e => set('min_stock_threshold', e.target.value)} className={inputCls} placeholder="10" />
                </div>
              </div>
              <div>
                <label className={labelCls}>Description</label>
                <textarea value={editingItem.description || ''} onChange={e => set('description', e.target.value)} className={inputCls} rows={2} placeholder="Description" />
              </div>
            </>
          );
        case 'coa':
          return (
            <>
              <div>
                <label className={labelCls}>Account Code *</label>
                <input type="text" value={editingItem.account_code || editingItem.code || ''} onChange={e => set('account_code', e.target.value)} className={inputCls} placeholder="1001" />
              </div>
              <div>
                <label className={labelCls}>Account Name *</label>
                <input type="text" value={editingItem.account_name || editingItem.name || ''} onChange={e => set('account_name', e.target.value)} className={inputCls} placeholder="Cash" />
              </div>
              <div>
                <label className={labelCls}>Account Type</label>
                <select value={editingItem.account_type || editingItem.type || 'Asset'} onChange={e => set('account_type', e.target.value)} className={inputCls}>
                  <option value="Asset">Asset</option>
                  <option value="Liability">Liability</option>
                  <option value="Equity">Equity</option>
                  <option value="Revenue">Revenue</option>
                  <option value="Expense">Expense</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Parent Code</label>
                <input type="text" value={editingItem.parent_code || ''} onChange={e => set('parent_code', e.target.value)} className={inputCls} placeholder="1000" />
              </div>
              <div>
                <label className={labelCls}>Level</label>
                <input type="number" value={editingItem.level || 1} onChange={e => set('level', e.target.value)} className={inputCls} placeholder="1" />
              </div>
            </>
          );
        case 'user':
          return (
            <>
              <div>
                <label className={labelCls}>User Code</label>
                <input type="text" value={editingItem.user_code || ''} onChange={e => set('user_code', e.target.value)} className={inputCls} placeholder="KSR-BSD-001" />
              </div>
              <div>
                <label className={labelCls}>Username *</label>
                <input type="text" value={editingItem.username || ''} onChange={e => set('username', e.target.value)} className={inputCls} placeholder="username" />
              </div>
              <div>
                <label className={labelCls}>Password {isNewItem ? '*' : '(leave blank to keep)'}</label>
                <input type="password" value={editingItem.password || ''} onChange={e => set('password', e.target.value)} className={inputCls} placeholder={isNewItem ? 'Password' : 'Leave blank to keep'} />
              </div>
              <div>
                <label className={labelCls}>PIN (4-6 digit)</label>
                <input type="password" value={editingItem.pin || ''} onChange={e => set('pin', e.target.value)} className={inputCls} placeholder="****" maxLength={6} />
              </div>
              <div>
                <label className={labelCls}>Full Name *</label>
                <input type="text" value={editingItem.full_name || editingItem.name || ''} onChange={e => set('full_name', e.target.value)} className={inputCls} placeholder="Full name" />
              </div>
              <div>
                <label className={labelCls}>Branch</label>
                <select value={editingItem.branch_id || ''} onChange={e => set('branch_id', e.target.value)} className={inputCls}>
                  <option value="">-- Select Branch --</option>
                  {branches.map((b: any) => (
                    <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelCls}>Role</label>
                <select value={editingItem.role || 'staff'} onChange={e => set('role', e.target.value)} className={inputCls}>
                  <option value="admin">Admin</option>
                  <option value="staff">Staff</option>
                  <option value="owner">Owner</option>
                  <option value="kasir">Kasir</option>
                </select>
              </div>
            </>
          );
        case 'branch':
          return (
            <>
              <div>
                <label className={labelCls}>Code *</label>
                <input type="text" value={editingItem.code || ''} onChange={e => set('code', e.target.value)} className={inputCls} placeholder="JKT-001" />
              </div>
              <div>
                <label className={labelCls}>Branch Name *</label>
                <input type="text" value={editingItem.name || ''} onChange={e => set('name', e.target.value)} className={inputCls} placeholder="Beauty & Shine BSD" />
              </div>
              <div>
                <label className={labelCls}>Address</label>
                <textarea value={editingItem.address || ''} onChange={e => set('address', e.target.value)} className={inputCls} rows={3} placeholder="Full address" />
              </div>
              <div>
                <label className={labelCls}>Phone</label>
                <input type="text" value={editingItem.phone || ''} onChange={e => set('phone', e.target.value)} className={inputCls} placeholder="08xxx" />
              </div>
            </>
          );
        case 'customer':
          return (
            <>
              <div>
                <label className={labelCls}>Name *</label>
                <input type="text" value={editingItem.name || ''} onChange={e => set('name', e.target.value)} className={inputCls} placeholder="Customer name" />
              </div>
              <div>
                <label className={labelCls}>Phone</label>
                <input type="tel" value={editingItem.phone || ''} onChange={e => set('phone', e.target.value)} className={inputCls} placeholder="08xxx" />
              </div>
              <div>
                <label className={labelCls}>Email</label>
                <input type="email" value={editingItem.email || ''} onChange={e => set('email', e.target.value)} className={inputCls} placeholder="email@example.com" />
              </div>
              <div>
                <label className={labelCls}>Notes</label>
                <textarea value={editingItem.notes || ''} onChange={e => set('notes', e.target.value)} className={inputCls} rows={2} placeholder="Notes (allergies, preferences, etc)" />
              </div>
            </>
          );
        case 'voucher':
          return (
            <>
              <div>
                <label className={labelCls}>Code *</label>
                <input type="text" value={editingItem.code || ''} onChange={e => set('code', e.target.value)} className={inputCls} placeholder="VOUCHER-001" />
              </div>
              <div>
                <label className={labelCls}>Name *</label>
                <input type="text" value={editingItem.name || ''} onChange={e => set('name', e.target.value)} className={inputCls} placeholder="Voucher name" />
              </div>
              <div>
                <label className={labelCls}>Type</label>
                <select value={editingItem.type || 'percentage'} onChange={e => set('type', e.target.value)} className={inputCls}>
                  <option value="percentage">Percentage</option>
                  <option value="fixed">Fixed</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Value</label>
                <input type="number" value={editingItem.value || ''} onChange={e => set('value', e.target.value)} className={inputCls} placeholder="0" />
              </div>
              <div>
                <label className={labelCls}>Min Purchase (Rp)</label>
                <input type="number" value={editingItem.min_purchase || ''} onChange={e => set('min_purchase', e.target.value)} className={inputCls} placeholder="0" />
              </div>
              <div>
                <label className={labelCls}>Max Discount (Rp)</label>
                <input type="number" value={editingItem.max_discount || ''} onChange={e => set('max_discount', e.target.value)} className={inputCls} placeholder="0" />
              </div>
              <div>
                <label className={labelCls}>Start Date</label>
                <input type="date" value={editingItem.start_date || ''} onChange={e => set('start_date', e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>End Date</label>
                <input type="date" value={editingItem.end_date || ''} onChange={e => set('end_date', e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Usage Limit</label>
                <input type="number" value={editingItem.usage_limit || ''} onChange={e => set('usage_limit', e.target.value)} className={inputCls} placeholder="0 (unlimited)" />
              </div>
            </>
          );
        case 'promo':
          return (
            <>
              <div>
                <label className={labelCls}>Name *</label>
                <input type="text" value={editingItem.name || ''} onChange={e => set('name', e.target.value)} className={inputCls} placeholder="Promo name" />
              </div>
              <div>
                <label className={labelCls}>Type</label>
                <select value={editingItem.type || 'percentage'} onChange={e => set('type', e.target.value)} className={inputCls}>
                  <option value="percentage">Percentage</option>
                  <option value="fixed">Fixed</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Value</label>
                <input type="number" value={editingItem.value || ''} onChange={e => set('value', e.target.value)} className={inputCls} placeholder="0" />
              </div>
              <div>
                <label className={labelCls}>Min Purchase (Rp)</label>
                <input type="number" value={editingItem.min_purchase || ''} onChange={e => set('min_purchase', e.target.value)} className={inputCls} placeholder="0" />
              </div>
              <div>
                <label className={labelCls}>Start Date</label>
                <input type="date" value={editingItem.start_date || ''} onChange={e => set('start_date', e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>End Date</label>
                <input type="date" value={editingItem.end_date || ''} onChange={e => set('end_date', e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Applicable To</label>
                <input type="text" value={editingItem.applicable_to || ''} onChange={e => set('applicable_to', e.target.value)} className={inputCls} placeholder="e.g. all, treatment, product" />
              </div>
            </>
          );
        case 'treatment-category':
          return (
            <>
              <div>
                <label className={labelCls}>Name *</label>
                <input type="text" value={editingItem.name || ''} onChange={e => set('name', e.target.value)} className={inputCls} placeholder="Treatment category name" />
              </div>
              <div>
                <label className={labelCls}>Chart of Account (COA)</label>
                <select value={editingItem.coa_id || ''} onChange={e => set('coa_id', e.target.value || null)} className={inputCls}>
                  <option value="">-- Pilih COA --</option>
                  {coaList.map((a: any) => (
                    <option key={a.id} value={a.id}>{a.account_code} - {a.account_name}</option>
                  ))}
                </select>
              </div>
            </>
          );
        case 'product-category':
          return (
            <>
              <div>
                <label className={labelCls}>Name *</label>
                <input type="text" value={editingItem.name || ''} onChange={e => set('name', e.target.value)} className={inputCls} placeholder="Product category name" />
              </div>
              <div>
                <label className={labelCls}>Chart of Account (COA)</label>
                <select value={editingItem.coa_id || ''} onChange={e => set('coa_id', e.target.value || null)} className={inputCls}>
                  <option value="">-- Pilih COA --</option>
                  {coaList.map((a: any) => (
                    <option key={a.id} value={a.id}>{a.account_code} - {a.account_name}</option>
                  ))}
                </select>
              </div>
            </>
          );
        case 'product-subcategory':
          return (
            <>
              <div>
                <label className={labelCls}>Name *</label>
                <input type="text" value={editingItem.name || ''} onChange={e => set('name', e.target.value)} className={inputCls} placeholder="Product subcategory name" />
              </div>
              <div>
                <label className={labelCls}>Parent Category *</label>
                <select value={editingItem.category_id || ''} onChange={e => set('category_id', e.target.value)} className={inputCls}>
                  <option value="">-- Select Parent Category --</option>
                  {productCategories.map((c: any) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
            </>
          );
        case 'treatment-subcategory':
          return (
            <>
              <div>
                <label className={labelCls}>Name *</label>
                <input type="text" value={editingItem.name || ''} onChange={e => set('name', e.target.value)} className={inputCls} placeholder="Treatment subcategory name" />
              </div>
              <div>
                <label className={labelCls}>Parent Category *</label>
                <select value={editingItem.category_id || ''} onChange={e => set('category_id', e.target.value)} className={inputCls}>
                  <option value="">-- Select Parent Category --</option>
                  {treatmentCategories.map((c: any) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
            </>
          );
        default:
          return null;
      }
    };

    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
          <h3 className="text-lg font-bold text-gray-800 mb-4">{title}</h3>
          <div className="space-y-4">
            {renderFields()}
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button onClick={() => setEditingItem(null)} className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium" disabled={saving}>Cancel</button>
            <button
              onClick={() => handleSave(getFormData())}
              disabled={saving}
              className="px-6 py-2 bg-[#C9A96E] text-white rounded-lg hover:bg-[#8B6914] font-medium disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    );
  };

  const renderTable = () => {
    if (loading) return <Spinner />;
    if (error) return <div className="bg-red-50 text-red-700 p-4 rounded-lg">{error}</div>;
    const items = data[activeTab];
    if (!items.length && activeTab !== 'customer') return <div className="text-gray-500 text-center py-8">No data found</div>;

    switch (activeTab) {
      case 'treatment':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Name</th>
                <th className="px-4 py-3 text-left text-sm">Category</th>
                <th className="px-4 py-3 text-right text-sm">Duration</th>
                <th className="px-4 py-3 text-right text-sm">Price</th>
                <th className="px-4 py-3 text-center text-sm w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((t: Treatment) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{t.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{t.category_id?.slice(0, 8)}...</td>
                  <td className="px-4 py-3 text-right">{t.duration_minutes || t.duration} min</td>
                  <td className="px-4 py-3 text-right">Rp {(t.price || 0).toLocaleString()}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => openEdit(t)} className="text-[#C9A96E] hover:text-[#8B6914] font-medium text-sm">✏️</button>
                      <button onClick={() => handleDelete(t.id)} className="text-red-500 hover:text-red-700 font-medium text-sm">🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'product':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-3 py-3 text-left text-xs">Product ID</th>
                <th className="px-3 py-3 text-left text-xs">Name</th>
                <th className="px-3 py-3 text-left text-xs">SKU</th>
                <th className="px-3 py-3 text-left text-xs">Category</th>
                <th className="px-3 py-3 text-left text-xs">Sub Category</th>
                <th className="px-3 py-3 text-left text-xs">BOM Name</th>
                <th className="px-3 py-3 text-left text-xs">Unit</th>
                <th className="px-3 py-3 text-right text-xs">Qty</th>
                <th className="px-3 py-3 text-left text-xs">Barcode</th>
                <th className="px-3 py-3 text-right text-xs">Tolerance %</th>
                <th className="px-3 py-3 text-center text-xs">Status UOM</th>
                <th className="px-3 py-3 text-center text-xs w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((p: Product) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-xs font-mono text-gray-500">{String(p.id).slice(0, 8)}...</td>
                  <td className="px-3 py-2 text-sm font-medium">{p.name}</td>
                  <td className="px-3 py-2 font-mono text-sm">{p.sku}</td>
                  <td className="px-3 py-2 text-sm text-gray-500">{p.category_name || p.category_id?.slice(0, 8) || '-'}</td>
                  <td className="px-3 py-2 text-sm text-gray-500">{p.subcategory_name || '-'}</td>
                  <td className="px-3 py-2 text-sm text-gray-500">{p.bom_name || '-'}</td>
                  <td className="px-3 py-2 text-sm text-gray-500">{p.unit || 'pcs'}</td>
                  <td className={`px-3 py-2 text-right font-semibold text-sm ${(p.qty ?? p.stock ?? 0) < 10 ? 'text-red-600' : 'text-green-600'}`}>{p.qty ?? p.stock ?? '-'}</td>
                  <td className="px-3 py-2 font-mono text-sm">{p.barcode || '-'}</td>
                  <td className="px-3 py-2 text-right text-sm">{p.receipt_tolerance ?? 0}%</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${(p.status_uom || 'active') === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {p.status_uom || 'active'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => openEdit(p)} className="text-[#C9A96E] hover:text-[#8B6914] font-medium text-sm">✏️</button>
                      <button onClick={() => handleDelete(p.id)} className="text-red-500 hover:text-red-700 font-medium text-sm">🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'coa':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Code</th>
                <th className="px-4 py-3 text-left text-sm">Name</th>
                <th className="px-4 py-3 text-left text-sm">Type</th>
                <th className="px-4 py-3 text-left text-sm">Parent</th>
                <th className="px-4 py-3 text-right text-sm">Level</th>
                <th className="px-4 py-3 text-center text-sm w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((c: COA) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono">{c.account_code || c.code}</td>
                  <td className="px-4 py-3">{c.account_name || c.name}</td>
                  <td className="px-4 py-3">{c.account_type || c.type}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{c.parent_code || '-'}</td>
                  <td className="px-4 py-3 text-right">{c.level || '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => openEdit(c)} className="text-[#C9A96E] hover:text-[#8B6914] font-medium text-sm">✏️</button>
                      <button onClick={() => handleDelete(c.id)} className="text-red-500 hover:text-red-700 font-medium text-sm">🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'user':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">User Code</th>
                <th className="px-4 py-3 text-left text-sm">Username</th>
                <th className="px-4 py-3 text-left text-sm">Full Name</th>
                <th className="px-4 py-3 text-left text-sm">PIN</th>
                <th className="px-4 py-3 text-left text-sm">Role</th>
                <th className="px-4 py-3 text-left text-sm">Branch</th>
                <th className="px-4 py-3 text-center text-sm w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((u: User) => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-sm">{u.user_code || '-'}</td>
                  <td className="px-4 py-3 font-medium">{u.username || '-'}</td>
                  <td className="px-4 py-3">{u.full_name || u.name}</td>
                  <td className="px-4 py-3"><span className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-sm font-mono">****</span></td>
                  <td className="px-4 py-3"><span className="bg-[#C9A96E] bg-opacity-20 text-[#8B6914] px-2 py-1 rounded text-sm">{u.role}</span></td>
                  <td className="px-4 py-3">{u.branch_name || u.branch || '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => openEdit(u)} className="text-[#C9A96E] hover:text-[#8B6914] font-medium text-sm">✏️</button>
                      <button onClick={() => handleDelete(u.id)} className="text-red-500 hover:text-red-700 font-medium text-sm">🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'branch':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Code</th>
                <th className="px-4 py-3 text-left text-sm">Name</th>
                <th className="px-4 py-3 text-left text-sm">Address</th>
                <th className="px-4 py-3 text-left text-sm">Phone</th>
                <th className="px-4 py-3 text-center text-sm w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((b: Branch) => (
                <tr key={b.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-sm">{b.code}</td>
                  <td className="px-4 py-3 font-semibold">{b.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{b.address || '-'}</td>
                  <td className="px-4 py-3 text-sm">{b.phone || '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => openEdit(b)} className="text-[#C9A96E] hover:text-[#8B6914] font-medium text-sm">✏️</button>
                      <button onClick={() => handleDelete(b.id)} className="text-red-500 hover:text-red-700 font-medium text-sm">🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'customer':
        return (
          <>
            {items.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                {customerSearch ? 'Tidak ditemukan' : 'Belum ada pelanggan'}
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-[#C9A96E] text-white">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm">Name</th>
                    <th className="px-4 py-3 text-left text-sm">Phone</th>
                    <th className="px-4 py-3 text-left text-sm">Email</th>
                    <th className="px-4 py-3 text-left text-sm">Notes</th>
                    <th className="px-4 py-3 text-center text-sm w-24">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {items.map((c: Customer) => (
                    <tr key={c.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-semibold">{c.name}</td>
                      <td className="px-4 py-3 text-sm font-mono">{c.phone || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{c.email || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 max-w-[200px] truncate">{c.notes || '-'}</td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex justify-center gap-2">
                          <button onClick={() => openEdit(c)} className="text-[#C9A96E] hover:text-[#8B6914] font-medium text-sm">✏️</button>
                          <button onClick={() => handleDelete(c.id)} className="text-red-500 hover:text-red-700 font-medium text-sm">🗑️</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        );
      case 'voucher':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Code</th>
                <th className="px-4 py-3 text-left text-sm">Name</th>
                <th className="px-4 py-3 text-left text-sm">Type</th>
                <th className="px-4 py-3 text-right text-sm">Value</th>
                <th className="px-4 py-3 text-right text-sm">Min Purchase</th>
                <th className="px-4 py-3 text-left text-sm">Period</th>
                <th className="px-4 py-3 text-center text-sm w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((v: Voucher) => (
                <tr key={v.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-sm">{v.code}</td>
                  <td className="px-4 py-3">{v.name}</td>
                  <td className="px-4 py-3"><span className="bg-[#C9A96E] bg-opacity-20 text-[#8B6914] px-2 py-1 rounded text-sm">{v.type}</span></td>
                  <td className="px-4 py-3 text-right">{v.type === 'percentage' ? `${v.value}%` : `Rp ${(v.value || 0).toLocaleString()}`}</td>
                  <td className="px-4 py-3 text-right">Rp {(v.min_purchase || 0).toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{v.start_date || '-'} → {v.end_date || '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => openEdit(v)} className="text-[#C9A96E] hover:text-[#8B6914] font-medium text-sm">✏️</button>
                      <button onClick={() => handleDelete(v.id)} className="text-red-500 hover:text-red-700 font-medium text-sm">🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'promo':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Name</th>
                <th className="px-4 py-3 text-left text-sm">Type</th>
                <th className="px-4 py-3 text-right text-sm">Value</th>
                <th className="px-4 py-3 text-right text-sm">Min Purchase</th>
                <th className="px-4 py-3 text-left text-sm">Period</th>
                <th className="px-4 py-3 text-left text-sm">Applicable To</th>
                <th className="px-4 py-3 text-center text-sm w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((p: Promo) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{p.name}</td>
                  <td className="px-4 py-3"><span className="bg-[#C9A96E] bg-opacity-20 text-[#8B6914] px-2 py-1 rounded text-sm">{p.type}</span></td>
                  <td className="px-4 py-3 text-right">{p.type === 'percentage' ? `${p.value}%` : `Rp ${(p.value || 0).toLocaleString()}`}</td>
                  <td className="px-4 py-3 text-right">Rp {(p.min_purchase || 0).toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{p.start_date || '-'} → {p.end_date || '-'}</td>
                  <td className="px-4 py-3 text-sm">{p.applicable_to || '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => openEdit(p)} className="text-[#C9A96E] hover:text-[#8B6914] font-medium text-sm">✏️</button>
                      <button onClick={() => handleDelete(p.id)} className="text-red-500 hover:text-red-700 font-medium text-sm">🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'loyalty':
        return <LoyaltySection />;
      case 'treatment-category':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Name</th>
                <th className="px-4 py-3 text-left text-sm">Chart of Account</th>
                <th className="px-4 py-3 text-center text-sm w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((c: TreatmentCategory) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{c.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{c.coa_code && c.coa_name ? `${c.coa_code} - ${c.coa_name}` : '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => openEdit(c)} className="text-[#C9A96E] hover:text-[#8B6914] font-medium text-sm">✏️</button>
                      <button onClick={() => handleDelete(c.id)} className="text-red-500 hover:text-red-700 font-medium text-sm">🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'product-category':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Name</th>
                <th className="px-4 py-3 text-left text-sm">Chart of Account</th>
                <th className="px-4 py-3 text-center text-sm w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((c: ProductCategory) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{c.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{c.coa_code && c.coa_name ? `${c.coa_code} - ${c.coa_name}` : '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => openEdit(c)} className="text-[#C9A96E] hover:text-[#8B6914] font-medium text-sm">✏️</button>
                      <button onClick={() => handleDelete(c.id)} className="text-red-500 hover:text-red-700 font-medium text-sm">🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'product-subcategory':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Name</th>
                <th className="px-4 py-3 text-left text-sm">Parent Category</th>
                <th className="px-4 py-3 text-center text-sm w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((s: ProductSubcategory) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{s.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{productCategories.find((c: any) => c.id === s.category_id)?.name || s.category_id?.slice(0, 8) || '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => openEdit(s)} className="text-[#C9A96E] hover:text-[#8B6914] font-medium text-sm">✏️</button>
                      <button onClick={() => handleDelete(s.id)} className="text-red-500 hover:text-red-700 font-medium text-sm">🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'treatment-subcategory':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Name</th>
                <th className="px-4 py-3 text-left text-sm">Parent Category</th>
                <th className="px-4 py-3 text-center text-sm w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((s: TreatmentSubcategory) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{s.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{treatmentCategories.find((c: any) => c.id === s.category_id)?.name || s.category_id?.slice(0, 8) || '-'}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => openEdit(s)} className="text-[#C9A96E] hover:text-[#8B6914] font-medium text-sm">✏️</button>
                      <button onClick={() => handleDelete(s.id)} className="text-red-500 hover:text-red-700 font-medium text-sm">🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Master Data</h1>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
              activeTab === tab.key
                ? 'bg-[#C9A96E] text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Toolbar */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        {renderToolbar()}
        <div className="overflow-x-auto">
          {renderTable()}
        </div>
      </div>

      {/* Edit/Add Modal */}
      {renderModal()}

      {/* Bulk Upload Modal */}
      {showBulkUpload && activeTab !== 'loyalty' && (
        <BulkUploadModal
          module={activeTab}
          apiPath={moduleApiMap[activeTab]}
          onClose={() => setShowBulkUpload(false)}
          onSuccess={() => { setShowBulkUpload(false); reload(); }}
        />
      )}
    </div>
  );
}
