import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import { parseUTCDate } from '../utils/dateUtils';

interface DashboardData {
  todayTransactions: number;
  todayRevenue: number;
  activeBookings: number;
  pendingClosing: boolean;
  recentTransactions: Array<{
    id: string;
    posCode: string;
    total: number;
    state: string;
    createdAt: string;
    customerName?: string;
  }>;
}

const STATE_COLORS: Record<string, string> = {
  PAID: 'bg-green-100 text-green-700',
  DRAFT: 'bg-gray-100 text-gray-600',
  CANCELLED: 'bg-red-100 text-red-600',
  VOIDED: 'bg-red-100 text-red-600',
  PAYMENT_PENDING: 'bg-yellow-100 text-yellow-700',
};

export default function PosHomePage() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const staff = (() => {
    try {
      return JSON.parse(localStorage.getItem('pos_staff') || '{}');
    } catch {
      return {};
    }
  })();

  const formatRp = (n: number) => 'Rp ' + (n || 0).toLocaleString('id-ID');

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      // Use dedicated home-summary endpoint (no branch filter = all branches)
      const summary = await api.getHomeSummary();
      setData({
        todayTransactions: summary.today_transactions || 0,
        todayRevenue: summary.today_revenue || 0,
        activeBookings: summary.active_bookings || 0,
        pendingClosing: false,
        recentTransactions: (summary.recent_transactions || []).map((t: any) => ({
          id: t.doc_key,
          posCode: t.doc_key || '-',
          total: t.total || 0,
          state: t.status?.toUpperCase() || 'DRAFT',
          createdAt: t.created_at || new Date().toISOString(),
          customerName: t.customer_name || '-',
        })),
      });
    } catch (err: any) {
      setError(err.message || 'Gagal memuat data dashboard');
    }
    setLoading(false);
  }

  const now = new Date();
  const greeting = now.getHours() < 12 ? 'Selamat Pagi' : now.getHours() < 17 ? 'Selamat Siang' : 'Selamat Sore';

  return (
    <div className="p-4 space-y-4">
      {/* Error Toast */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {/* Greeting Card */}
      <div className="bg-gradient-to-br from-[var(--gold)] to-[var(--rose)] rounded-2xl p-5 text-white shadow-lg">
        <p className="text-sm opacity-90">{greeting},</p>
        <h2 className="text-xl font-bold mt-0.5">{staff.name || 'Kasir'}</h2>
        <div className="flex items-center justify-between mt-2 flex-wrap gap-2">
          <p className="text-xs opacity-75">
            {now.toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          </p>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 bg-white/20 rounded-full px-2.5 py-1">
              <span className="text-xs">🔓</span>
              <span className="text-xs font-medium">{localStorage.getItem('pos_shift_code') || 'Shift Aktif'}</span>
            </div>
            <div className="flex items-center gap-1.5 bg-white/20 rounded-full px-2.5 py-1">
              <span className="text-xs">💵</span>
              <span className="text-xs font-medium">
                Kas Awal: Rp {Number(localStorage.getItem('pos_opening_cash') || 0).toLocaleString('id-ID')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Stale shift warning */}
      {(() => {
        const shiftCode = localStorage.getItem('pos_shift_code') || '';
        const match = shiftCode.match(/SFT-\w+-(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/);
        if (match) {
          const shiftDate = new Date(parseInt(match[1]), parseInt(match[2])-1, parseInt(match[3]),
                                     parseInt(match[4]), parseInt(match[5]), parseInt(match[6]));
          const hoursSince = (now.getTime() - shiftDate.getTime()) / (1000*60*60);
          if (hoursSince > 12) {
            return (
              <div className="bg-amber-50 border border-amber-200 text-amber-700 text-sm px-4 py-3 rounded-xl flex items-center gap-2">
                <span>⚠️</span>
                <span>Shift ini sudah aktif lebih dari 12 jam. Pertimbangkan untuk tutup shift dan buka shift baru.</span>
              </div>
            );
          }
        }
        return null;
      })()}

      {/* Stats Cards */}
      {loading ? (
        <LoadingSkeleton rows={2} />
      ) : data && (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
            <p className="text-xs text-gray-400">Transaksi Hari Ini</p>
            <p className="text-2xl font-bold text-[var(--charcoal)] mt-1">{data.todayTransactions}</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
            <p className="text-xs text-gray-400">Pendapatan</p>
            <p className="text-lg font-bold text-[var(--charcoal)] mt-1">{formatRp(data.todayRevenue)}</p>
          </div>
        </div>
      )}

      {/* Recent Transactions */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-[var(--charcoal)]">Transaksi Terakhir</h3>
          <button onClick={() => navigate('/kasir')} className="text-xs text-[var(--gold)] font-medium">
            Lihat Semua
          </button>
        </div>
        {loading ? (
          <LoadingSkeleton rows={3} />
        ) : data?.recentTransactions.length ? (
          <div className="space-y-2">
            {data.recentTransactions.map((tx) => (
              <button
                key={tx.id}
                onClick={() => navigate(`/receipt/${tx.id}`)}
                className="w-full bg-white rounded-xl p-3 border border-gray-100 shadow-sm flex items-center justify-between text-left active:bg-gray-50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[var(--charcoal)] font-mono">{tx.posCode}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATE_COLORS[tx.state] || 'bg-gray-100 text-gray-600'}`}>
                      {tx.state}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">{tx.customerName}</p>
                </div>
                <span className="text-sm font-semibold text-[var(--charcoal)]">{formatRp(tx.total)}</span>
              </button>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-xl p-6 border border-gray-100 text-center">
            <p className="text-gray-400 text-sm">Belum ada transaksi hari ini</p>
          </div>
        )}
      </div>

      {/* Refresh Button */}
      <button
        onClick={loadDashboard}
        disabled={loading}
        className="w-full py-3 rounded-xl border border-gray-200 text-sm font-medium text-gray-500 active:bg-gray-50 transition-colors disabled:opacity-50"
      >
        {loading ? 'Memuat...' : '↻ Muat Ulang'}
      </button>
    </div>
  );
}
