import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import Modal from './common/Modal';
import OfflineIndicator from './OfflineIndicator';

const NAV_ITEMS = [
  { to: '/', label: 'Home', icon: HomeIcon },
  { to: '/kasir', label: 'Kasir', icon: KasirIcon },
  { to: '/booking', label: 'Booking', icon: BookingIcon },
  { to: '/closing', label: 'Closing', icon: ClosingIcon },
  { to: '/more', label: 'Lainnya', icon: MoreIcon },
];

function HomeIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#C9A96E' : '#9CA3AF'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  );
}

function KasirIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#C9A96E' : '#9CA3AF'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
      <line x1="3" y1="6" x2="21" y2="6" />
      <path d="M16 10a4 4 0 01-8 0" />
    </svg>
  );
}

function BookingIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#C9A96E' : '#9CA3AF'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
      <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" />
    </svg>
  );
}

function ClosingIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#C9A96E' : '#9CA3AF'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
      <path d="M6 8h.01M10 8h.01" />
      <line x1="14" y1="8" x2="18" y2="8" />
      <path d="M6 11h.01M10 11h.01" />
      <line x1="14" y1="11" x2="18" y2="11" />
    </svg>
  );
}

function MoreIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#C9A96E' : '#9CA3AF'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="1" />
      <circle cx="12" cy="5" r="1" />
      <circle cx="12" cy="19" r="1" />
    </svg>
  );
}

const MORE_ITEMS = [
  { to: '/voucher', label: 'Voucher & Promo', icon: '🎟️' },
  { to: '/treatment-record', label: 'Catatan Treatment', icon: '📋' },
  { to: '/receipt', label: 'Riwayat Struk', icon: '🧾' },
  { to: '/open-shift', label: 'Buka Shift Baru', icon: '🔓' },
  { to: '/close-shift', label: 'Tutup Shift', icon: '🔒' },
];

function PosBranchSelector() {
  const [branches, setBranches] = useState<any[]>([]);
  const [selected, setSelected] = useState(localStorage.getItem('pos_branch_id') || '');

  useEffect(() => {
    api.getBranches()
      .then((res: any) => {
        const list = Array.isArray(res) ? res : res.items || [];
        setBranches(list);
        if (!selected && list.length > 0) {
          localStorage.setItem('pos_branch_id', list[0].id);
          setSelected(list[0].id);
        }
      })
      .catch(() => setBranches([]));
  }, []);

  const changeBranch = (branchId: string) => {
    setSelected(branchId);
    localStorage.setItem('pos_branch_id', branchId);
    window.dispatchEvent(new CustomEvent('branch-changed', { detail: { branchId } }));
    window.location.reload();
  };

  return (
    <select
      value={selected}
      onChange={(e) => changeBranch(e.target.value)}
      className="max-w-[128px] border border-gray-200 rounded-lg px-2 py-1 bg-white text-[11px] text-gray-600 focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
      title="Pilih cabang POS"
    >
      {branches.map((b: any) => (
        <option key={b.id} value={b.id}>{b.code || b.name}</option>
      ))}
    </select>
  );
}

export default function PosLayout() {
  const location = useLocation();
  const [showMore, setShowMore] = useState(false);

  const staff = (() => {
    try {
      return JSON.parse(localStorage.getItem('pos_staff') || '{}');
    } catch {
      return {};
    }
  })();

  return (
    <div className="min-h-screen bg-[var(--ivory)]">
      <OfflineIndicator />
      {/* ── Header ── */}
      <header className="fixed top-0 inset-x-0 h-14 bg-white border-b border-gray-100 flex items-center justify-between px-4 z-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--gold)] to-[var(--rose)] flex items-center justify-center text-white font-bold text-xs shadow-sm">
            B
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-[var(--charcoal)] text-sm leading-tight">Beauty & Shine</span>
            <span className="text-[10px] text-gray-400 leading-tight">{staff.name || 'Kasir'}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <PosBranchSelector />
          <div className="w-2 h-2 rounded-full bg-green-400" />
          <span className="text-xs text-gray-400">Online</span>
        </div>
      </header>

      {/* ── Main Content ── */}
      <main className="pt-14 pb-20 min-h-screen">
        <Outlet />
      </main>

      {/* ── Bottom Navigation ── */}
      <nav className="fixed bottom-0 inset-x-0 h-16 bg-white border-t border-gray-100 flex items-center justify-around z-50 safe-area-pb">
        {NAV_ITEMS.map((item) => {
          const isActive = item.to === '/'
            ? location.pathname === '/'
            : location.pathname.startsWith(item.to);
          const Icon = item.icon;

          if (item.to === '/more') {
            return (
              <button
                key={item.to}
                onClick={() => setShowMore(true)}
                className="flex flex-col items-center justify-center gap-0.5 py-1 min-w-[56px]"
              >
                <Icon active={showMore} />
                <span className={`text-[10px] leading-tight ${showMore ? 'text-[var(--gold)] font-medium' : 'text-gray-400'}`}>
                  {item.label}
                </span>
              </button>
            );
          }

          return (
            <NavLink
              key={item.to}
              to={item.to}
              className="flex flex-col items-center justify-center gap-0.5 py-1 min-w-[56px]"
            >
              <Icon active={isActive} />
              <span className={`text-[10px] leading-tight ${isActive ? 'text-[var(--gold)] font-medium' : 'text-gray-400'}`}>
                {item.label}
              </span>
            </NavLink>
          );
        })}
      </nav>

      {/* ── More Menu Modal ── */}
      <Modal open={showMore} onClose={() => setShowMore(false)} title="Menu Lainnya">
        <div className="space-y-1">
          {MORE_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setShowMore(false)}
              className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-gray-50 transition-colors"
            >
              <span className="text-xl">{item.icon}</span>
              <span className="text-sm font-medium text-[var(--charcoal)]">{item.label}</span>
              <svg className="w-4 h-4 ml-auto text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </NavLink>
          ))}
          <div className="border-t border-gray-100 my-2" />
          <button
            onClick={() => {
              localStorage.removeItem('pos_token');
              localStorage.removeItem('pos_staff');
              localStorage.removeItem('pos_shift_id');
              window.location.href = '/app/login';
            }}
            className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-red-50 transition-colors w-full text-left"
          >
            <span className="text-xl">🚪</span>
            <span className="text-sm font-medium text-red-500">Keluar</span>
          </button>
        </div>
      </Modal>
    </div>
  );
}
