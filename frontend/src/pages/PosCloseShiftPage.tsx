import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';



interface ShiftSummary {
  shift_code: string;
  opening_cash: number;
  txn_count: number;
  total_sales: number;
  cash_sales: number;
  qris_sales: number;
  transfer_sales: number;
  treatment_count: number;
  treatment_sales: number;
}

export default function PosCloseShiftPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<ShiftSummary | null>(null);
  const [closingCash, setClosingCash] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [staff, setStaff] = useState<any>(null);

  useEffect(() => {
    const s = JSON.parse(localStorage.getItem('pos_staff') || '{}');
    if (!s.id) {
      navigate('/login');
      return;
    }
    setStaff(s);
    loadSummary(s.id);
  }, []);

  async function loadSummary(staffId: string) {
    setFetching(true);
    try {
      const res = await fetch(`/api/pos/shift/current?staff_id=${staffId}`);
      const data = await res.json();
      if (!data.success || !data.has_shift) {
        setError('Tidak ada shift yang aktif');
        setFetching(false);
        return;
      }
      setSummary({
        shift_code: data.shift_code,
        opening_cash: data.opening_cash,
        txn_count: data.txn_count,
        total_sales: data.total_sales,
        cash_sales: data.cash_sales,
        qris_sales: data.qris_sales,
        transfer_sales: data.transfer_sales,
        treatment_count: data.treatment_count,
        treatment_sales: data.treatment_sales,
      });
    } catch {
      setError('Gagal memuat data shift');
    }
    setFetching(false);
  }

  const expectedCash = summary ? summary.opening_cash + summary.cash_sales : 0;
  const closingNum = parseFloat(closingCash.replace(/[^0-9]/g, '')) || 0;
  const variance = closingNum - expectedCash;

  const handleClose = async (e: React.FormEvent) => {
    e.preventDefault();
    const shiftId = localStorage.getItem('pos_shift_id');
    if (!shiftId) {
      setError('Shift ID tidak ditemukan');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/pos/shift/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          shift_id: shiftId,
          closing_cash: closingNum,
          notes,
        }),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        setError(data.message || 'Gagal menutup shift');
        setLoading(false);
        return;
      }

      setResult(data);
      // Clear shift from localStorage
      localStorage.removeItem('pos_shift_id');
      localStorage.removeItem('pos_shift_code');
      localStorage.removeItem('pos_opening_cash');
    } catch {
      setError('Gagal terhubung ke server');
    }
    setLoading(false);
  };

  const fmt = (n: number) => `Rp ${(n || 0).toLocaleString('id-ID')}`;

  // Result screen
  if (result) {
    const s = result.summary;
    return (
      <div className="min-h-screen bg-[var(--ivory)] flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-sm space-y-4 text-center">
          <div className="text-5xl mb-2">✅</div>
          <h1 className="text-xl font-bold text-[var(--charcoal)]">Shift Ditutup</h1>
          <p className="text-sm text-gray-400">{result.shift_code}</p>

          <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm text-left space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Kas Awal</span>
              <span className="font-medium">{fmt(s.opening_cash)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Total Penjualan</span>
              <span className="font-medium">{fmt(s.total_sales)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">💵 Tunai</span>
              <span className="font-medium">{fmt(s.cash_sales)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">🧾 QRIS</span>
              <span className="font-medium">{fmt(s.qris_sales)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">🏦 Transfer</span>
              <span className="font-medium">{fmt(s.transfer_sales)}</span>
            </div>
            {s.treatment_count > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">💆 Treatment ({s.treatment_count}x)</span>
                <span className="font-medium">{fmt(s.treatment_sales)}</span>
              </div>
            )}
            <hr />
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Transaksi</span>
              <span className="font-medium">{s.transaction_count}x</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Kas Seharusnya</span>
              <span className="font-medium">{fmt(s.expected_cash)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Kas Aktual</span>
              <span className="font-medium">{fmt(s.closing_cash)}</span>
            </div>
            <hr />
            <div className="flex justify-between">
              <span className="font-semibold">Variance</span>
              <span className={`font-bold text-lg ${Math.abs(s.variance) < 1000 ? 'text-green-600' : s.variance > 0 ? 'text-blue-600' : 'text-red-600'}`}>
                {s.variance >= 0 ? '+' : ''}{fmt(s.variance)}
              </span>
            </div>
          </div>

          <button
            onClick={() => {
              localStorage.removeItem('pos_token');
              localStorage.removeItem('pos_staff');
              navigate('/login');
            }}
            className="w-full py-3.5 rounded-xl bg-[var(--gold)] text-white font-semibold text-base"
          >
            Kembali ke Login
          </button>
        </div>
      </div>
    );
  }

  // Loading state
  if (fetching) {
    return (
      <div className="min-h-screen bg-[var(--ivory)] flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-4 border-[var(--gold)] border-t-transparent rounded-full" />
      </div>
    );
  }

  // Close shift form
  return (
    <div className="min-h-screen bg-[var(--ivory)] pb-8">
      {/* Header */}
      <div className="sticky top-0 bg-[var(--ivory)] z-10 px-4 pt-4 pb-3">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-gray-500 text-xl">←</button>
          <div>
            <h1 className="text-lg font-bold text-[var(--charcoal)]">Tutup Shift</h1>
            <p className="text-xs text-gray-400">{summary?.shift_code} • {staff?.name}</p>
          </div>
        </div>
      </div>

      <div className="px-4 space-y-4">
        {error && (
          <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-xl">
            {error}
          </div>
        )}

        {/* Summary Card */}
        {summary && (
          <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
            <h3 className="font-semibold text-[var(--charcoal)] mb-3">📊 Ringkasan Shift</h3>
            <div className="space-y-2.5">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Kas Awal</span>
                <span className="font-medium">{fmt(summary.opening_cash)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Transaksi</span>
                <span className="font-medium">{summary.txn_count}x</span>
              </div>
              <hr />
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">💵 Tunai</span>
                <span className="font-medium">{fmt(summary.cash_sales)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">🧾 QRIS</span>
                <span className="font-medium">{fmt(summary.qris_sales)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">🏦 Transfer</span>
                <span className="font-medium">{fmt(summary.transfer_sales)}</span>
              </div>
              {summary.treatment_count > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">💆 Treatment ({summary.treatment_count}x)</span>
                  <span className="font-medium">{fmt(summary.treatment_sales)}</span>
                </div>
              )}
              <hr />
              <div className="flex justify-between">
                <span className="text-sm font-semibold">Total Penjualan</span>
                <span className="font-bold">{fmt(summary.total_sales)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Expected Cash */}
        <div className="bg-amber-50 rounded-2xl p-4 border border-amber-200 text-center">
          <p className="text-xs text-amber-600 mb-1">Uang Tunai Seharusnya di Laci</p>
          <p className="text-2xl font-bold text-amber-700">{fmt(expectedCash)}</p>
          <p className="text-xs text-amber-500 mt-1">
            Kas Awal {fmt(summary?.opening_cash || 0)} + Tunai {fmt(summary?.cash_sales || 0)}
          </p>
        </div>

        {/* Input Closing Cash */}
        <form onSubmit={handleClose} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-2">
              💵 Hitung Uang di Laci
            </label>
            <input
              type="text"
              inputMode="numeric"
              value={closingCash}
              onChange={(e) => setClosingCash(e.target.value.replace(/[^0-9]/g, ''))}
              placeholder="0"
              required
              className="w-full px-4 py-4 rounded-xl border border-gray-200 bg-white text-[var(--charcoal)] text-center text-3xl font-bold font-mono focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            />
            {closingNum > 0 && (
              <p className="text-center text-sm text-gray-400 mt-1">
                {fmt(closingNum)}
              </p>
            )}
          </div>

          {/* Variance indicator */}
          {closingNum > 0 && (
            <div className={`rounded-xl p-3 text-center text-sm font-medium ${Math.abs(variance) < 1000 ? 'bg-green-50 text-green-700' : variance > 0 ? 'bg-blue-50 text-blue-700' : 'bg-red-50 text-red-700'}`}>
              {Math.abs(variance) < 1000
                ? `✅ Sesuai (selisih ${fmt(Math.abs(variance))})`
                : `${variance > 0 ? '📈 Lebih' : '📉 Kurang'} ${fmt(Math.abs(variance))}`
              }
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Catatan (opsional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Catatan shift hari ini..."
              rows={2}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent resize-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading || closingNum === 0}
            className="w-full py-3.5 rounded-xl bg-red-500 text-white font-semibold text-base active:bg-red-600 disabled:opacity-50 transition-colors shadow-sm"
          >
            {loading ? 'Menutup Shift...' : '🔒 Tutup Shift'}
          </button>
        </form>
      </div>
    </div>
  );
}
