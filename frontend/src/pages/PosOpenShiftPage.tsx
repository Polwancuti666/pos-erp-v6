import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function PosOpenShiftPage() {
  const navigate = useNavigate();
  const [openingCash, setOpeningCash] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [staff, setStaff] = useState<any>(null);
  const [existingShift, setExistingShift] = useState<any>(null);
  const [checkingShift, setCheckingShift] = useState(true);

  useEffect(() => {
    const s = JSON.parse(localStorage.getItem('pos_staff') || '{}');
    if (!s.id) {
      navigate('/login');
      return;
    }
    setStaff(s);
    checkExistingShift(s.id);
  }, []);

  async function checkExistingShift(staffId: string) {
    setCheckingShift(true);
    try {
      const res = await fetch(`/api/pos/shift/current?staff_id=${staffId}`);
      const data = await res.json();
      if (data.success && data.has_shift) {
        setExistingShift(data);
      }
    } catch {
      // ignore — will open new shift
    }
    setCheckingShift(false);
  }

  const handleContinueShift = () => {
    if (!existingShift) return;
    localStorage.setItem('pos_shift_id', existingShift.shift_id);
    localStorage.setItem('pos_shift_code', existingShift.shift_code || '');
    localStorage.setItem('pos_opening_cash', String(existingShift.opening_cash || 0));
    navigate('/');
  };

  const handleCloseAndOpen = async () => {
    if (!existingShift) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/pos/shift/close', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          shift_id: existingShift.shift_id,
          closing_cash: 0,
          notes: 'Auto-close for re-open',
        }),
      });
      const data = await res.json();
      if (data.success) {
        // Clear shift data
        localStorage.removeItem('pos_shift_id');
        localStorage.removeItem('pos_shift_code');
        localStorage.removeItem('pos_opening_cash');
        setExistingShift(null);
      } else {
        setError(data.message || 'Gagal menutup shift');
      }
    } catch {
      setError('Gagal terhubung ke server');
    }
    setLoading(false);
  };

  const handleOpenShift = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!staff) return;

    const cash = parseFloat(openingCash.replace(/[^0-9]/g, '')) || 0;
    if (cash < 0) {
      setError('Kas awal tidak boleh negatif');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/pos/shift/open`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          staff_id: staff.id,
          staff_name: staff.name,
          branch_code: localStorage.getItem('pos_branch_code') || staff.branch || 'HQ',
          branch_id: localStorage.getItem('pos_branch_id') || undefined,
          opening_cash: cash,
        }),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        setError(data.message || 'Gagal membuka shift');
        setLoading(false);
        return;
      }

      localStorage.setItem('pos_shift_id', data.shift_id);
      localStorage.setItem('pos_shift_code', data.shift_code);
      localStorage.setItem('pos_opening_cash', String(cash));

      navigate('/');
    } catch {
      setError('Gagal terhubung ke server');
    }
    setLoading(false);
  };

  const formatDisplay = (val: string) => {
    const num = parseFloat(val.replace(/[^0-9]/g, '')) || 0;
    return num > 0 ? `Rp ${num.toLocaleString('id-ID')}` : '';
  };

  if (checkingShift) {
    return (
      <div className="min-h-screen bg-[var(--ivory)] flex flex-col items-center justify-center px-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--gold)]"></div>
        <p className="text-sm text-gray-400 mt-4">Memeriksa shift...</p>
      </div>
    );
  }

  // If there's an existing shift, show options
  if (existingShift) {
    const openedAt = existingShift.opened_at ? new Date(existingShift.opened_at) : null;
    const isStale = openedAt ? (Date.now() - openedAt.getTime()) > 12 * 60 * 60 * 1000 : false;

    return (
      <div className="min-h-screen bg-[var(--ivory)] flex flex-col items-center justify-center px-4">
        <div className="mb-6 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--gold)] to-[var(--rose)] flex items-center justify-center text-white font-bold text-2xl shadow-lg mx-auto mb-3">
            B
          </div>
          <h1 className="text-xl font-bold text-[var(--charcoal)]">Shift Aktif</h1>
          <p className="text-sm text-gray-400 mt-1">
            {staff?.name} • {staff?.branch || 'HQ'}
          </p>
        </div>

        <div className="w-full max-w-sm space-y-4">
          {error && (
            <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-xl text-center">
              {error}
            </div>
          )}

          {/* Current shift info */}
          <div className={`rounded-xl p-4 border ${isStale ? 'bg-amber-50 border-amber-200' : 'bg-green-50 border-green-200'}`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">{isStale ? '⚠️' : '✅'}</span>
              <span className={`font-semibold text-sm ${isStale ? 'text-amber-700' : 'text-green-700'}`}>
                {existingShift.shift_code}
              </span>
            </div>
            <div className="text-xs text-gray-500 space-y-1">
              <p>🕐 Dibuka: {openedAt ? openedAt.toLocaleString('id-ID') : '-'}</p>
              <p>💵 Kas Awal: Rp {Number(existingShift.opening_cash || 0).toLocaleString('id-ID')}</p>
              <p>🧾 Transaksi: {existingShift.txn_count || 0}</p>
              <p>💰 Total Penjualan: Rp {Number(existingShift.total_sales || 0).toLocaleString('id-ID')}</p>
            </div>
            {isStale && (
              <p className="text-xs text-amber-600 mt-2 font-medium">
                Shift ini sudah aktif lebih dari 12 jam. Disarankan untuk tutup dan buka shift baru.
              </p>
            )}
          </div>

          {/* Action buttons */}
          <button
            onClick={handleContinueShift}
            className="w-full py-3.5 rounded-xl bg-[var(--gold)] text-white font-semibold text-base active:bg-[var(--gold)]/90 transition-colors shadow-sm"
          >
            ▶️ Lanjutkan Shift
          </button>

          <button
            onClick={handleCloseAndOpen}
            disabled={loading}
            className="w-full py-3.5 rounded-xl border-2 border-red-300 text-red-600 font-semibold text-base active:bg-red-50 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Menutup...' : '🔄 Tutup & Buka Shift Baru'}
          </button>

          <button
            onClick={() => navigate('/')}
            className="w-full py-2 text-sm text-gray-400 hover:text-gray-600 transition-colors"
          >
            ← Kembali ke Home
          </button>
        </div>
      </div>
    );
  }

  // No existing shift — show open shift form
  return (
    <div className="min-h-screen bg-[var(--ivory)] flex flex-col items-center justify-center px-4">
      {/* Logo */}
      <div className="mb-6 text-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--gold)] to-[var(--rose)] flex items-center justify-center text-white font-bold text-2xl shadow-lg mx-auto mb-3">
          B
        </div>
        <h1 className="text-xl font-bold text-[var(--charcoal)]">Buka Shift</h1>
        <p className="text-sm text-gray-400 mt-1">
          {staff?.name} • {staff?.branch || 'HQ'}
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleOpenShift} className="w-full max-w-sm space-y-5">
        {error && (
          <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-xl text-center">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-600 mb-2">
            💵 Kas Awal (Uang di Laci)
          </label>
          <input
            type="text"
            inputMode="numeric"
            value={openingCash}
            onChange={(e) => setOpeningCash(e.target.value.replace(/[^0-9]/g, ''))}
            placeholder="0"
            className="w-full px-4 py-4 rounded-xl border border-gray-200 bg-white text-[var(--charcoal)] text-center text-3xl font-bold font-mono focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
          />
          {openingCash && (
            <p className="text-center text-sm text-gray-400 mt-1">
              {formatDisplay(openingCash)}
            </p>
          )}
        </div>

        {/* Quick presets */}
        <div className="grid grid-cols-3 gap-2">
          {[100000, 200000, 500000].map((val) => (
            <button
              key={val}
              type="button"
              onClick={() => setOpeningCash(String(val))}
              className="py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-gray-600 active:bg-gray-50 transition-colors"
            >
              Rp {val.toLocaleString('id-ID')}
            </button>
          ))}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3.5 rounded-xl bg-[var(--gold)] text-white font-semibold text-base active:bg-[var(--gold)]/90 disabled:opacity-50 transition-colors shadow-sm"
        >
          {loading ? (
            <span className="inline-flex items-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Membuka Shift...
            </span>
          ) : (
            '🔓 Buka Shift'
          )}
        </button>
      </form>

      <p className="text-xs text-gray-300 mt-8">
        Masukkan jumlah uang tunai yang ada di laci kasir
      </p>
    </div>
  );
}
