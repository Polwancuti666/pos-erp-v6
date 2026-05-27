import { Outlet, NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/checkout', label: 'Kasir', icon: '🛒' },
  { to: '/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/exceptions', label: 'Exception', icon: '⚠️' },
  { to: '/coa', label: 'COA', icon: '📋' },
  { to: '/closing', label: 'Closing', icon: '🔒' },
];

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-ivory">
      {/* Top Nav */}
      <header className="bg-white border-b border-gray-100 px-4 h-14 flex items-center justify-between sticky top-0 z-50">
        <h1 className="font-semibold text-charcoal text-lg">Beauty & Shine</h1>
        <span className="text-xs text-gray-400">POS-ERP V6</span>
      </header>

      {/* Main Content */}
      <main className="flex-1 pb-20 overflow-auto">
        <Outlet />
      </main>

      {/* Bottom Nav (Mobile) */}
      <nav className="fixed bottom-0 inset-x-0 bg-white border-t border-gray-100 flex justify-around items-center h-16 z-50 safe-area-bottom">
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-0.5 text-xs py-1 px-2 rounded-lg transition-colors ${
                isActive ? 'text-gold font-semibold' : 'text-gray-400'
              }`
            }
          >
            <span className="text-xl">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
