import { Link } from 'react-router-dom';

const MODULES = [
  {
    to: '/dashboard',
    icon: '📊',
    title: 'Dashboard',
    desc: 'Monitor penjualan, cabang, sync status & alert real-time',
    color: 'from-blue-500/10 to-blue-500/5',
    border: 'border-blue-200',
    iconBg: 'bg-blue-100',
  },
  {
    to: '/exceptions',
    icon: '⚠️',
    title: 'Exception Queue',
    desc: 'Tangani sync failure, unmapped COA & masalah operasional',
    color: 'from-amber-500/10 to-amber-500/5',
    border: 'border-amber-200',
    iconBg: 'bg-amber-100',
  },
  {
    to: '/coa',
    icon: '📋',
    title: 'COA Mapping',
    desc: 'Mapping chart of accounts untuk integrasi akuntansi',
    color: 'from-purple-500/10 to-purple-500/5',
    border: 'border-purple-200',
    iconBg: 'bg-purple-100',
  },
  {
    to: '/closing',
    icon: '🔒',
    title: 'Daily Closing',
    desc: 'Tutup operasional harian, rekonsiliasi & laporan',
    color: 'from-rose-500/10 to-rose-500/5',
    border: 'border-rose-200',
    iconBg: 'bg-rose-100',
  },
];

export default function HomePage() {
  return (
    <div className="max-w-5xl mx-auto">
      {/* Hero */}
      <div className="mb-8">
        <h2 className="text-2xl md:text-3xl font-bold text-[var(--charcoal)] mb-2">
          Menu Utama
        </h2>
        <p className="text-gray-500 text-sm md:text-base">
          Pilih modul untuk mengelola operasional Beauty & Shine
        </p>
      </div>

      {/* Module Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-4 md:gap-5">
        {MODULES.map((mod, i) => (
          <Link
            key={mod.to}
            to={mod.to}
            className={`group relative bg-gradient-to-br ${mod.color} border ${mod.border} rounded-2xl p-5 md:p-6 transition-all hover:shadow-lg hover:-translate-y-1 hover:border-gray-300`}
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <div className="flex items-start gap-4">
              <div className={`${mod.iconBg} w-12 h-12 rounded-xl flex items-center justify-center text-2xl shrink-0 group-hover:scale-110 transition-transform`}>
                {mod.icon}
              </div>
              <div className="min-w-0">
                <h3 className="font-semibold text-[var(--charcoal)] text-base mb-1 group-hover:text-[var(--gold)] transition-colors">
                  {mod.title}
                </h3>
                <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">
                  {mod.desc}
                </p>
              </div>
            </div>
            <div className="absolute top-4 right-4 text-gray-300 group-hover:text-[var(--gold)] transition-colors">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </div>
          </Link>
        ))}
      </div>

      {/* Quick Stats */}
      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Hari Ini', value: 'Rp 23.5jt', icon: '💰', sub: 'Operational Sales' },
          { label: 'Pending Sync', value: '67', icon: '🔄', sub: 'Transaksi' },
          { label: 'Exception', value: '3', icon: '⚠️', sub: 'Open Issues' },
          { label: 'Cabang', value: '2', icon: '🏪', sub: 'Aktif' },
        ].map(stat => (
          <div key={stat.label} className="bg-white rounded-xl border border-gray-100 p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">{stat.icon}</span>
              <span className="text-xs text-gray-400">{stat.label}</span>
            </div>
            <div className="text-xl font-bold text-[var(--charcoal)]">{stat.value}</div>
            <div className="text-[10px] text-gray-400 mt-0.5">{stat.sub}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
