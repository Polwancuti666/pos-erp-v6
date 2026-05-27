import { useAutoRefresh } from '@/hooks/useAutoRefresh';
import { dashboardApi } from '@/api/client';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';

// Map API response to display format
interface BranchData {
  branch_code: string;
  operational_sales: string;
  paid_pending_posting: string;
  posted_revenue: string;
  unreconciled_variance: string;
  pending_sync_count: number;
  failed_retry_count: number;
  last_sync_at: string;
  is_stale: boolean;
  queue_alert: boolean;
  sla_alert: boolean;
}

interface DashboardData {
  branches: BranchData[];
  total_operational_sales: string;
  total_posted_revenue: string;
  total_pending_sync_count: number;
}

interface AlertData {
  alert_type: string;
  severity: string;
  message: string;
  count: number;
}

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

function AlertBanner({ alerts }: { alerts: AlertData[] }) {
  if (!alerts.length) return null;
  return (
    <div className="space-y-2">
      {alerts.map((a, i) => (
        <div
          key={i}
          className={`p-3 rounded-xl text-sm ${
            a.severity === 'critical' || a.severity === 'CRITICAL' ? 'bg-red-100 text-red-700' :
            a.severity === 'warning' || a.severity === 'WARNING' ? 'bg-yellow-100 text-yellow-700' :
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
  const { data: dashData, loading, lastUpdated, refresh } = useAutoRefresh<DashboardData>(
    () => dashboardApi.summary(today), 300000
  );
  const { data: alerts } = useAutoRefresh<AlertData[]>(
    () => dashboardApi.alerts(), 300000
  );

  const fmt = (n: string | number | undefined) => {
    if (n === undefined || n === null) return 'Rp 0';
    const num = typeof n === 'string' ? parseFloat(n) : n;
    if (isNaN(num)) return 'Rp 0';
    return 'Rp ' + num.toLocaleString('id-ID');
  };

  if (loading && !dashData) return <div className="p-4"><LoadingSkeleton rows={6} /></div>;
  if (!dashData) return <div className="p-4 text-center text-gray-500">Gagal memuat data</div>;

  const totalOps = parseFloat(dashData.total_operational_sales) || 0;
  const totalPosted = parseFloat(dashData.total_posted_revenue) || 0;
  const unposted = totalOps - totalPosted;
  const hq = dashData.branches.find(b => b.branch_code === 'HQ');

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
        <MetricCard label="Operasional Sales" value={fmt(totalOps)} subtitle="Termasuk yang belum dibukukan" />
        <MetricCard label="Pendapatan Tercatat" value={fmt(totalPosted)} type="primary" />
        <MetricCard
          label="Belum Tercatat"
          value={fmt(unposted)}
          type={unposted > 0 ? 'warning' : 'info'}
          badge={unposted > 0 ? 'Perlu perhatian' : undefined}
        />
        <MetricCard
          label="Pending Sync"
          value={String(dashData.total_pending_sync_count)}
          type={dashData.total_pending_sync_count > 10 ? 'danger' : 'info'}
          badge={dashData.total_pending_sync_count > 10 ? 'Perlu sync' : undefined}
        />
      </div>

      {/* Branch Details */}
      <div className="bg-white rounded-xl border border-gray-100 p-4">
        <h3 className="text-sm font-semibold text-charcoal mb-3">Cabang</h3>
        <div className="space-y-3">
          {dashData.branches.map((b) => (
            <div key={b.branch_code} className={`p-3 rounded-lg border ${b.is_stale ? 'border-yellow-300 bg-yellow-50' : 'border-gray-100'}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-charcoal">{b.branch_code}</span>
                {b.is_stale && <span className="text-xs text-yellow-700 bg-yellow-200 px-2 py-0.5 rounded-full">Stale</span>}
                {b.queue_alert && <span className="text-xs text-red-700 bg-red-200 px-2 py-0.5 rounded-full ml-1">Queue Alert</span>}
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <p className="text-gray-500">Sales</p>
                  <p className="font-medium">{fmt(b.operational_sales)}</p>
                </div>
                <div>
                  <p className="text-gray-500">Posted</p>
                  <p className="font-medium">{fmt(b.posted_revenue)}</p>
                </div>
                <div>
                  <p className="text-gray-500">Pending Sync</p>
                  <p className="font-medium">{b.pending_sync_count}</p>
                </div>
                <div>
                  <p className="text-gray-500">Variance</p>
                  <p className="font-medium">{fmt(b.unreconciled_variance)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
