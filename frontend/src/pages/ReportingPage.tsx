import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

type Tab = 'sales' | 'treatment' | 'payment' | 'therapist' | 'commission' | 'inventory' | 'finance' | 'shift';

const tabs: { key: Tab; label: string; icon: string }[] = [
  { key: 'sales', label: 'Daily Sales', icon: '📊' },
  { key: 'treatment', label: 'By Treatment', icon: '💆' },
  { key: 'payment', label: 'Payment Method', icon: '💳' },
  { key: 'therapist', label: 'Therapist', icon: '👩‍⚕️' },
  { key: 'commission', label: 'Commission', icon: '💵' },
  { key: 'inventory', label: 'Inventory', icon: '📦' },
  { key: 'finance', label: 'Finance', icon: '💰' },
  { key: 'shift', label: 'Shift', icon: '🔄' },
];

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(amount);

const fmtDate = (d: Date) => d.toISOString().split('T')[0];

// Date range presets
const datePresets = [
  { label: 'Hari Ini', getRange: () => { const t = new Date(); return { from: fmtDate(t), to: fmtDate(t) }; } },
  { label: 'Kemarin', getRange: () => { const t = new Date(); t.setDate(t.getDate() - 1); return { from: fmtDate(t), to: fmtDate(t) }; } },
  { label: '7 Hari', getRange: () => { const t = new Date(); const f = new Date(t); f.setDate(f.getDate() - 7); return { from: fmtDate(f), to: fmtDate(t) }; } },
  { label: '30 Hari', getRange: () => { const t = new Date(); const f = new Date(t); f.setDate(f.getDate() - 30); return { from: fmtDate(f), to: fmtDate(t) }; } },
  { label: 'Bulan Ini', getRange: () => { const t = new Date(); const f = new Date(t.getFullYear(), t.getMonth(), 1); return { from: fmtDate(f), to: fmtDate(t) }; } },
  { label: 'Bulan Lalu', getRange: () => { const t = new Date(); const f = new Date(t.getFullYear(), t.getMonth() - 1, 1); const e = new Date(t.getFullYear(), t.getMonth(), 0); return { from: fmtDate(f), to: fmtDate(e) }; } },
];

export default function ReportingPage() {
  const [activeTab, setActiveTab] = useState<Tab>('sales');
  const [data, setData] = useState<Record<Tab, any>>({
    sales: [], treatment: [], payment: [], therapist: [], commission: { summary: [], detail: [] }, inventory: [], finance: null, shift: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Date range filter
  const today = new Date();
  const defaultFrom = new Date(today);
  defaultFrom.setDate(defaultFrom.getDate() - 30);
  const [dateFrom, setDateFrom] = useState(fmtDate(defaultFrom));
  const [dateTo, setDateTo] = useState(fmtDate(today));
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [branchId, setBranchId] = useState<string>('');
  const [branches, setBranches] = useState<any[]>([]);

  // Load branches
  useEffect(() => {
    api.getBranches?.()?.then?.((res: any) => setBranches(res?.items || res || [])).catch?.(() => {});
  }, []);

  const buildParams = useCallback(() => {
    const p = new URLSearchParams();
    if (dateFrom) p.set('date_from', dateFrom);
    if (dateTo) p.set('date_to', dateTo);
    if (branchId) p.set('branch_id', branchId);
    return p.toString();
  }, [dateFrom, dateTo, branchId]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const params = buildParams();
    const fetchers: Record<Tab, () => Promise<any>> = {
      sales: () => api.getDailySales(params),
      treatment: () => api.getSalesByTreatment(params),
      payment: () => api.getSalesByPayment(params),
      therapist: () => api.getTherapistPerformance(params),
      commission: async () => {
        const [summary, detail] = await Promise.all([
          api.getCommissionSummary(params),
          api.getCommissionDetail(params),
        ]);
        return { summary: summary.items || [], detail: detail.items || [] };
      },
      inventory: () => api.getStockSummary(),
      finance: () => api.getFinanceSummary(),
      shift: () => api.getShiftSummary(params),
    };
    fetchers[activeTab]()
      .then((res) => setData((prev) => ({ ...prev, [activeTab]: Array.isArray(res) ? res : res.items || res.data || res })))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [activeTab, buildParams]);

  // Date preset handler
  const handlePreset = (preset: typeof datePresets[0]) => {
    const range = preset.getRange();
    setDateFrom(range.from);
    setDateTo(range.to);
    setActivePreset(preset.label);
  };

  const handleExportCSV = async () => {
    try {
      const params = buildParams();
      const blob = await api.exportCSV(activeTab, params);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${activeTab}_${dateFrom}_to_${dateTo}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert('Export failed: ' + err.message);
    }
  };

  const handleExportExcel = async () => {
    try {
      const params = buildParams();
      const blob = await api.exportExcel(activeTab, params);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${activeTab}_${dateFrom}_to_${dateTo}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert('Export failed: ' + err.message);
    }
  };

  const renderContent = () => {
    if (loading) return <div className="flex justify-center py-8"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#C9A96E]"></div></div>;
    if (error) return <div className="bg-red-50 text-red-700 p-4 rounded-lg">{error}</div>;

    switch (activeTab) {
      case 'sales': {
        const salesData = data.sales as any[];
        if (!salesData?.length) return <div className="text-gray-500 text-center py-8">No data</div>;
        return (
          <div>
            {/* Summary cards */}
            <div className="grid grid-cols-3 gap-4 p-4 mb-4">
              <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
                <p className="text-xs text-gray-500">Total Transactions</p>
                <p className="text-xl font-bold text-gray-800">
                  {salesData.reduce((s: number, r: any) => s + Number(r.transaction_count || 0), 0)}
                </p>
              </div>
              <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
                <p className="text-xs text-gray-500">Total Revenue</p>
                <p className="text-xl font-bold text-[#C9A96E]">
                  {formatCurrency(salesData.reduce((s: number, r: any) => s + Number(r.total || 0), 0))}
                </p>
              </div>
              <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
                <p className="text-xs text-gray-500">Avg / Day</p>
                <p className="text-xl font-bold text-gray-800">
                  {formatCurrency(salesData.reduce((s: number, r: any) => s + Number(r.total || 0), 0) / Math.max(salesData.length, 1))}
                </p>
              </div>
            </div>
            {/* Bar chart */}
            <div className="mb-6 px-4">
              <div className="flex items-end gap-1 h-40">
                {salesData.slice(-14).map((s: any, i: number) => {
                  const maxRev = Math.max(...salesData.map((x: any) => Number(x.total || 0)));
                  const height = maxRev > 0 ? (Number(s.total || 0) / maxRev) * 100 : 0;
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center group relative">
                      <div className="absolute -top-8 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                        {formatCurrency(Number(s.total || 0))}
                      </div>
                      <div
                        className="w-full bg-gradient-to-t from-[#C9A96E] to-[#C08081] rounded-t transition-all hover:opacity-80"
                        style={{ height: `${Math.max(height, 2)}%` }}
                      />
                      <div className="text-[10px] mt-1 text-gray-500">{new Date(s.sale_date).getDate()}</div>
                    </div>
                  );
                })}
              </div>
            </div>
            {/* Table */}
            <table className="w-full">
              <thead className="bg-[#C9A96E] text-white">
                <tr>
                  <th className="px-4 py-3 text-left text-sm">Date</th>
                  <th className="px-4 py-3 text-right text-sm">Transactions</th>
                  <th className="px-4 py-3 text-right text-sm">Subtotal</th>
                  <th className="px-4 py-3 text-right text-sm">Discount</th>
                  <th className="px-4 py-3 text-right text-sm">Tax</th>
                  <th className="px-4 py-3 text-right text-sm">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {salesData.map((s: any, i: number) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{new Date(s.sale_date).toLocaleDateString('id-ID')}</td>
                    <td className="px-4 py-3 text-right">{s.transaction_count}</td>
                    <td className="px-4 py-3 text-right">{formatCurrency(Number(s.subtotal || 0))}</td>
                    <td className="px-4 py-3 text-right text-red-600">{formatCurrency(Number(s.discount || 0))}</td>
                    <td className="px-4 py-3 text-right">{formatCurrency(Number(s.tax || 0))}</td>
                    <td className="px-4 py-3 text-right font-semibold">{formatCurrency(Number(s.total || 0))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }

      case 'treatment': {
        const treatmentData = data.treatment as any[];
        if (!treatmentData?.length) return <div className="text-gray-500 text-center py-8">No data</div>;
        const totalRevenue = treatmentData.reduce((s: number, r: any) => s + Number(r.revenue || 0), 0);
        return (
          <div>
            <div className="space-y-3 p-4 mb-6">
              {treatmentData.slice(0, 10).map((t: any, i: number) => {
                const pct = totalRevenue > 0 ? (Number(t.revenue || 0) / totalRevenue * 100) : 0;
                return (
                  <div key={i} className="flex items-center gap-3">
                    <div className="w-40 text-sm truncate" title={t.item_name}>{t.item_name}</div>
                    <div className="flex-1 bg-gray-200 rounded-full h-6 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-[#C9A96E] to-[#C08081] h-full rounded-full flex items-center justify-end pr-2"
                        style={{ width: `${Math.max(pct, 3)}%` }}
                      >
                        <span className="text-xs text-white font-bold">{pct.toFixed(1)}%</span>
                      </div>
                    </div>
                    <div className="w-28 text-right text-sm font-medium">{formatCurrency(Number(t.revenue || 0))}</div>
                  </div>
                );
              })}
            </div>
            <table className="w-full">
              <thead className="bg-[#C9A96E] text-white">
                <tr>
                  <th className="px-4 py-3 text-left text-sm">Treatment</th>
                  <th className="px-4 py-3 text-right text-sm">Count</th>
                  <th className="px-4 py-3 text-right text-sm">Revenue</th>
                  <th className="px-4 py-3 text-right text-sm">Share</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {treatmentData.map((t: any, i: number) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{t.item_name}</td>
                    <td className="px-4 py-3 text-right">{t.count}</td>
                    <td className="px-4 py-3 text-right">{formatCurrency(Number(t.revenue || 0))}</td>
                    <td className="px-4 py-3 text-right">{(totalRevenue > 0 ? Number(t.revenue || 0) / totalRevenue * 100 : 0).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }

      case 'payment': {
        const paymentData = data.payment as any[];
        if (!paymentData?.length) return <div className="text-gray-500 text-center py-8">No data</div>;
        const totalPayment = paymentData.reduce((s: number, r: any) => s + Number(r.total || 0), 0);
        const colors = ['#C9A96E', '#C08081', '#6B8E23', '#4682B4', '#9370DB', '#D2691E'];
        return (
          <div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 p-4 mb-4">
              {paymentData.map((p: any, i: number) => (
                <div key={i} className="rounded-lg p-4 border" style={{ borderColor: colors[i % colors.length] + '40', backgroundColor: colors[i % colors.length] + '10' }}>
                  <p className="text-sm text-gray-600">{p.payment_method || 'Unknown'}</p>
                  <p className="text-lg font-bold" style={{ color: colors[i % colors.length] }}>{formatCurrency(Number(p.total || 0))}</p>
                  <p className="text-xs text-gray-500">{p.count} transaksi • {(totalPayment > 0 ? Number(p.total || 0) / totalPayment * 100 : 0).toFixed(1)}%</p>
                </div>
              ))}
            </div>
            <table className="w-full">
              <thead className="bg-[#C9A96E] text-white">
                <tr>
                  <th className="px-4 py-3 text-left text-sm">Payment Method</th>
                  <th className="px-4 py-3 text-right text-sm">Transactions</th>
                  <th className="px-4 py-3 text-right text-sm">Total</th>
                  <th className="px-4 py-3 text-right text-sm">Share</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {paymentData.map((p: any, i: number) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{p.payment_method || 'Unknown'}</td>
                    <td className="px-4 py-3 text-right">{p.count}</td>
                    <td className="px-4 py-3 text-right font-semibold">{formatCurrency(Number(p.total || 0))}</td>
                    <td className="px-4 py-3 text-right">{(totalPayment > 0 ? Number(p.total || 0) / totalPayment * 100 : 0).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }

      case 'therapist': {
        const therapistData = data.therapist as any[];
        if (!therapistData?.length) return <div className="text-gray-500 text-center py-8">No data</div>;
        return (
          <div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 mb-4">
              <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
                <p className="text-xs text-gray-500">Total Staff</p>
                <p className="text-xl font-bold">{therapistData.length}</p>
              </div>
              <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
                <p className="text-xs text-gray-500">Total Sessions</p>
                <p className="text-xl font-bold">{therapistData.reduce((s: number, r: any) => s + Number(r.total_sessions || 0), 0)}</p>
              </div>
              <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
                <p className="text-xs text-gray-500">Total Revenue</p>
                <p className="text-xl font-bold text-[#C9A96E]">
                  {formatCurrency(therapistData.reduce((s: number, r: any) => s + Number(r.revenue_generated || r.total_revenue || 0), 0))}
                </p>
              </div>
              <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
                <p className="text-xs text-gray-500">Avg Revenue/Staff</p>
                <p className="text-xl font-bold">
                  {formatCurrency(therapistData.reduce((s: number, r: any) => s + Number(r.revenue_generated || r.total_revenue || 0), 0) / Math.max(therapistData.length, 1))}
                </p>
              </div>
            </div>
            <table className="w-full">
              <thead className="bg-[#C9A96E] text-white">
                <tr>
                  <th className="px-4 py-3 text-left text-sm">#</th>
                  <th className="px-4 py-3 text-left text-sm">Therapist</th>
                  <th className="px-4 py-3 text-right text-sm">Sessions</th>
                  <th className="px-4 py-3 text-right text-sm">Revenue Generated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {therapistData.map((t: any, i: number) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}
                    </td>
                    <td className="px-4 py-3 font-medium">{t.therapist_name}</td>
                    <td className="px-4 py-3 text-right">{t.total_sessions}</td>
                    <td className="px-4 py-3 text-right font-semibold">{formatCurrency(Number(t.revenue_generated || t.total_revenue || 0))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }


      case 'commission': {
        const commissionData = data.commission || { summary: [], detail: [] };
        const summary = commissionData.summary || [];
        const detail = commissionData.detail || [];
        const pending = detail.filter((c: any) => c.status === 'pending');
        const totalAmount = detail.reduce((s: number, c: any) => s + Number(c.commission_amount || 0), 0);
        const pendingAmount = pending.reduce((s: number, c: any) => s + Number(c.commission_amount || 0), 0);

        const refreshCommission = async () => {
          setLoading(true);
          setError(null);
          try {
            const params = buildParams();
            const [summaryRes, detailRes] = await Promise.all([
              api.getCommissionSummary(params),
              api.getCommissionDetail(params),
            ]);
            setData((prev) => ({ ...prev, commission: { summary: summaryRes.items || [], detail: detailRes.items || [] } }));
          } catch (err: any) {
            setError(err.message);
          } finally {
            setLoading(false);
          }
        };

        const generate = async () => {
          try {
            const res = await api.generateCommissions(buildParams());
            alert(res.message || `Generated ${res.generated || 0} commissions`);
            await refreshCommission();
          } catch (err: any) {
            alert('Generate failed: ' + err.message);
          }
        };

        const markAllPendingPaid = async () => {
          const ids = pending.map((c: any) => c.id);
          if (!ids.length) return alert('Tidak ada komisi pending');
          if (!confirm(`Mark ${ids.length} komisi pending sebagai paid?`)) return;
          try {
            await api.markCommissionsPaid(ids);
            await refreshCommission();
          } catch (err: any) {
            alert('Mark paid failed: ' + err.message);
          }
        };

        return (
          <div>
            <div className="flex flex-wrap items-center justify-between gap-3 p-4 border-b border-gray-100">
              <div>
                <h3 className="font-semibold text-gray-800">💵 Staff Commission Tracking</h3>
                <p className="text-xs text-gray-500">Generate dari treatment completed, lalu mark paid saat komisi sudah dibayarkan.</p>
              </div>
              <div className="flex gap-2">
                <button onClick={generate} className="px-4 py-2 bg-[#C9A96E] text-white rounded-lg text-sm font-medium hover:bg-[#8B6914]">⚙️ Generate</button>
                <button onClick={markAllPendingPaid} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">✅ Mark Pending Paid</button>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4">
              <div className="bg-[#C9A96E]/10 rounded-lg p-4">
                <p className="text-xs text-gray-500">Commission Records</p>
                <p className="text-2xl font-bold">{detail.length}</p>
              </div>
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-xs text-gray-500">Total Commission</p>
                <p className="text-xl font-bold text-blue-600">{formatCurrency(totalAmount)}</p>
              </div>
              <div className="bg-yellow-50 rounded-lg p-4">
                <p className="text-xs text-gray-500">Pending Amount</p>
                <p className="text-xl font-bold text-yellow-700">{formatCurrency(pendingAmount)}</p>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-xs text-gray-500">Paid Amount</p>
                <p className="text-xl font-bold text-green-600">{formatCurrency(totalAmount - pendingAmount)}</p>
              </div>
            </div>

            {summary.length > 0 && (
              <div className="px-4 pb-4">
                <h4 className="font-semibold text-gray-700 mb-2">By Therapist</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {summary.map((s: any) => (
                    <div key={s.therapist_id} className="border border-gray-200 rounded-lg p-3">
                      <div className="font-medium text-gray-800">{s.therapist_name}</div>
                      <div className="text-xs text-gray-500">{s.total_commissions} records</div>
                      <div className="mt-2 flex justify-between text-sm"><span>Total</span><b>{formatCurrency(Number(s.total_amount || 0))}</b></div>
                      <div className="flex justify-between text-sm text-yellow-700"><span>Pending</span><b>{formatCurrency(Number(s.pending_amount || 0))}</b></div>
                      <div className="flex justify-between text-sm text-green-700"><span>Paid</span><b>{formatCurrency(Number(s.paid_amount || 0))}</b></div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <table className="w-full">
              <thead className="bg-[#C9A96E] text-white">
                <tr>
                  <th className="px-4 py-3 text-left text-sm">Date</th>
                  <th className="px-4 py-3 text-left text-sm">Therapist</th>
                  <th className="px-4 py-3 text-left text-sm">Treatment</th>
                  <th className="px-4 py-3 text-right text-sm">Price</th>
                  <th className="px-4 py-3 text-right text-sm">Rate</th>
                  <th className="px-4 py-3 text-right text-sm">Commission</th>
                  <th className="px-4 py-3 text-center text-sm">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {detail.map((c: any) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">{new Date(c.created_at).toLocaleDateString('id-ID')}</td>
                    <td className="px-4 py-3 font-medium">{c.therapist_name}</td>
                    <td className="px-4 py-3 text-sm">{c.treatment_name}</td>
                    <td className="px-4 py-3 text-right">{formatCurrency(Number(c.treatment_price || 0))}</td>
                    <td className="px-4 py-3 text-right">{Number(c.commission_rate || 0).toFixed(1)}%</td>
                    <td className="px-4 py-3 text-right font-semibold">{formatCurrency(Number(c.commission_amount || 0))}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${c.status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                        {c.status === 'paid' ? '✅ Paid' : '⏳ Pending'}
                      </span>
                    </td>
                  </tr>
                ))}
                {detail.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Belum ada data komisi. Klik Generate untuk membuat dari completed treatment.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        );
      }

      case 'inventory': {
        const inventoryData = data.inventory as any[];
        if (!inventoryData?.length) return <div className="text-gray-500 text-center py-8">No data</div>;
        const totalQty = inventoryData.reduce((sum: number, s: any) => sum + Number(s.balance || 0), 0);
        const lowStock = inventoryData.filter((s: any) => Number(s.balance || 0) < 10).length;
        return (
          <div>
            <div className="grid grid-cols-3 gap-4 p-4 mb-4">
              <div className="bg-[#C9A96E]/10 rounded-lg p-4">
                <p className="text-sm text-gray-600">Total Products</p>
                <p className="text-2xl font-bold text-[#C9A96E]">{inventoryData.length}</p>
              </div>
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-sm text-gray-600">Total Quantity</p>
                <p className="text-2xl font-bold text-blue-600">{totalQty.toLocaleString()}</p>
              </div>
              <div className={`${lowStock > 0 ? 'bg-red-50' : 'bg-green-50'} rounded-lg p-4`}>
                <p className="text-sm text-gray-600">Low Stock Items</p>
                <p className={`text-2xl font-bold ${lowStock > 0 ? 'text-red-600' : 'text-green-600'}`}>{lowStock}</p>
              </div>
            </div>
            <table className="w-full">
              <thead className="bg-[#C9A96E] text-white">
                <tr>
                  <th className="px-4 py-3 text-left text-sm">Product</th>
                  <th className="px-4 py-3 text-left text-sm">SKU</th>
                  <th className="px-4 py-3 text-right text-sm">Qty In</th>
                  <th className="px-4 py-3 text-right text-sm">Qty Out</th>
                  <th className="px-4 py-3 text-right text-sm">Balance</th>
                  <th className="px-4 py-3 text-right text-sm">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {inventoryData.map((s: any, i: number) => {
                  const bal = Number(s.balance || 0);
                  const status = bal === 0 ? { text: '⛔ Empty', cls: 'text-red-700 bg-red-100' }
                    : bal < 5 ? { text: '🔴 Critical', cls: 'text-red-600 bg-red-50' }
                    : bal < 10 ? { text: '🟡 Low', cls: 'text-yellow-600 bg-yellow-50' }
                    : { text: '🟢 OK', cls: 'text-green-600 bg-green-50' };
                  return (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3">{s.product_name}</td>
                      <td className="px-4 py-3 font-mono text-sm">{s.sku}</td>
                      <td className="px-4 py-3 text-right">{s.qty_in}</td>
                      <td className="px-4 py-3 text-right">{s.qty_out}</td>
                      <td className="px-4 py-3 text-right font-semibold">{bal}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${status.cls}`}>{status.text}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
      }

      case 'finance': {
        const financeData = data.finance as any;
        if (!financeData) return <div className="text-gray-500 text-center py-8">No data</div>;
        const margin = financeData.revenue > 0
          ? ((financeData.revenue - financeData.expenses) / financeData.revenue * 100)
          : 0;
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
            <div className="bg-green-50 border border-green-200 rounded-xl p-6">
              <p className="text-sm text-green-700">Revenue</p>
              <p className="text-3xl font-bold text-green-600 mt-2">{formatCurrency(financeData.revenue)}</p>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-xl p-6">
              <p className="text-sm text-red-700">Expenses</p>
              <p className="text-3xl font-bold text-red-600 mt-2">{formatCurrency(financeData.expenses)}</p>
            </div>
            <div className="bg-[#C9A96E]/10 border border-[#C9A96E] rounded-xl p-6">
              <p className="text-sm text-[#8B6914]">Net Profit</p>
              <p className="text-3xl font-bold text-[#C9A96E] mt-2">{formatCurrency(financeData.net_profit)}</p>
            </div>
            <div className="bg-[#C08081]/10 border border-[#C08081] rounded-xl p-6">
              <p className="text-sm text-[#8B4041]">Profit Margin</p>
              <p className="text-3xl font-bold text-[#C08081] mt-2">{margin.toFixed(1)}%</p>
            </div>
            {financeData.ap_outstanding > 0 && (
              <div className="bg-orange-50 border border-orange-200 rounded-xl p-6 md:col-span-2">
                <p className="text-sm text-orange-700">AP Outstanding</p>
                <p className="text-2xl font-bold text-orange-600 mt-2">{formatCurrency(financeData.ap_outstanding)}</p>
              </div>
            )}
            {financeData.bank_balances?.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 md:col-span-2">
                <p className="text-sm text-blue-700 mb-3">Bank Balances</p>
                <div className="space-y-2">
                  {financeData.bank_balances.map((b: any, i: number) => (
                    <div key={i} className="flex justify-between">
                      <span className="text-sm">{b.bank_name} ({b.account_no})</span>
                      <span className="font-semibold">{formatCurrency(Number(b.balance))}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      }

      case 'shift': {
        const shiftData = data.shift as any[];
        if (!shiftData?.length) return <div className="text-gray-500 text-center py-8">No data</div>;
        const closedShifts = shiftData.filter((s: any) => s.status === 'closed');
        const totalSales = closedShifts.reduce((sum: number, s: any) => sum + Number(s.total_sales || 0), 0);
        const totalTxns = closedShifts.reduce((sum: number, s: any) => sum + Number(s.transaction_count || 0), 0);
        const totalVariance = closedShifts.reduce((sum: number, s: any) => sum + Number(s.variance || 0), 0);
        return (
          <div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 mb-4">
              <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
                <p className="text-xs text-gray-500">Total Shifts</p>
                <p className="text-xl font-bold">{shiftData.length}</p>
              </div>
              <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
                <p className="text-xs text-gray-500">Total Transactions</p>
                <p className="text-xl font-bold">{totalTxns}</p>
              </div>
              <div className="bg-gradient-to-br from-[#C9A96E]/10 to-[#C08081]/10 rounded-lg p-4">
                <p className="text-xs text-gray-500">Total Sales</p>
                <p className="text-xl font-bold text-[#C9A96E]">{formatCurrency(totalSales)}</p>
              </div>
              <div className={`rounded-lg p-4 ${totalVariance >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                <p className="text-xs text-gray-500">Total Variance</p>
                <p className={`text-xl font-bold ${totalVariance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {totalVariance >= 0 ? '+' : ''}{formatCurrency(totalVariance)}
                </p>
              </div>
            </div>
            <table className="w-full">
              <thead className="bg-[#C9A96E] text-white">
                <tr>
                  <th className="px-4 py-3 text-left text-sm">Shift Code</th>
                  <th className="px-4 py-3 text-left text-sm">Staff</th>
                  <th className="px-4 py-3 text-left text-sm">Branch</th>
                  <th className="px-4 py-3 text-right text-sm">Opening</th>
                  <th className="px-4 py-3 text-right text-sm">Closing</th>
                  <th className="px-4 py-3 text-right text-sm">Sales</th>
                  <th className="px-4 py-3 text-right text-sm">Txns</th>
                  <th className="px-4 py-3 text-right text-sm">Variance</th>
                  <th className="px-4 py-3 text-center text-sm">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {shiftData.map((s: any, i: number) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-sm">{s.shift_code}</td>
                    <td className="px-4 py-3 font-medium">{s.staff_name}</td>
                    <td className="px-4 py-3 text-sm">{s.branch || '-'}</td>
                    <td className="px-4 py-3 text-right">{formatCurrency(Number(s.opening_cash || 0))}</td>
                    <td className="px-4 py-3 text-right">{s.closing_cash ? formatCurrency(Number(s.closing_cash)) : '-'}</td>
                    <td className="px-4 py-3 text-right font-semibold">{formatCurrency(Number(s.total_sales || 0))}</td>
                    <td className="px-4 py-3 text-right">{s.transaction_count || 0}</td>
                    <td className={`px-4 py-3 text-right font-medium ${Number(s.variance || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {s.variance != null ? formatCurrency(Number(s.variance)) : '-'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${s.status === 'closed' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                        {s.status === 'closed' ? '✅ Closed' : '🔵 Open'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-800">📊 Reports</h1>
        <div className="flex items-center gap-3">
          {/* Date range */}
          <div className="flex items-center gap-2 bg-white rounded-lg shadow px-3 py-2">
            <label className="text-xs text-gray-500">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); setActivePreset(null); }}
              className="border border-gray-300 rounded px-2 py-1 text-sm"
            />
            <label className="text-xs text-gray-500">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => { setDateTo(e.target.value); setActivePreset(null); }}
              className="border border-gray-300 rounded px-2 py-1 text-sm"
            />
          </div>
          {/* Branch filter */}
          {branches.length > 0 && (
            <select
              value={branchId}
              onChange={(e) => setBranchId(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white shadow"
            >
              <option value="">Semua Cabang</option>
              {branches.map((b: any) => (
                <option key={b.id} value={b.id}>{b.code} - {b.name}</option>
              ))}
            </select>
          )}
          {/* Export buttons */}
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors text-sm font-medium"
          >
            <span>📥</span> CSV
          </button>
          <button
            onClick={handleExportExcel}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            <span>📊</span> Excel
          </button>
        </div>
      </div>

      {/* Date presets */}
      <div className="flex flex-wrap gap-2">
        {datePresets.map((preset) => (
          <button
            key={preset.label}
            onClick={() => handlePreset(preset)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              activePreset === preset.label
                ? 'bg-[#C9A96E] text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {preset.label}
          </button>
        ))}
      </div>

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
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}
