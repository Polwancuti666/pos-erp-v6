import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api } from '../api/client';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: '📊', desc: 'KPI & Monitoring' },
  { to: '/master', label: 'Master Data', icon: '📋', desc: 'Produk, Treatment, COA', children: [
    { to: '/master/treatment', label: '💆 Treatments', icon: '💆', desc: 'Layanan & Perawatan' },
    { to: '/master/product', label: '🧴 Products', icon: '🧴', desc: 'Produk & Stok' },
    { to: '/master/branch', label: '🏢 Branches', icon: '🏢', desc: 'Cabang Bisnis' },
    { to: '/master/user', label: '👩 Users', icon: '👩', desc: 'Pengguna & Akses' },
    { to: '/master/customer', label: '👥 Customers', icon: '👥', desc: 'Data Pelanggan' },
    { to: '/master/coa', label: '📒 Chart of Accounts', icon: '📒', desc: 'Kode Akun' },
    { to: '/master/voucher', label: '🎫 Vouchers', icon: '🎫', desc: 'Voucher & Kupon' },
    { to: '/master/promo', label: '🏷️ Promos', icon: '🏷️', desc: 'Promosi & Diskon' },
    { to: '/master/treatment-category', label: '📂 Treatment Category', icon: '📂', desc: 'Kategori Treatment' },
    { to: '/master/treatment-subcategory', label: '📂 Treatment Subcategory', icon: '📂', desc: 'Subkategori Treatment' },
    { to: '/master/product-category', label: '📦 Product Category', icon: '📦', desc: 'Kategori Produk' },
    { to: '/master/product-subcategory', label: '📦 Product Subcategory', icon: '📦', desc: 'Subkategori Produk' },
  ]},
  { to: '/inventory', label: 'Inventory', icon: '📦', desc: 'Stok, BOM, Opname' },
  { to: '/finance', label: 'Finance', icon: '💰', desc: 'Journal, GL, AP, Bank' },
  { to: '/accounting', label: 'Accounting', icon: '📒', desc: 'COA Upload & Management', children: [
    { to: '/coa-upload', label: 'COA Upload', icon: '📤', desc: 'Upload Chart of Accounts' },
    { to: '/coa-management', label: 'COA Management', icon: '📊', desc: 'Kelola Akun & Mapping' },
  ]},
  { to: '/reporting', label: 'Laporan', icon: '📈', desc: 'Sales, Inventory, Finance' },
  { to: '/period', label: 'Periode', icon: '📅', desc: 'Lock & Closing' },
  { to: '/exceptions', label: 'Exception', icon: '⚠️', desc: 'Penanganan Masalah' },
  { to: '/operations', label: 'Operations', icon: '⚙️', desc: 'WIP, Schedule, Pricelist, Settlement' },
];

function NavGroup({ item }: { item: typeof NAV_ITEMS[number] }) {
  const location = useLocation();
  const hasChildren = 'children' in item && item.children;
  const isExpanded = hasChildren && item.children!.some(c => location.pathname.startsWith(c.to));
  const [open, setOpen] = useState(isExpanded);

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all ${
          isExpanded ? 'text-gray-900 font-semibold' : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
        }`}
      >
        <span className="text-lg w-7 text-center">{item.icon}</span>
        <div className="flex-1 text-left">
          <div>{item.label}</div>
          <div className="text-[10px] text-gray-400 font-normal">{item.desc}</div>
        </div>
        <svg className={`w-4 h-4 transition-transform ${open ? 'rotate-90' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
      {open && hasChildren && (
        <div className="ml-4 mt-0.5 space-y-0.5 border-l-2 border-gray-100 pl-3">
          {item.children!.map(child => (
            <NavLink
              key={child.to}
              to={child.to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all ${
                  isActive
                    ? 'bg-[#C9A96E]/10 text-gray-900 font-medium'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <span className="text-base w-5 text-center">{child.icon}</span>
              <span>{child.label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

function MobileNavGroup({ item, onClose }: { item: typeof NAV_ITEMS[number]; onClose: () => void }) {
  const location = useLocation();
  const hasChildren = 'children' in item && item.children;
  const isExpanded = hasChildren && item.children!.some(c => location.pathname.startsWith(c.to));
  const [open, setOpen] = useState(isExpanded);

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-sm transition-all ${
          isExpanded ? 'text-gray-900 font-semibold' : 'text-gray-500 hover:bg-gray-50'
        }`}
      >
        <span className="text-xl w-8 text-center">{item.icon}</span>
        <div className="flex-1 text-left">
          <div>{item.label}</div>
          <div className="text-[11px] text-gray-400 font-normal">{item.desc}</div>
        </div>
        <svg className={`w-4 h-4 transition-transform ${open ? 'rotate-90' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
      {open && hasChildren && (
        <div className="ml-4 mt-0.5 space-y-0.5 border-l-2 border-gray-100 pl-3">
          {item.children!.map(child => (
            <NavLink
              key={child.to}
              to={child.to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-all ${
                  isActive
                    ? 'bg-[#C9A96E]/10 text-gray-900 font-medium'
                    : 'text-gray-500 hover:bg-gray-50'
                }`
              }
            >
              <span className="text-base w-5 text-center">{child.icon}</span>
              <span>{child.label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

function BranchSelector() {
  const [branches, setBranches] = useState<any[]>([]);
  const [selected, setSelected] = useState(localStorage.getItem('erp_branch_id') || 'all');

  useEffect(() => {
    api.getBranches()
      .then((res: any) => setBranches(Array.isArray(res) ? res : res.items || []))
      .catch(() => setBranches([]));
  }, []);

  const changeBranch = (branchId: string) => {
    setSelected(branchId);
    localStorage.setItem('erp_branch_id', branchId);
    window.dispatchEvent(new CustomEvent('branch-changed', { detail: { branchId } }));
    // Existing pages mostly fetch on mount; reload gives consistent cross-page branch isolation.
    window.location.reload();
  };

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-400">Cabang</span>
      <select
        value={selected}
        onChange={(e) => changeBranch(e.target.value)}
        className="border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-700 text-xs focus:ring-2 focus:ring-[#C9A96E] focus:border-transparent"
      >
        <option value="all">Semua Cabang</option>
        {branches.map((b: any) => (
          <option key={b.id} value={b.id}>{b.code ? `${b.code} — ${b.name}` : b.name}</option>
        ))}
      </select>
    </div>
  );
}

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  function handleLogout() {
    localStorage.removeItem('erp_token');
    navigate('/login');
  }

  const currentNav = NAV_ITEMS.find(n => {
    if (n.to === '/') return location.pathname === '/app' || location.pathname === '/app/';
    if ('children' in n && n.children) {
      return n.children.some(c => location.pathname.startsWith(c.to));
    }
    return location.pathname.startsWith(n.to);
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Desktop Sidebar (≥768px) ── */}
      <aside className="hidden md:flex fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-100 flex-col z-40">
        {/* Logo */}
        <div className="h-16 flex items-center gap-3 px-5 border-b border-gray-100">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#C9A96E] to-[#C08081] flex items-center justify-center text-white font-bold text-sm shadow-sm">
            B
          </div>
          <div>
            <h1 className="font-bold text-gray-900 text-sm leading-tight">Beauty & Shine</h1>
            <p className="text-[10px] text-gray-400">ERP System v6</p>
          </div>
        </div>

        {/* Nav Links */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map(item => (
            item.children ? (
              <NavGroup key={item.to} item={item} />
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-[#C9A96E]/10 to-transparent text-gray-900 font-semibold shadow-sm'
                      : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                  }`
                }
              >
                <span className="text-lg w-7 text-center">{item.icon}</span>
                <div>
                  <div>{item.label}</div>
                  <div className="text-[10px] text-gray-400 font-normal">{item.desc}</div>
                </div>
              </NavLink>
            )
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-100">
          <div className="flex items-center gap-3 px-2">
            <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 text-xs">
              👤
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-gray-900 truncate">Admin</div>
              <div className="text-[10px] text-gray-400">Branch-aware</div>
            </div>
            <button
              onClick={handleLogout}
              title="Logout"
              className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* ── Mobile Header ── */}
      <header className="md:hidden fixed top-0 inset-x-0 h-14 bg-white border-b border-gray-100 flex items-center justify-between px-4 z-50">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 -ml-2 rounded-lg hover:bg-gray-50"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {sidebarOpen ? (
              <path d="M18 6L6 18M6 6l12 12" />
            ) : (
              <path d="M3 12h18M3 6h18M3 18h18" />
            )}
          </svg>
        </button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#C9A96E] to-[#C08081] flex items-center justify-center text-white font-bold text-xs shadow-sm">
            B
          </div>
          <span className="font-semibold text-gray-900 text-sm">Beauty & Shine</span>
        </div>
        <div className="scale-90 origin-right"><BranchSelector /></div>
      </header>

      {/* ── Mobile Slide-over Menu ── */}
      {sidebarOpen && (
        <>
          <div
            className="md:hidden fixed inset-0 bg-black/20 z-40 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="md:hidden fixed top-14 left-0 w-72 h-[calc(100vh-3.5rem)] bg-white border-r border-gray-100 z-50 animate-slide-in shadow-xl">
            <nav className="py-3 px-3 space-y-0.5">
              {NAV_ITEMS.map(item => (
                item.children ? (
                  <MobileNavGroup key={item.to} item={item} onClose={() => setSidebarOpen(false)} />
                ) : (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/'}
                    onClick={() => setSidebarOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-3 rounded-xl text-sm transition-all ${
                        isActive
                          ? 'bg-[#C9A96E]/10 text-gray-900 font-semibold'
                          : 'text-gray-500 hover:bg-gray-50'
                      }`
                    }
                  >
                    <span className="text-xl w-8 text-center">{item.icon}</span>
                    <div>
                      <div>{item.label}</div>
                      <div className="text-[11px] text-gray-400 font-normal">{item.desc}</div>
                    </div>
                  </NavLink>
                )
              ))}
            </nav>
          </div>
        </>
      )}

      {/* ── Main Content ── */}
      <main className="md:ml-64 pt-14 md:pt-0 min-h-screen">
        {/* Desktop Topbar */}
        <div className="hidden md:flex h-14 items-center justify-between px-6 bg-white border-b border-gray-100 sticky top-0 z-30">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <span className="text-gray-300">/</span>
            <span className="font-medium text-gray-900">{currentNav?.label || 'Dashboard'}</span>
          </div>
          <div className="flex items-center gap-4">
            <BranchSelector />
            <div className="text-xs text-gray-400">ERP System v6</div>
            <span className="text-xs font-medium text-gray-600">Admin</span>
            <button
              onClick={handleLogout}
              className="px-3 py-1.5 rounded-lg text-xs font-medium text-gray-500 hover:text-red-500 hover:bg-red-50 transition border border-gray-200 hover:border-red-200"
            >
              Logout
            </button>
          </div>
        </div>

        <div className="p-4 md:p-6">
          <Outlet />
        </div>
      </main>

      {/* ── Mobile Bottom Nav ── */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-white/95 backdrop-blur-lg border-t border-gray-100 flex justify-around items-center h-16 z-50 pb-[env(safe-area-inset-bottom)]">
        {NAV_ITEMS.filter(n => n.to !== '/').slice(0, 5).map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-0.5 py-1 px-2 rounded-lg transition-colors ${
                isActive ? 'text-[#C9A96E]' : 'text-gray-400'
              }`
            }
          >
            <span className="text-lg">{item.icon}</span>
            <span className="text-[10px] font-medium">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
