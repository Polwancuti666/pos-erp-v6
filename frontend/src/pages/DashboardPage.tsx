import { useAutoRefresh } from '@/hooks/useAutoRefresh';
import { dashboardApi } from '@/api/client';
import { DashboardSummary, DashboardAlert } from '@/types';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';

function MetricCard({ label, value, type = 'primary', subtitle, badge }: {
  label: string; value: string; type?: 'primary' | 'warning' | 'danger' | 'info'; subtitle?: string; badge?: string;
}) {
  const COLORS = {
    primary: 'bg-white border-gray-100',
    warning: 'bg-yellow-50 border-yellow-200',
    danger: 'bg-red-50 border-red-200',
    info: 'bg-blue-50 border-blue-200',
  };
  return (
    <div className={`rounded-xl border p-4 ${COLORS[type]}`}>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-xl font-bold text-charcoal">{value}</p>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
      {badge && <span className="inline-block mt-1 px-2 py-0.5 bg-red-100 text-red-600 text-xs rounded-full">{badge}</span>}
    </div>
  );
}

function AlertBanner({ alerts }: { alerts: DashboardAlert[] }) {
  if (!alerts.length) return null;
  return (
    <div className="space-y-2">
      {alerts.map((a, i) => (
        <div
          key={i}
          className={`p-3 rounded-xl text-sm ${
            a.severity === 'critical' ? 'bg-red-100 text-red-700' :
            a.severity === 'warning' ? 'bg-yellow-100 text-yellow-700' :
            'bg-blue-100 text-blue-700'
          }`}
        >
          {a.message}
          {a.count > 0 && <span className="ml-2 font-bold">({a.count})</span>}
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const today = new Date().toISOString().split('T')[0];
  const { data: summary, loading, lastUpdated, refresh } = useAutoRefresh<DashboardSummary>(
    () => dashboardApi.summary(today, 'HQ'), 300000
  );
  const { data: alerts } = useAutoRefresh<DashboardAlert[]>(
    () => dashboardApi.alerts(), 300000
  );

  const fmt = (n: number) => 'Rp ' + n.toLocaleString('id-ID');

  if (loading && !summary) return <div className="p-4"><LoadingSkeleton rows={6} /></div>;
  if (!summary) return <div className="p-4 text-center text-gray-500">Gagal memuat data</div>;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-charcoal">Dashboard Owner</h2>
        <div className="text-right">
          {lastUpdated && (
            <p className="text-xs text-gray-400">Diperbarui: {lastUpdated.toLocaleTimeString('id-ID')}</p>
          )}
          <button onClick={refresh} className="text-xs text-gold font-medium">Refresh</button>
        </div>
      </div>

      <AlertBanner alerts={alerts || []} />

      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Operasional Sales" value={fmt(summary.operationalSales)} subtitle="Termasuk yang belum dibukukan" />
        <MetricCard label="Pendapatan Tercatat" value={fmt(summary.postedRevenue)} type="primary" />
        <MetricCard
          label="Belum Tercatat"
          value={fmt(summary.unpostedPaidSales)}
          type={summary.unpostedPaidSales > 0 ? 'warning' : 'info'}
          badge={summary.unpostedPaidSales > 0 ? 'Perlu perhatian' : undefined}
        />
        <MetricCard
          label="Variance Belum Selesai"
          value={String(summary.unreconciledVariance.count)}
          type={summary.unreconciledVariance.count > 0 ? 'danger' : 'info'}
          badge={summary.unreconciledVariance.count > 0 ? 'Action needed' : undefined}
        />
      </div>

      {/* Transaction Counts */}
      <div className="bg-white rounded-xl border border-gray-100 p-4">
        <h3 className="text-sm font-semibold text-charcoal mb-3">Transaksi Hari Ini</h3>
        <div className="grid grid-cols-4 gap-2 text-center">
          <div><p className="text-lg font-bold">{summary.transactionCounts.total}</p><p className="text-xs text-gray-500">Total</p></div>
          <div><p className="text-lg font-bold">{summary.transactionCounts.cash}</p><p className="text-xs text-gray-500">Tunai</p></div>
          <div><p className="text-lg font-bold">{summary.transactionCounts.qris}</p><p className="text-xs text-gray-500">QRIS</p></div>
          <div><p className="text-lg font-bold">{summary.transactionCounts.bankTransfer}</p><p className="text-xs text-gray-500">Transfer</p></div>
        </div>
      </div>

      {/* Top Services */}
      {summary.topServices.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <h3 className="text-sm font-semibold text-charcoal mb-3">Top Layanan</h3>
          <div className="space-y-2">
            {summary.topServices.map((s, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div>
                  <span className="text-xs text-gray-400 mr-2">#{i + 1}</span>
                  <span className="text-sm font-medium">{s.name}</span>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">{fmt(s.revenue)}</p>
                  <p className="text-xs text-gray-400">{s.count}x</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
