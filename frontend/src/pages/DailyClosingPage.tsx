import { useState, useEffect } from 'react';
import { closingApi } from '@/api/client';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';

type Step = 'summary' | 'count' | 'confirm' | 'done';

const VARIANCE_REASONS = [
  'Salah kembalian',
  'Kehilangan',
  'Selisih kecil (<Rp 1.000)',
  'Koreksi kasir',
  'Lainnya',
];

interface ClosingSummary {
  branch_code: string;
  business_date: string;
  operational_sales: string;
  counted_cash: string;
  pending_queued_transactions: number;
  variance_amount: string;
  variance_percent: string;
  status: string;
  reason_code: string | null;
}

export default function DailyClosingPage() {
  const [step, setStep] = useState<Step>('summary');
  const [summary, setSummary] = useState<ClosingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [cashCounted, setCashCounted] = useState('');
  const [varianceReason, setVarianceReason] = useState('');
  const [varianceNote, setVarianceNote] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);
  const [submitResult, setSubmitResult] = useState<any>(null);

  const today = new Date().toISOString().split('T')[0];
  const fmt = (n: string | number) => {
    const num = typeof n === 'string' ? parseFloat(n) : n;
    if (isNaN(num)) return 'Rp 0';
    return 'Rp ' + num.toLocaleString('id-ID');
  };

  useEffect(() => { loadSummary(); }, []);

  const loadSummary = async () => {
    setLoading(true);
    try {
      const data = await closingApi.summary(`date=${today}&branch=HQ`);
      setSummary(data);
    } catch { /* empty */ }
    setLoading(false);
  };

  const salesAmount = summary ? parseFloat(summary.operational_sales) || 0 : 0;
  const cashExpected = salesAmount; // Simplified — in real app would be cash-only sales
  const cashCount = parseInt(cashCounted.replace(/[^0-9]/g, ''), 10) || 0;
  const variance = cashExpected - cashCount;
  const absVariance = Math.abs(variance);

  const handleSubmit = async () => {
    if (!summary) return;
    setLoading(true);
    try {
      const result = await closingApi.submit({
        date: today,
        branchCode: 'HQ',
        cashCounted: cashCount,
        varianceReason,
        varianceNote: varianceReason === 'Lainnya' ? varianceNote : undefined,
      });
      setSubmitResult(result);
      setStep('done');
    } catch { alert('Gagal submit closing'); }
    setLoading(false);
    setShowConfirm(false);
  };

  if (loading && !summary) return <div className="p-4"><LoadingSkeleton rows={6} /></div>;
  if (!summary) return <div className="p-4 text-center text-gray-500">Gagal memuat data closing</div>;

  // ── Done ──
  if (step === 'done' && submitResult) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="text-center py-8">
          <div className="text-6xl mb-4">🔒</div>
          <h2 className="text-2xl font-bold text-[var(--charcoal)] mb-2">Closing Berhasil</h2>
          <p className="text-gray-500">{today} — Cabang HQ</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-4 space-y-3">
          <div className="flex justify-between"><span className="text-gray-500">Total Sales</span><span className="font-semibold">{fmt(salesAmount)}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Kas Dihitung</span><span className="font-semibold">{fmt(cashCount)}</span></div>
          <hr />
          <div className="flex justify-between"><span className="text-gray-500">Selisih</span><span className={variance !== 0 ? 'text-red-600 font-semibold' : 'text-green-600'}>{fmt(variance)}</span></div>
          {varianceReason && <div className="flex justify-between"><span className="text-gray-500">Alasan</span><span>{varianceReason}</span></div>}
        </div>

        <button onClick={() => { setStep('summary'); loadSummary(); }} className="w-full bg-gray-100 text-[var(--charcoal)] py-3 rounded-xl font-medium">
          Kembali
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-[var(--charcoal)]">Daily Closing</h2>
      <p className="text-sm text-gray-500">{today} — Cabang {summary.branch_code}</p>

      {/* Step 1: Summary */}
      {step === 'summary' && (
        <div className="space-y-3 animate-fade-in">
          <div className="bg-white rounded-xl border border-gray-100 p-4 space-y-3">
            <h3 className="font-semibold text-[var(--charcoal)]">Ringkasan Hari Ini</h3>
            <div className="flex justify-between"><span className="text-gray-500">Operational Sales</span><span className="font-semibold">{fmt(summary.operational_sales)}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Status</span><span className={`font-medium ${summary.status === 'ALLOWED' ? 'text-green-600' : 'text-red-600'}`}>{summary.status}</span></div>
            {summary.pending_queued_transactions > 0 && (
              <div className="flex justify-between"><span className="text-gray-500">Pending Sync</span><span className="text-yellow-600">{summary.pending_queued_transactions}</span></div>
            )}
          </div>

          {/* Blockers */}
          {summary.status === 'BLOCKED' && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <p className="text-red-700 font-medium">⚠ Closing diblokir</p>
              <p className="text-sm text-red-600">{summary.reason_code || 'Ada masalah yang harus diselesaikan'}</p>
            </div>
          )}

          {summary.pending_queued_transactions > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
              <p className="text-yellow-700 text-sm">Ada {summary.pending_queued_transactions} transaksi pending. Closing tetap bisa dilakukan.</p>
            </div>
          )}

          <button
            onClick={() => setStep('count')}
            disabled={summary.status === 'BLOCKED'}
            className="w-full bg-[var(--gold)] text-white py-4 rounded-xl font-semibold text-lg disabled:opacity-40 disabled:cursor-not-allowed active:bg-[var(--gold)]/90"
          >
            Lanjut Hitung Kas
          </button>
        </div>
      )}

      {/* Step 2: Cash Count */}
      {step === 'count' && (
        <div className="space-y-4 animate-fade-in">
          <div className="bg-[var(--ivory-warm)] rounded-xl p-4 text-center">
            <p className="text-sm text-gray-500 mb-1">Kas Expected</p>
            <p className="text-2xl font-bold text-[var(--charcoal)]">{fmt(cashExpected)}</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <label className="text-sm text-gray-500 block mb-2">Kas Dihitung (Fisik)</label>
            <input
              type="text"
              inputMode="numeric"
              value={cashCounted}
              onChange={e => setCashCounted(e.target.value)}
              placeholder="0"
              className="w-full text-2xl font-bold text-[var(--charcoal)] text-center outline-none bg-transparent"
            />
          </div>

          {cashCount > 0 && (
            <div className={`rounded-xl p-4 text-center ${variance === 0 ? 'bg-green-50' : 'bg-red-50'}`}>
              <p className="text-sm text-gray-500 mb-1">Selisih</p>
              <p className={`text-xl font-bold ${variance === 0 ? 'text-green-600' : 'text-red-600'}`}>
                {variance > 0 ? '+' : ''}{fmt(variance)}
              </p>
            </div>
          )}

          {absVariance > 50000 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
              Selisih kas di atas Rp 50.000. Memerlukan approval Owner.
            </div>
          )}

          <button
            onClick={() => setStep('confirm')}
            disabled={cashCount === 0}
            className="w-full bg-[var(--gold)] text-white py-4 rounded-xl font-semibold text-lg disabled:opacity-40 active:bg-[var(--gold)]/90"
          >
            Lanjut Konfirmasi
          </button>
        </div>
      )}

      {/* Step 3: Confirm */}
      {step === 'confirm' && (
        <div className="space-y-4 animate-fade-in">
          {absVariance > 0 && (
            <div className="space-y-3">
              <label className="text-sm font-medium text-[var(--charcoal)]">Alasan Selisih *</label>
              <select
                value={varianceReason}
                onChange={e => setVarianceReason(e.target.value)}
                className="w-full p-3 border border-gray-200 rounded-xl bg-white text-[var(--charcoal)]"
              >
                <option value="">Pilih alasan...</option>
                {VARIANCE_REASONS.map(r => <option key={r} value={r}>{r}</option>)}
              </select>

              {varianceReason === 'Lainnya' && (
                <textarea
                  value={varianceNote}
                  onChange={e => setVarianceNote(e.target.value)}
                  placeholder="Jelaskan alasan..."
                  className="w-full p-3 border border-gray-200 rounded-xl bg-white text-[var(--charcoal)] h-24 resize-none"
                />
              )}
            </div>
          )}

          <button
            onClick={() => setShowConfirm(true)}
            disabled={absVariance > 0 && !varianceReason}
            className="w-full bg-[var(--charcoal)] text-white py-4 rounded-xl font-semibold text-lg disabled:opacity-40 active:bg-[var(--charcoal)]/90"
          >
            Konfirmasi Closing
          </button>
        </div>
      )}

      {/* Confirm Modal */}
      {showConfirm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full space-y-4">
            <h3 className="text-lg font-bold text-[var(--charcoal)]">Konfirmasi Closing</h3>
            <p className="text-gray-600">Closing tidak bisa diubah setelah dikonfirmasi.</p>
            <p className="font-medium text-[var(--charcoal)]">Kas: {fmt(cashCount)} | Selisih: {fmt(absVariance)}</p>
            <div className="flex gap-3">
              <button onClick={() => setShowConfirm(false)} className="flex-1 py-3 bg-gray-100 rounded-xl font-medium">
                Batal
              </button>
              <button onClick={handleSubmit} className="flex-1 py-3 bg-[var(--charcoal)] text-white rounded-xl font-medium">
                Ya, Closing
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
