import { useState, useEffect } from 'react';
import { api } from '../api/client';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';

interface DashboardData {
  today: { sales_amount: number; transaction_count: number };
  month: { sales_amount: number; transaction_count: number };
  alerts: { pending_sync: number; open_exceptions: number; pending_approvals: number; low_stock: number };
  top_treatments: { item_name: string; count: number; revenue: number }[];
  recent_transactions: { doc_key: string; customer_name: string; total: number; status: string; created_at: string }[];
  sales_trend: { date: string; transactions: number; revenue: number }[];
  sales_by_payment: { method: string; count: number; amount: number }[];
  low_stock_items: { name: string; sku: string; balance: number }[];
}

const COLORS = ['#C9A96E', '#8B6914', '#C08081', '#6B8E23', '#4682B4', '#DAA520'];
const formatRp = (n: number) => 'Rp ' + (n || 0).toLocaleString('id-ID');
const formatShort = (n: number) => {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'jt';
  if (n >= 1_000) return (n / 1_000).toFixed(0) + 'rb';
  return n.toString();
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDashboard()
      .then((res) => setData(res))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#C9A96E]"></div>
      </div>
    );
  }

  if (!data) {
    return <div className="text-center py-16 text-gray-500">Gagal memuat dashboard</div>;
  }

  const trendData = (data.sales_trend || []).map((d) => ({
    ...d,
    revenue: Number(d.revenue),
    date: new Date(d.date).toLocaleDateString('id-ID', { day: '2-digit', month: 'short' }),
  }));

  const paymentData = (data.sales_by_payment || []).map((d) => ({
    ...d,
    amount: Number(d.amount),
    name: d.method || 'Unknown',
  }));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>

      {/* ── KPI Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard label="Penjualan Hari Ini" value={formatRp(data.today.sales_amount)} icon="💰" sub={`${data.today.transaction_count} transaksi`} />
        <KPICard label="Penjualan Bulan Ini" value={formatRp(data.month.sales_amount)} icon="📈" sub={`${data.month.transaction_count} transaksi`} />
        <KPICard label="Pending Sync" value={String(data.alerts.pending_sync)} icon="🔄" alert={data.alerts.pending_sync > 0} />
        <KPICard label="Stok Rendah" value={String(data.alerts.low_stock)} icon="⚠️" alert={data.alerts.low_stock > 0} />
      </div>

      {/* ── Sales Trend Chart (14 days) ── */}
      {trendData.length > 0 && (
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-4">📊 Tren Penjualan (14 Hari)</h2>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={trendData}>
              <defs>
                <linearGradient id="goldGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#C9A96E" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#C9A96E" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={formatShort} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: any) => formatRp(Number(v))} />
              <Area type="monotone" dataKey="revenue" stroke="#C9A96E" fill="url(#goldGradient)" strokeWidth={2} name="Revenue" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── Top Treatments ── */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-4">🏆 Top Treatments</h2>
          {(data.top_treatments || []).length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.top_treatments} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tickFormatter={formatShort} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="item_name" width={120} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v: any) => formatRp(Number(v))} />
                <Bar dataKey="revenue" fill="#C9A96E" radius={[0, 4, 4, 0]} name="Revenue" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-center py-8">Belum ada data</p>
          )}
        </div>

        {/* ── Sales by Payment Method ── */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-4">💳 Metode Pembayaran</h2>
          {paymentData.length > 0 ? (
            <div className="flex items-center gap-6">
              <ResponsiveContainer width="50%" height={250}>
                <PieChart>
                  <Pie data={paymentData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} dataKey="amount" nameKey="name" label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}>
                    {paymentData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v: any) => formatRp(Number(v))} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {paymentData.map((p, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                    <span className="text-sm text-gray-600 flex-1">{p.name || 'Unknown'}</span>
                    <span className="text-sm font-semibold">{formatRp(p.amount)}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-gray-400 text-center py-8">Belum ada data</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── Low Stock Alert ── */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-4">⚠️ Stok Rendah</h2>
          {(data.low_stock_items || []).length > 0 ? (
            <div className="space-y-3">
              {data.low_stock_items.map((item, i) => (
                <div key={i} className="flex items-center justify-between bg-red-50 rounded-lg p-3">
                  <div>
                    <p className="font-medium text-gray-800">{item.name}</p>
                    <p className="text-xs text-gray-500 font-mono">{item.sku}</p>
                  </div>
                  <span className={`font-bold text-lg ${item.balance <= 3 ? 'text-red-600' : 'text-orange-500'}`}>
                    {item.balance}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-green-600 text-center py-8">✅ Semua stok aman</p>
          )}
        </div>

        {/* ── Recent Transactions ── */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-4">🧾 Transaksi Terakhir</h2>
          <div className="space-y-2">
            {(data.recent_transactions || []).slice(0, 8).map((tx, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div>
                  <p className="text-sm font-mono font-medium text-gray-800">{tx.doc_key}</p>
                  <p className="text-xs text-gray-500">{tx.customer_name || 'Tamu'}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">{formatRp(tx.total)}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    tx.status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>{tx.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function KPICard({ label, value, icon, sub, alert }: { label: string; value: string; icon: string; sub?: string; alert?: boolean }) {
  return (
    <div className={`bg-white rounded-xl shadow-lg p-5 ${alert ? 'ring-2 ring-red-400' : ''}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-xl font-bold text-gray-800 mt-1">{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
        </div>
        <span className="text-2xl">{icon}</span>
      </div>
    </div>
  );
}
