import { useState, useEffect } from 'react';
import { fetchJSON } from '../api/client';

// --- Types ---
type Tab = 'production' | 'bankrecon' | 'costcenter' | 'schedule' | 'certification' | 'pricelist' | 'cancelreason' | 'recurring' | 'cashflow' | 'whatsapp' | 'executive' | 'settlement';
type PricelistSubTab = 'product' | 'treatment';

interface ProductionOrder {
  id: string; order_no: string; product_name?: string; product_id: string;
  planned_qty: number; actual_qty?: number; planned_date: string; branch_name?: string;
  status: string; created_at: string;
}
interface Reconciliation {
  id: string; recon_no: string; bank_account: string; period: string;
  bank_balance: number; book_balance: number; difference: number;
  matched_count: number; unmatched_count: number; status: string;
}
interface BankReconSummary {
  bank_balance: number; book_balance: number; difference: number;
  matched_count: number; unmatched_count: number;
}
interface CostCenter {
  id: string; code: string; name: string; branch_name?: string; branch_id?: string;
}
interface CostCenterSummary {
  items: Array<{ cost_center_id: string; code: string; name: string; total_debit: number; total_credit: number }>;
}
interface Schedule {
  id: string; therapist_name?: string; therapist_id: string; date: string;
  start_time: string; end_time: string; branch_name?: string; status: string;
}
interface Certification {
  id: string; therapist_name?: string; therapist_id: string; cert_name: string;
  issuer: string; issue_date: string; expiry_date: string; status: string; days_until_expiry?: number;
}
interface PricelistItem {
  id: string; item_name?: string; name?: string; branch_name?: string; branch_id?: string;
  price: number; valid_from: string; valid_until: string;
}
interface CancelReason {
  id: string; code: string; name: string; description: string;
}

const tabs: { key: Tab; label: string }[] = [
  { key: 'production', label: '🏭 Production' },
  { key: 'bankrecon', label: '🏦 Bank Recon' },
  { key: 'costcenter', label: '📊 Cost Center' },
  { key: 'schedule', label: '📅 Schedule' },
  { key: 'certification', label: '📜 Certification' },
  { key: 'pricelist', label: '💰 Pricelist' },
  { key: 'cancelreason', label: '❌ Cancel Reason' },
  { key: 'recurring', label: '🔁 Recurring Journal' },
  { key: 'cashflow', label: '💸 Cash Flow' },
  { key: 'whatsapp', label: '💬 WhatsApp' },
  { key: 'executive', label: '👔 Executive' },
  { key: 'settlement', label: '📋 POS Settlement' },
];

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(amount);

const Spinner = () => (
  <div className="flex justify-center py-8">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#C9A96E]"></div>
  </div>
);

const ErrorMsg = ({ msg }: { msg: string }) => (
  <div className="bg-red-50 text-red-700 p-4 rounded-lg">{msg}</div>
);

const EmptyState = ({ msg }: { msg?: string }) => (
  <div className="text-gray-500 text-center py-8">{msg || 'No data found'}</div>
);

const statusBadge = (status: string) => {
  const map: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    in_progress: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    qc_failed: 'bg-red-100 text-red-700',
    closed: 'bg-gray-100 text-gray-700',
    active: 'bg-green-100 text-green-700',
    disposed: 'bg-red-100 text-red-700',
    maintenance: 'bg-yellow-100 text-yellow-700',
    expired: 'bg-red-100 text-red-700',
    expiring: 'bg-yellow-100 text-yellow-700',
    valid: 'bg-green-100 text-green-700',
  };
  return map[status] || 'bg-gray-100 text-gray-700';
};

// ─── 1. PRODUCTION ───────────────────────────────────────────────────
function ProductionSection() {
  const [orders, setOrders] = useState<ProductionOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ product_id: '', planned_qty: '', planned_date: '', branch_id: '' });
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    fetchJSON('/wip/production-order')
      .then((res) => setOrders(Array.isArray(res) ? res : res.items || res.data || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const handleCreate = async () => {
    try {
      await fetchJSON('/wip/production-order', {
        method: 'POST',
        body: JSON.stringify({ ...form, planned_qty: Number(form.planned_qty) }),
      });
      setShowForm(false);
      setForm({ product_id: '', planned_qty: '', planned_date: '', branch_id: '' });
      load();
    } catch (err: any) { alert('Error: ' + err.message); }
  };

  const handleAction = async (id: string, action: string) => {
    setActionLoading(`${id}-${action}`);
    try {
      await fetchJSON(`/wip/production-order/${id}/${action}`, { method: 'POST' });
      load();
    } catch (err: any) { alert('Error: ' + err.message); }
    finally { setActionLoading(null); }
  };

  // Variance analysis
  const variance = orders.filter(o => o.status === 'completed' && o.actual_qty != null).map(o => ({
    ...o, variance: (o.actual_qty || 0) - o.planned_qty,
    variance_pct: o.planned_qty ? (((o.actual_qty || 0) - o.planned_qty) / o.planned_qty * 100) : 0,
  }));

  if (loading) return <Spinner />;
  if (error) return <ErrorMsg msg={error} />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Production Orders</h3>
        <button onClick={() => setShowForm(!showForm)} className="bg-[#C9A96E] text-white px-4 py-2 rounded-lg hover:bg-[#b8985d] text-sm">
          + New Order
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-50 p-4 rounded-lg border space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <input placeholder="Product ID" value={form.product_id} onChange={e => setForm({ ...form, product_id: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Planned Qty" type="number" value={form.planned_qty} onChange={e => setForm({ ...form, planned_qty: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input type="date" value={form.planned_date} onChange={e => setForm({ ...form, planned_date: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Branch ID" value={form.branch_id} onChange={e => setForm({ ...form, branch_id: e.target.value })} className="border rounded px-3 py-2 text-sm" />
          </div>
          <button onClick={handleCreate} className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700">Submit</button>
        </div>
      )}

      {!orders.length ? <EmptyState /> : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Order No</th>
                <th className="px-4 py-3 text-left text-sm">Product</th>
                <th className="px-4 py-3 text-right text-sm">Planned Qty</th>
                <th className="px-4 py-3 text-right text-sm">Actual Qty</th>
                <th className="px-4 py-3 text-left text-sm">Planned Date</th>
                <th className="px-4 py-3 text-left text-sm">Status</th>
                <th className="px-4 py-3 text-left text-sm">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {orders.map((o) => (
                <tr key={o.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-sm">{o.order_no}</td>
                  <td className="px-4 py-3">{o.product_name || o.product_id}</td>
                  <td className="px-4 py-3 text-right">{o.planned_qty}</td>
                  <td className="px-4 py-3 text-right">{o.actual_qty ?? '-'}</td>
                  <td className="px-4 py-3 text-sm">{o.planned_date}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${statusBadge(o.status)}`}>{o.status}</span>
                  </td>
                  <td className="px-4 py-3 space-x-2">
                    {o.status === 'draft' && (
                      <button onClick={() => handleAction(o.id, 'start')} disabled={actionLoading === `${o.id}-start`}
                        className="text-blue-600 hover:underline text-sm disabled:opacity-50">
                        {actionLoading === `${o.id}-start` ? '...' : 'Start'}
                      </button>
                    )}
                    {o.status === 'in_progress' && (
                      <>
                        <button onClick={() => handleAction(o.id, 'complete')} disabled={actionLoading === `${o.id}-complete`}
                          className="text-green-600 hover:underline text-sm disabled:opacity-50">
                          {actionLoading === `${o.id}-complete` ? '...' : 'Complete'}
                        </button>
                        <button onClick={() => handleAction(o.id, 'qc')} disabled={actionLoading === `${o.id}-qc`}
                          className="text-orange-600 hover:underline text-sm disabled:opacity-50">
                          {actionLoading === `${o.id}-qc` ? '...' : 'QC'}
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {variance.length > 0 && (
        <div className="mt-6">
          <h4 className="font-semibold text-[#C9A96E] mb-3">Variance Analysis (Planned vs Actual)</h4>
          <table className="w-full">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-2 text-left text-sm">Order No</th>
                <th className="px-4 py-2 text-right text-sm">Planned</th>
                <th className="px-4 py-2 text-right text-sm">Actual</th>
                <th className="px-4 py-2 text-right text-sm">Variance</th>
                <th className="px-4 py-2 text-right text-sm">Variance %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {variance.map(v => (
                <tr key={v.id}>
                  <td className="px-4 py-2 font-mono text-sm">{v.order_no}</td>
                  <td className="px-4 py-2 text-right">{v.planned_qty}</td>
                  <td className="px-4 py-2 text-right">{v.actual_qty}</td>
                  <td className={`px-4 py-2 text-right font-semibold ${v.variance < 0 ? 'text-red-600' : v.variance > 0 ? 'text-green-600' : ''}`}>
                    {v.variance > 0 ? '+' : ''}{v.variance}
                  </td>
                  <td className={`px-4 py-2 text-right text-sm ${v.variance_pct < 0 ? 'text-red-600' : ''}`}>
                    {v.variance_pct.toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── 3. BANK RECON ──────────────────────────────────────────────────
function BankReconSection() {
  const [recons, setRecons] = useState<Reconciliation[]>([]);
  const [summary, setSummary] = useState<BankReconSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ bank_account_id: '', period: '' });

  const load = () => {
    setLoading(true);
    Promise.all([fetchJSON('/bank-recon/reconciliation/summary'), fetchJSON('/bank-recon/reconciliation/summary')])
      .then(([res, sum]) => {
        setRecons(Array.isArray(res) ? res : res.items || res.data || []);
        setSummary(sum);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const handleCreate = async () => {
    try {
      await fetchJSON('/bank-recon/reconciliation/create', { method: 'POST', body: JSON.stringify(form) });
      setShowForm(false);
      setForm({ bank_account_id: '', period: '' });
      load();
    } catch (err: any) { alert('Error: ' + err.message); }
  };

  const handleClose = async (id: string) => {
    try {
      await fetchJSON(`/bank-recon/reconciliation/${id}/close`, { method: 'POST' });
      load();
    } catch (err: any) { alert('Error: ' + err.message); }
  };

  if (loading) return <Spinner />;
  if (error) return <ErrorMsg msg={error} />;

  return (
    <div className="space-y-4">
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
            <p className="text-xs text-gray-500">Bank Balance</p>
            <p className="text-xl font-bold">{formatCurrency(summary.bank_balance)}</p>
          </div>
          <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
            <p className="text-xs text-gray-500">Book Balance</p>
            <p className="text-xl font-bold">{formatCurrency(summary.book_balance)}</p>
          </div>
          <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
            <p className="text-xs text-gray-500">Difference</p>
            <p className={`text-xl font-bold ${summary.difference !== 0 ? 'text-red-600' : 'text-green-600'}`}>
              {formatCurrency(summary.difference)}
            </p>
          </div>
          <div className="bg-green-50 rounded-lg p-4">
            <p className="text-xs text-gray-500">Matched</p>
            <p className="text-xl font-bold text-green-600">{summary.matched_count}</p>
          </div>
          <div className="bg-red-50 rounded-lg p-4">
            <p className="text-xs text-gray-500">Unmatched</p>
            <p className="text-xl font-bold text-red-600">{summary.unmatched_count}</p>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Reconciliations</h3>
        <button onClick={() => setShowForm(!showForm)} className="bg-[#C9A96E] text-white px-4 py-2 rounded-lg hover:bg-[#b8985d] text-sm">
          + New Reconciliation
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-50 p-4 rounded-lg border space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Bank Account ID" value={form.bank_account_id} onChange={e => setForm({ ...form, bank_account_id: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Period (e.g. 2026-05)" value={form.period} onChange={e => setForm({ ...form, period: e.target.value })} className="border rounded px-3 py-2 text-sm" />
          </div>
          <button onClick={handleCreate} className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700">Submit</button>
        </div>
      )}

      {!recons.length ? <EmptyState /> : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Recon No</th>
                <th className="px-4 py-3 text-left text-sm">Bank Account</th>
                <th className="px-4 py-3 text-left text-sm">Period</th>
                <th className="px-4 py-3 text-right text-sm">Bank Balance</th>
                <th className="px-4 py-3 text-right text-sm">Book Balance</th>
                <th className="px-4 py-3 text-right text-sm">Difference</th>
                <th className="px-4 py-3 text-left text-sm">Status</th>
                <th className="px-4 py-3 text-left text-sm">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {recons.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-sm">{r.recon_no}</td>
                  <td className="px-4 py-3">{r.bank_account}</td>
                  <td className="px-4 py-3 text-sm">{r.period}</td>
                  <td className="px-4 py-3 text-right">{formatCurrency(r.bank_balance)}</td>
                  <td className="px-4 py-3 text-right">{formatCurrency(r.book_balance)}</td>
                  <td className={`px-4 py-3 text-right font-semibold ${r.difference !== 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {formatCurrency(r.difference)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${statusBadge(r.status)}`}>{r.status}</span>
                  </td>
                  <td className="px-4 py-3">
                    {r.status === 'draft' && (
                      <button onClick={() => handleClose(r.id)} className="text-green-600 hover:underline text-sm">Close</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── 4. COST CENTER ─────────────────────────────────────────────────
function CostCenterSection() {
  const [centers, setCenters] = useState<CostCenter[]>([]);
  const [summary, setSummary] = useState<CostCenterSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ code: '', name: '', branch_id: '' });

  const load = () => {
    setLoading(true);
    Promise.all([fetchJSON('/cost-center/cost_center'), fetchJSON('/cost-center/cost-center/summary')])
      .then(([res, sum]) => {
        setCenters(Array.isArray(res) ? res : res.items || res.data || []);
        setSummary(sum);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const handleSubmit = async () => {
    try {
      if (editId) {
        await fetchJSON(`/cost-center/cost_center/${editId}`, { method: 'PUT', body: JSON.stringify(form) });
      } else {
        await fetchJSON('/cost-center/cost_center', { method: 'POST', body: JSON.stringify(form) });
      }
      setShowForm(false);
      setEditId(null);
      setForm({ code: '', name: '', branch_id: '' });
      load();
    } catch (err: any) { alert('Error: ' + err.message); }
  };

  const handleEdit = (c: CostCenter) => {
    setForm({ code: c.code, name: c.name, branch_id: c.branch_id || '' });
    setEditId(c.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this cost center?')) return;
    try {
      await fetchJSON(`/cost-center/cost_center/${id}`, { method: 'DELETE' });
      load();
    } catch (err: any) { alert('Error: ' + err.message); }
  };

  if (loading) return <Spinner />;
  if (error) return <ErrorMsg msg={error} />;

  const summaryMap = new Map<string, { debit: number; credit: number }>();
  summary?.items?.forEach(s => summaryMap.set(s.cost_center_id, { debit: s.total_debit, credit: s.total_credit }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Cost Centers</h3>
        <button onClick={() => { setShowForm(!showForm); setEditId(null); setForm({ code: '', name: '', branch_id: '' }); }}
          className="bg-[#C9A96E] text-white px-4 py-2 rounded-lg hover:bg-[#b8985d] text-sm">
          + New Cost Center
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-50 p-4 rounded-lg border space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <input placeholder="Code" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Branch ID" value={form.branch_id} onChange={e => setForm({ ...form, branch_id: e.target.value })} className="border rounded px-3 py-2 text-sm" />
          </div>
          <div className="space-x-2">
            <button onClick={handleSubmit} className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700">
              {editId ? 'Update' : 'Create'}
            </button>
            {editId && (
              <button onClick={() => { setShowForm(false); setEditId(null); }} className="bg-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-400">Cancel</button>
            )}
          </div>
        </div>
      )}

      {!centers.length ? <EmptyState /> : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Code</th>
                <th className="px-4 py-3 text-left text-sm">Name</th>
                <th className="px-4 py-3 text-left text-sm">Branch</th>
                <th className="px-4 py-3 text-right text-sm">Total Debit</th>
                <th className="px-4 py-3 text-right text-sm">Total Credit</th>
                <th className="px-4 py-3 text-left text-sm">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {centers.map((c) => {
                const s = summaryMap.get(c.id);
                return (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-sm">{c.code}</td>
                    <td className="px-4 py-3 font-medium">{c.name}</td>
                    <td className="px-4 py-3 text-sm">{c.branch_name || '-'}</td>
                    <td className="px-4 py-3 text-right">{s ? formatCurrency(s.debit) : '-'}</td>
                    <td className="px-4 py-3 text-right">{s ? formatCurrency(s.credit) : '-'}</td>
                    <td className="px-4 py-3 space-x-2">
                      <button onClick={() => handleEdit(c)} className="text-blue-600 hover:underline text-sm">Edit</button>
                      <button onClick={() => handleDelete(c.id)} className="text-red-600 hover:underline text-sm">Delete</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── 5. SCHEDULE ────────────────────────────────────────────────────
function ScheduleSection() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date(); d.setDate(1); return d.toISOString().split('T')[0];
  });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().split('T')[0]);
  const [therapistFilter, setTherapistFilter] = useState('');
  const [branchFilter, setBranchFilter] = useState('');
  const [availability, setAvailability] = useState<any[]>([]);
  const [showAvailability, setShowAvailability] = useState(false);
  const [bulkDate, setBulkDate] = useState('');
  const [bulkTherapist, setBulkTherapist] = useState('');

  const load = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    if (therapistFilter) params.set('therapist_id', therapistFilter);
    if (branchFilter) params.set('branch_id', branchFilter);
    fetchJSON(`/schedule?${params.toString()}`)
      .then((res) => setSchedules(Array.isArray(res) ? res : res.items || res.data || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };
  useEffect(load, [dateFrom, dateTo, therapistFilter, branchFilter]);

  const checkAvailability = async () => {
    try {
      const params = new URLSearchParams();
      if (dateFrom) params.set('date', dateFrom);
      if (therapistFilter) params.set('therapist_id', therapistFilter);
      const res = await fetchJSON(`/schedule/availability?${params.toString()}`);
      setAvailability(Array.isArray(res) ? res : res.items || res.data || []);
      setShowAvailability(true);
    } catch (err: any) { alert('Error: ' + err.message); }
  };

  const handleBulkCreate = async () => {
    if (!bulkDate || !bulkTherapist) { alert('Date and therapist are required'); return; }
    try {
      await fetchJSON('/schedule/bulk', {
        method: 'POST',
        body: JSON.stringify({ date: bulkDate, therapist_id: bulkTherapist }),
      });
      setBulkDate(''); setBulkTherapist('');
      load();
    } catch (err: any) { alert('Error: ' + err.message); }
  };

  if (loading) return <Spinner />;
  if (error) return <ErrorMsg msg={error} />;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3 bg-gray-50 p-4 rounded-lg">
        <div>
          <label className="text-xs text-gray-500 block mb-1">From</label>
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">To</label>
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Therapist ID</label>
          <input placeholder="Filter by therapist" value={therapistFilter} onChange={e => setTherapistFilter(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Branch ID</label>
          <input placeholder="Filter by branch" value={branchFilter} onChange={e => setBranchFilter(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        </div>
        <button onClick={checkAvailability} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          Check Availability
        </button>
      </div>

      {/* Bulk Create */}
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Bulk Date</label>
          <input type="date" value={bulkDate} onChange={e => setBulkDate(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Therapist ID</label>
          <input placeholder="Therapist ID" value={bulkTherapist} onChange={e => setBulkTherapist(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        </div>
        <button onClick={handleBulkCreate} className="bg-[#C9A96E] text-white px-4 py-2 rounded text-sm hover:bg-[#b8985d]">
          Bulk Create
        </button>
      </div>

      {/* Availability Results */}
      {showAvailability && availability.length > 0 && (
        <div className="bg-blue-50 p-4 rounded-lg">
          <h4 className="font-semibold text-blue-700 mb-2">Availability</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {availability.map((a: any, i: number) => (
              <div key={i} className={`p-3 rounded-lg border ${a.available ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                <p className="font-medium text-sm">{a.therapist_name || a.therapist_id}</p>
                <p className={`text-xs ${a.available ? 'text-green-600' : 'text-red-600'}`}>
                  {a.available ? 'Available' : 'Unavailable'}
                </p>
                {a.time_slot && <p className="text-xs text-gray-500">{a.time_slot}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {!schedules.length ? <EmptyState msg="No schedules found for this period" /> : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Date</th>
                <th className="px-4 py-3 text-left text-sm">Therapist</th>
                <th className="px-4 py-3 text-left text-sm">Start</th>
                <th className="px-4 py-3 text-left text-sm">End</th>
                <th className="px-4 py-3 text-left text-sm">Branch</th>
                <th className="px-4 py-3 text-left text-sm">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {schedules.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm">{s.date}</td>
                  <td className="px-4 py-3 font-medium">{s.therapist_name || s.therapist_id}</td>
                  <td className="px-4 py-3 text-sm">{s.start_time}</td>
                  <td className="px-4 py-3 text-sm">{s.end_time}</td>
                  <td className="px-4 py-3 text-sm">{s.branch_name || '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${statusBadge(s.status)}`}>{s.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── 6. CERTIFICATION ───────────────────────────────────────────────
function CertificationSection() {
  const [certs, setCerts] = useState<Certification[]>([]);
  const [expiring, setExpiring] = useState<Certification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ therapist_id: '', cert_name: '', issuer: '', issue_date: '', expiry_date: '' });

  const load = () => {
    setLoading(true);
    Promise.all([fetchJSON('/certification'), fetchJSON('/certification/expiring')])
      .then(([res, exp]) => {
        setCerts(Array.isArray(res) ? res : res.items || res.data || []);
        setExpiring(Array.isArray(exp) ? exp : exp.items || exp.data || []);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const handleCreate = async () => {
    try {
      await fetchJSON('/certification', { method: 'POST', body: JSON.stringify(form) });
      setShowForm(false);
      setForm({ therapist_id: '', cert_name: '', issuer: '', issue_date: '', expiry_date: '' });
      load();
    } catch (err: any) { alert('Error: ' + err.message); }
  };

  const isExpiringSoon = (expiryDate: string) => {
    const diff = new Date(expiryDate).getTime() - Date.now();
    return diff > 0 && diff <= 30 * 24 * 60 * 60 * 1000;
  };

  if (loading) return <Spinner />;
  if (error) return <ErrorMsg msg={error} />;

  return (
    <div className="space-y-4">
      {expiring.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h4 className="font-semibold text-yellow-700 mb-2">⚠️ Expiring Within 30 Days ({expiring.length})</h4>
          <div className="space-y-2">
            {expiring.map((e) => (
              <div key={e.id} className="flex items-center gap-3 text-sm">
                <span className="px-2 py-0.5 bg-yellow-200 text-yellow-800 rounded text-xs font-medium">expiring</span>
                <span className="font-medium">{e.therapist_name || e.therapist_id}</span>
                <span className="text-gray-600">— {e.cert_name}</span>
                <span className="text-gray-500">expires {e.expiry_date}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Certifications</h3>
        <button onClick={() => setShowForm(!showForm)} className="bg-[#C9A96E] text-white px-4 py-2 rounded-lg hover:bg-[#b8985d] text-sm">
          + Add Certification
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-50 p-4 rounded-lg border space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <input placeholder="Therapist ID" value={form.therapist_id} onChange={e => setForm({ ...form, therapist_id: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Cert Name" value={form.cert_name} onChange={e => setForm({ ...form, cert_name: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Issuer" value={form.issuer} onChange={e => setForm({ ...form, issuer: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <div>
              <label className="text-xs text-gray-500">Issue Date</label>
              <input type="date" value={form.issue_date} onChange={e => setForm({ ...form, issue_date: e.target.value })} className="border rounded px-3 py-2 text-sm w-full" />
            </div>
            <div>
              <label className="text-xs text-gray-500">Expiry Date</label>
              <input type="date" value={form.expiry_date} onChange={e => setForm({ ...form, expiry_date: e.target.value })} className="border rounded px-3 py-2 text-sm w-full" />
            </div>
          </div>
          <button onClick={handleCreate} className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700">Add</button>
        </div>
      )}

      {!certs.length ? <EmptyState /> : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Therapist</th>
                <th className="px-4 py-3 text-left text-sm">Cert Name</th>
                <th className="px-4 py-3 text-left text-sm">Issuer</th>
                <th className="px-4 py-3 text-left text-sm">Issue Date</th>
                <th className="px-4 py-3 text-left text-sm">Expiry Date</th>
                <th className="px-4 py-3 text-left text-sm">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {certs.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{c.therapist_name || c.therapist_id}</td>
                  <td className="px-4 py-3">{c.cert_name}</td>
                  <td className="px-4 py-3 text-sm">{c.issuer}</td>
                  <td className="px-4 py-3 text-sm">{c.issue_date}</td>
                  <td className="px-4 py-3 text-sm">{c.expiry_date}</td>
                  <td className="px-4 py-3">
                    {isExpiringSoon(c.expiry_date) ? (
                      <span className="px-2 py-1 rounded text-xs font-medium bg-yellow-100 text-yellow-700">expiring soon</span>
                    ) : (
                      <span className={`px-2 py-1 rounded text-xs font-medium ${statusBadge(c.status)}`}>{c.status}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── 7. PRICELIST ───────────────────────────────────────────────────
function PricelistSection() {
  const [subTab, setSubTab] = useState<PricelistSubTab>('product');
  const [items, setItems] = useState<PricelistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lookupQuery, setLookupQuery] = useState('');
  const [lookupResult, setLookupResult] = useState<any>(null);
  const [lookupLoading, setLookupLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    const endpoint = subTab === 'product' ? '/pricelist/product-pricelist' : '/pricelist/treatment-pricelist';
    fetchJSON(endpoint)
      .then((res) => setItems(Array.isArray(res) ? res : res.items || res.data || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [subTab]);

  const handleLookup = async () => {
    if (!lookupQuery) return;
    setLookupLoading(true);
    try {
      const res = await fetchJSON(`/pricelist/price-lookup?q=${encodeURIComponent(lookupQuery)}`);
      setLookupResult(res);
    } catch (err: any) { alert('Error: ' + err.message); }
    finally { setLookupLoading(false); }
  };

  return (
    <div className="space-y-4">
      {/* Sub-tabs */}
      <div className="flex gap-2">
        <button onClick={() => setSubTab('product')}
          className={`px-4 py-2 rounded-lg text-sm font-medium ${subTab === 'product' ? 'bg-[#C9A96E] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
          Product Pricelist
        </button>
        <button onClick={() => setSubTab('treatment')}
          className={`px-4 py-2 rounded-lg text-sm font-medium ${subTab === 'treatment' ? 'bg-[#C9A96E] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
          Treatment Pricelist
        </button>
      </div>

      {/* Price Lookup */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <h4 className="text-sm font-semibold mb-2">Price Lookup</h4>
        <div className="flex gap-2">
          <input placeholder="Search item name or code..." value={lookupQuery} onChange={e => setLookupQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleLookup()}
            className="border rounded px-3 py-2 text-sm flex-1" />
          <button onClick={handleLookup} disabled={lookupLoading}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50">
            {lookupLoading ? '...' : 'Search'}
          </button>
        </div>
        {lookupResult && (
          <div className="mt-3 p-3 bg-white rounded border">
            <pre className="text-sm whitespace-pre-wrap">{JSON.stringify(lookupResult, null, 2)}</pre>
          </div>
        )}
      </div>

      {loading ? <Spinner /> : error ? <ErrorMsg msg={error} /> : !items.length ? <EmptyState /> : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Item Name</th>
                <th className="px-4 py-3 text-left text-sm">Branch</th>
                <th className="px-4 py-3 text-right text-sm">Price</th>
                <th className="px-4 py-3 text-left text-sm">Valid From</th>
                <th className="px-4 py-3 text-left text-sm">Valid Until</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{p.item_name || p.name}</td>
                  <td className="px-4 py-3 text-sm">{p.branch_name || '-'}</td>
                  <td className="px-4 py-3 text-right font-semibold text-[#C9A96E]">{formatCurrency(p.price)}</td>
                  <td className="px-4 py-3 text-sm">{p.valid_from}</td>
                  <td className="px-4 py-3 text-sm">{p.valid_until}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── 8. CANCEL REASON ───────────────────────────────────────────────
function CancelReasonSection() {
  const [reasons, setReasons] = useState<CancelReason[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ code: '', name: '', description: '' });

  const load = () => {
    setLoading(true);
    fetchJSON('/cancel-reason/cancel-reason')
      .then((res) => setReasons(Array.isArray(res) ? res : res.items || res.data || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const handleSubmit = async () => {
    try {
      if (editId) {
        await fetchJSON(`/cancel-reason/cancel-reason/${editId}`, { method: 'PUT', body: JSON.stringify(form) });
      } else {
        await fetchJSON('/cancel-reason/cancel-reason', { method: 'POST', body: JSON.stringify(form) });
      }
      setShowForm(false);
      setEditId(null);
      setForm({ code: '', name: '', description: '' });
      load();
    } catch (err: any) { alert('Error: ' + err.message); }
  };

  const handleEdit = (r: CancelReason) => {
    setForm({ code: r.code, name: r.name, description: r.description });
    setEditId(r.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this cancel reason?')) return;
    try {
      await fetchJSON(`/cancel-reason/cancel-reason/${id}`, { method: 'DELETE' });
      load();
    } catch (err: any) { alert('Error: ' + err.message); }
  };

  if (loading) return <Spinner />;
  if (error) return <ErrorMsg msg={error} />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Cancel Reasons</h3>
        <button onClick={() => { setShowForm(!showForm); setEditId(null); setForm({ code: '', name: '', description: '' }); }}
          className="bg-[#C9A96E] text-white px-4 py-2 rounded-lg hover:bg-[#b8985d] text-sm">
          + New Reason
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-50 p-4 rounded-lg border space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input placeholder="Code" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="border rounded px-3 py-2 text-sm" />
          </div>
          <div className="space-x-2">
            <button onClick={handleSubmit} className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700">
              {editId ? 'Update' : 'Create'}
            </button>
            {editId && (
              <button onClick={() => { setShowForm(false); setEditId(null); }} className="bg-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-400">Cancel</button>
            )}
          </div>
        </div>
      )}

      {!reasons.length ? <EmptyState /> : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Code</th>
                <th className="px-4 py-3 text-left text-sm">Name</th>
                <th className="px-4 py-3 text-left text-sm">Description</th>
                <th className="px-4 py-3 text-left text-sm">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {reasons.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-sm">{r.code}</td>
                  <td className="px-4 py-3 font-medium">{r.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{r.description}</td>
                  <td className="px-4 py-3 space-x-2">
                    <button onClick={() => handleEdit(r)} className="text-blue-600 hover:underline text-sm">Edit</button>
                    <button onClick={() => handleDelete(r.id)} className="text-red-600 hover:underline text-sm">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── 9. RECURRING JOURNAL ───────────────────────────────────────────
function RecurringJournalSection() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', frequency: 'monthly', next_run_date: new Date().toISOString().slice(0,10), auto_post: false, branch_id: '' });

  useEffect(() => {
    fetchJSON('/recurring-journal/list').then(r => setItems(r.recurring_journals || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    await fetchJSON('/recurring-journal/create', { method: 'POST', body: JSON.stringify(form) });
    setShowForm(false);
    const r = await fetchJSON('/recurring-journal/list');
    setItems(r.recurring_journals || []);
  };

  const handleRun = async (id: string) => {
    await fetchJSON(`/recurring-journal/${id}/run`, { method: 'POST' });
    const r = await fetchJSON('/recurring-journal/list');
    setItems(r.recurring_journals || []);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this recurring journal?')) return;
    await fetchJSON(`/recurring-journal/${id}`, { method: 'DELETE' });
    setItems(items.filter(i => i.id !== id));
  };

  if (loading) return <Spinner />;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">🔁 Recurring Journal</h3>
        <button onClick={() => setShowForm(!showForm)} className="bg-[#C9A96E] text-white px-4 py-2 rounded-lg text-sm">
          {showForm ? 'Cancel' : '+ New Recurring Journal'}
        </button>
      </div>
      {showForm && (
        <div className="bg-gray-50 p-4 rounded-lg mb-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          <input className="border rounded px-3 py-2" placeholder="Name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
          <select className="border rounded px-3 py-2" value={form.frequency} onChange={e => setForm({...form, frequency: e.target.value})}>
            <option value="daily">Daily</option><option value="weekly">Weekly</option><option value="biweekly">Biweekly</option>
            <option value="monthly">Monthly</option><option value="quarterly">Quarterly</option><option value="yearly">Yearly</option>
          </select>
          <input className="border rounded px-3 py-2" type="date" value={form.next_run_date} onChange={e => setForm({...form, next_run_date: e.target.value})} />
          <button onClick={handleCreate} className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm">Create</button>
        </div>
      )}
      {items.length === 0 ? <EmptyState msg="No recurring journals" /> : (
        <div className="space-y-2">
          {items.map((item: any) => (
            <div key={item.id} className="flex items-center justify-between bg-gray-50 p-4 rounded-lg">
              <div>
                <p className="font-medium">{item.name}</p>
                <p className="text-sm text-gray-500">Frequency: {item.frequency} | Next: {item.next_run_date} | Runs: {item.total_runs || 0}</p>
              </div>
              <div className="flex gap-2">
                <button onClick={() => handleRun(item.id)} className="bg-blue-600 text-white px-3 py-1 rounded text-sm">▶ Run Now</button>
                <button onClick={() => handleDelete(item.id)} className="bg-red-600 text-white px-3 py-1 rounded text-sm">🗑</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── 10. CASH FLOW ──────────────────────────────────────────────────
function CashFlowSection() {
  const [report, setReport] = useState<any>(null);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState(new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0,10));
  const [dateTo, setDateTo] = useState(new Date().toISOString().slice(0,10));
  const [subTab, setSubTab] = useState<'report' | 'categories'>('report');

  const loadData = () => {
    setLoading(true);
    Promise.all([
      fetchJSON(`/cash-flow/report?date_from=${dateFrom}&date_to=${dateTo}`),
      fetchJSON('/cash-flow/categories'),
    ]).then(([r, c]) => { setReport(r); setCategories(c.categories || []); }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const types = [
    { key: 'operating', label: '🔵 Operating Activities', color: 'blue' },
    { key: 'investing', label: '🟢 Investing Activities', color: 'green' },
    { key: 'financing', label: '🟡 Financing Activities', color: 'yellow' },
  ];

  if (loading) return <Spinner />;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">💸 Cash Flow Statement</h3>
        <div className="flex gap-2">
          {(['report','categories'] as const).map(t => (
            <button key={t} onClick={() => setSubTab(t)} className={`px-3 py-1 rounded text-sm ${subTab === t ? 'bg-[#C9A96E] text-white' : 'bg-gray-100'}`}>
              {t === 'report' ? '📊 Report' : '📋 Categories'}
            </button>
          ))}
        </div>
      </div>
      {subTab === 'report' && (
        <>
          <div className="flex gap-3 mb-4">
            <input type="date" className="border rounded px-3 py-2" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
            <input type="date" className="border rounded px-3 py-2" value={dateTo} onChange={e => setDateTo(e.target.value)} />
            <button onClick={loadData} className="bg-[#C9A96E] text-white px-4 py-2 rounded-lg text-sm">Filter</button>
          </div>
          {report && (
            <div className="space-y-4">
              {types.map(t => (
                <div key={t.key} className="border rounded-lg p-4">
                  <h4 className="font-semibold mb-2">{t.label}</h4>
                  {(report[t.key] || []).length === 0 ? <p className="text-gray-400 text-sm">No data</p> : (
                    <table className="w-full text-sm">
                      <thead><tr className="border-b"><th className="text-left py-1">Category</th><th className="text-right">Debit</th><th className="text-right">Credit</th><th className="text-right">Net</th></tr></thead>
                      <tbody>{(report[t.key] || []).map((r: any, i: number) => (
                        <tr key={i} className="border-b"><td className="py-1">{r.name || r.code || '-'}</td><td className="text-right">{formatCurrency(r.total_debit)}</td><td className="text-right">{formatCurrency(r.total_credit)}</td><td className="text-right font-medium">{formatCurrency(r.net_amount)}</td></tr>
                      ))}</tbody>
                    </table>
                  )}
                  <div className="text-right font-bold mt-2">Net: {formatCurrency(report[`net_${t.key}`] || 0)}</div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
      {subTab === 'categories' && (
        <div className="space-y-2">
          {categories.map((cat: any) => (
            <div key={cat.id} className="flex justify-between bg-gray-50 p-3 rounded">
              <div><span className="font-mono text-sm mr-2">{cat.code}</span><span className="font-medium">{cat.name}</span></div>
              <span className="text-sm text-gray-500">{cat.type}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── 11. WHATSAPP BOOKING ───────────────────────────────────────────
function WhatsAppSection() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any>(null);
  const [reply, setReply] = useState('');

  useEffect(() => {
    Promise.all([fetchJSON('/whatsapp/sessions'), fetchJSON('/whatsapp/stats')])
      .then(([s, st]) => { setSessions(s.sessions || []); setStats(st); })
      .catch(() => {}).finally(() => setLoading(false));
  }, []);

  const loadSession = async (id: string) => {
    const s = await fetchJSON(`/whatsapp/sessions/${id}`);
    setSelected(s);
  };

  const sendReply = async () => {
    if (!reply.trim() || !selected) return;
    await fetchJSON(`/whatsapp/sessions/${selected.id}/reply`, { method: 'POST', body: JSON.stringify({ message: reply }) });
    setReply('');
    loadSession(selected.id);
  };

  if (loading) return <Spinner />;

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">💬 WhatsApp Booking</h3>
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          {[
            { label: 'Total Sessions', val: stats.total_sessions },
            { label: 'Active', val: stats.active_sessions },
            { label: 'Today Messages', val: stats.today_messages },
            { label: 'Pending Bookings', val: stats.pending_bookings },
          ].map(s => (
            <div key={s.label} className="bg-gray-50 p-3 rounded-lg text-center">
              <p className="text-2xl font-bold text-[#C9A96E]">{s.val}</p>
              <p className="text-xs text-gray-500">{s.label}</p>
            </div>
          ))}
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="font-medium mb-2">Sessions</h4>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {sessions.length === 0 ? <EmptyState msg="No WhatsApp sessions" /> : sessions.map((s: any) => (
              <div key={s.id} onClick={() => loadSession(s.id)} className={`p-3 rounded-lg cursor-pointer border ${selected?.id === s.id ? 'border-[#C9A96E] bg-amber-50' : 'bg-gray-50 hover:bg-gray-100'}`}>
                <div className="flex justify-between">
                  <span className="font-medium">{s.customer_name || s.phone}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${s.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>{s.status}</span>
                </div>
                <p className="text-sm text-gray-500 truncate">{s.last_message || 'No messages'}</p>
              </div>
            ))}
          </div>
        </div>
        <div>
          {selected ? (
            <div>
              <h4 className="font-medium mb-2">Chat: {selected.customer_name || selected.phone}</h4>
              <div className="border rounded-lg p-3 h-64 overflow-y-auto bg-gray-50 mb-2 space-y-2">
                {(selected.messages || []).map((m: any) => (
                  <div key={m.id} className={`flex ${m.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-xs px-3 py-1.5 rounded-lg text-sm ${m.direction === 'outbound' ? 'bg-[#C9A96E] text-white' : 'bg-white border'}`}>{m.content}</div>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <input className="flex-1 border rounded px-3 py-2" placeholder="Type reply..." value={reply} onChange={e => setReply(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendReply()} />
                <button onClick={sendReply} className="bg-[#C9A96E] text-white px-4 py-2 rounded-lg">Send</button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">Select a session to view chat</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── 12. EXECUTIVE DASHBOARD ────────────────────────────────────────
function ExecutiveSection() {
  const [summary, setSummary] = useState<any>(null);
  const [branches, setBranches] = useState<any[]>([]);
  const [topTreatments, setTopTreatments] = useState<any[]>([]);
  const [topTherapists, setTopTherapists] = useState<any[]>([]);
  const [kpis, setKpis] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState(new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0,10));
  const [dateTo, setDateTo] = useState(new Date().toISOString().slice(0,10));

  const loadData = () => {
    setLoading(true);
    const params = `date_from=${dateFrom}&date_to=${dateTo}`;
    Promise.all([
      fetchJSON(`/executive/summary?${params}`),
      fetchJSON(`/executive/branch-comparison?${params}`),
      fetchJSON(`/executive/top-treatments?${params}&limit=5`),
      fetchJSON(`/executive/top-therapists?${params}&limit=5`),
      fetchJSON('/executive/kpi-targets'),
    ]).then(([s, b, tt, tp, k]) => {
      setSummary(s); setBranches(b.branches || []);
      setTopTreatments(tt.treatments || []); setTopTherapists(tp.therapists || []);
      setKpis(k.targets || []);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  if (loading) return <Spinner />;

  const kpiCards = summary ? [
    { label: 'Revenue', value: formatCurrency(summary.revenue), icon: '💰' },
    { label: 'Profit', value: formatCurrency(summary.profit), icon: '📈' },
    { label: 'Transactions', value: summary.transactions, icon: '🧾' },
    { label: 'Avg Ticket', value: formatCurrency(summary.avg_ticket_size), icon: '🎟️' },
    { label: 'Treatments', value: summary.total_treatments, icon: '💆' },
    { label: 'New Customers', value: summary.new_customers, icon: '👥' },
  ] : [];

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">👔 Executive Dashboard</h3>
        <div className="flex gap-2">
          <input type="date" className="border rounded px-3 py-2 text-sm" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          <input type="date" className="border rounded px-3 py-2 text-sm" value={dateTo} onChange={e => setDateTo(e.target.value)} />
          <button onClick={loadData} className="bg-[#C9A96E] text-white px-4 py-2 rounded-lg text-sm">Filter</button>
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {kpiCards.map(c => (
          <div key={c.label} className="bg-gradient-to-br from-amber-50 to-orange-50 p-4 rounded-xl border text-center">
            <p className="text-2xl mb-1">{c.icon}</p>
            <p className="text-lg font-bold">{c.value}</p>
            <p className="text-xs text-gray-500">{c.label}</p>
          </div>
        ))}
      </div>
      {kpis.length > 0 && (
        <div className="mb-6">
          <h4 className="font-medium mb-3">🎯 KPI Targets</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {kpis.map((kpi: any) => {
              const actual = summary?.[kpi.metric_type] ?? 0;
              const pct = kpi.target_value > 0 ? Math.min(100, Math.round((actual / kpi.target_value) * 100)) : 0;
              return (
                <div key={kpi.id} className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm font-medium">{kpi.name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 bg-gray-200 rounded-full h-2"><div className="bg-[#C9A96E] h-2 rounded-full" style={{width: `${pct}%`}} /></div>
                    <span className="text-xs font-bold">{pct}%</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Target: {kpi.target_value} | Actual: {actual}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <h4 className="font-medium mb-3">🏥 Branch Performance</h4>
          <div className="space-y-2">
            {branches.map((b: any) => (
              <div key={b.id} className="flex justify-between bg-gray-50 p-3 rounded">
                <div><p className="font-medium">{b.branch_name}</p><p className="text-xs text-gray-500">{b.transactions} transactions</p></div>
                <div className="text-right"><p className="font-bold">{formatCurrency(b.revenue)}</p><p className="text-xs text-gray-500">Avg: {formatCurrency(b.avg_ticket)}</p></div>
              </div>
            ))}
            {branches.length === 0 && <EmptyState msg="No branch data" />}
          </div>
        </div>
        <div>
          <h4 className="font-medium mb-3">⭐ Top Treatments</h4>
          <div className="space-y-2">
            {topTreatments.map((t: any, i: number) => (
              <div key={i} className="flex justify-between bg-gray-50 p-3 rounded">
                <div><p className="font-medium">{t.treatment_name}</p><p className="text-xs text-gray-500">{t.booking_count} bookings</p></div>
                <span className="font-bold">{formatCurrency(t.total_revenue)}</span>
              </div>
            ))}
            {topTreatments.length === 0 && <EmptyState msg="No treatment data" />}
          </div>
        </div>
      </div>
      <div>
        <h4 className="font-medium mb-3">👩‍⚕️ Top Therapists</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b bg-gray-50"><th className="text-left p-2">#</th><th className="text-left">Name</th><th className="text-right">Treatments</th><th className="text-right">Revenue</th><th className="text-right">Rating</th></tr></thead>
            <tbody>{topTherapists.map((t: any, i: number) => (
              <tr key={i} className="border-b"><td className="p-2">{i+1}</td><td>{t.therapist_name}</td><td className="text-right">{t.treatments_done}</td><td className="text-right">{formatCurrency(t.total_revenue)}</td><td className="text-right">⭐ {Number(t.avg_rating || 0).toFixed(1)}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── 13. POS SETTLEMENT ────────────────────────────────────────────
function SettlementSection() {
  type SubTab = 'closing' | 'shifts';
  const [subTab, setSubTab] = useState<SubTab>('closing');
  const [closings, setClosings] = useState<any[]>([]);
  const [shifts, setShifts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [branchFilter, setBranchFilter] = useState('');

  const load = () => {
    setLoading(true);
    const branchParam = branchFilter ? `?branch_id=${branchFilter}` : '';
    const p1 = fetchJSON(`/daily-closing/history${branchParam}`).catch(() => ({ items: [] }));
    const p2 = fetchJSON(`/pos/shift/history${branchParam}`).catch(() => ({ items: [] }));
    Promise.all([p1, p2]).then(([c, s]) => {
      setClosings(Array.isArray(c) ? c : c.items || []);
      setShifts(Array.isArray(s) ? s : s.items || []);
    }).finally(() => setLoading(false));
  };
  useEffect(load, [branchFilter]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex gap-1">
          {(['closing', 'shifts'] as SubTab[]).map((t) => (
            <button key={t} onClick={() => setSubTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${subTab === t ? 'bg-[#C9A96E] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {t === 'closing' ? '📋 Closing Harian' : '🔄 Shift History'}
            </button>
          ))}
        </div>
      </div>

      {loading ? <Spinner /> : subTab === 'closing' ? (
        <div className="bg-white rounded-xl border overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs text-gray-500 uppercase">
                <th className="px-4 py-3">Tanggal</th>
                <th className="px-4 py-3">Branch</th>
                <th className="px-4 py-3 text-right">Transaksi</th>
                <th className="px-4 py-3 text-right">Operasional</th>
                <th className="px-4 py-3 text-right">Uang Hitung</th>
                <th className="px-4 py-3 text-right">Variance</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {closings.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-8 text-gray-400">Belum ada data closing</td></tr>
              ) : closings.map((c: any, i: number) => (
                <tr key={i} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium">{c.business_date || c.date || '-'}</td>
                  <td className="px-4 py-3 text-sm">{c.branch_code || '-'}</td>
                  <td className="px-4 py-3 text-sm text-right">{c.transaction_count ?? '-'}</td>
                  <td className="px-4 py-3 text-sm text-right">{formatCurrency(c.operational_sales || c.total_nominal || 0)}</td>
                  <td className="px-4 py-3 text-sm text-right">{formatCurrency(c.counted_cash || 0)}</td>
                  <td className="px-4 py-3 text-sm text-right">
                    <span className={c.variance_amount > 0 ? 'text-green-600' : c.variance_amount < 0 ? 'text-red-600' : 'text-gray-500'}>
                      {c.variance_amount >= 0 ? '+' : ''}{formatCurrency(c.variance_amount || 0)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${c.status === 'submitted' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                      {c.status || 'draft'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs text-gray-500 uppercase">
                <th className="px-4 py-3">Shift Code</th>
                <th className="px-4 py-3">Kasir</th>
                <th className="px-4 py-3">Branch</th>
                <th className="px-4 py-3 text-right">Kas Awal</th>
                <th className="px-4 py-3 text-right">Penjualan</th>
                <th className="px-4 py-3 text-right">Kas Akhir</th>
                <th className="px-4 py-3 text-right">Variance</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Waktu</th>
              </tr>
            </thead>
            <tbody>
              {shifts.length === 0 ? (
                <tr><td colSpan={9} className="text-center py-8 text-gray-400">Belum ada data shift</td></tr>
              ) : shifts.map((s: any, i: number) => (
                <tr key={i} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-mono font-medium">{s.shift_code || '-'}</td>
                  <td className="px-4 py-3 text-sm">{s.staff_name || s.staff_id || '-'}</td>
                  <td className="px-4 py-3 text-sm">{s.branch_code || '-'}</td>
                  <td className="px-4 py-3 text-sm text-right">{formatCurrency(s.opening_cash || 0)}</td>
                  <td className="px-4 py-3 text-sm text-right">{formatCurrency(s.total_sales || 0)}</td>
                  <td className="px-4 py-3 text-sm text-right">{s.closing_cash != null ? formatCurrency(s.closing_cash) : '-'}</td>
                  <td className="px-4 py-3 text-sm text-right">
                    {s.variance != null ? (
                      <span className={s.variance > 0 ? 'text-green-600' : s.variance < 0 ? 'text-red-600' : 'text-gray-500'}>
                        {s.variance >= 0 ? '+' : ''}{formatCurrency(s.variance)}
                      </span>
                    ) : '-'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${s.status === 'open' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>
                      {s.status || '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {s.opened_at ? new Date(s.opened_at).toLocaleString('id-ID', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── MAIN PAGE ──────────────────────────────────────────────────────
export default function OperationsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('production');

  const renderSection = () => {
    switch (activeTab) {
      case 'production': return <ProductionSection />;
      case 'bankrecon': return <BankReconSection />;
      case 'costcenter': return <CostCenterSection />;
      case 'schedule': return <ScheduleSection />;
      case 'certification': return <CertificationSection />;
      case 'pricelist': return <PricelistSection />;
      case 'cancelreason': return <CancelReasonSection />;
      case 'recurring': return <RecurringJournalSection />;
      case 'cashflow': return <CashFlowSection />;
      case 'whatsapp': return <WhatsAppSection />;
      case 'executive': return <ExecutiveSection />;
      case 'settlement': return <SettlementSection />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-800">Operations</h1>
          <p className="text-sm text-gray-500 mt-1">BPMN v3 Operations Management</p>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex overflow-x-auto gap-1 py-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  activeTab === tab.key
                    ? 'bg-[#C9A96E] text-white shadow-sm'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-6">
            {renderSection()}
          </div>
        </div>
      </div>
    </div>
  );
}
