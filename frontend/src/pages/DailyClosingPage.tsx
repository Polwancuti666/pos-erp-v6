import { useState, useEffect } from 'react';
import { closingApi } from '@/api/client';
import { DailyClosingSummary, ClosingReport } from '@/types';
import Modal from '@/components/common/Modal';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';

type Step = 'summary' | 'count' | 'confirm' | 'done';

const VARIANCE_REASONS = [
  'Salah kembalian',
  'Kehilangan',
  'Selisih kecil (<Rp 1.000)',
  'Koreksi kasir',
  'Lainnya',
];

export default function DailyClosingPage() {
  const [step, setStep] = useState<Step>('summary');
  const [summary, setSummary] = useState<DailyClosingSummary | null>(null);
  const [report, setReport] = useState<ClosingReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [cashCounted, setCashCounted] = useState('');
  const [varianceReason, setVarianceReason] = useState('');
  const [varianceNote, setVarianceNote] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);

  const today = new Date().toISOString().split('T')[0];
  const fmt = (n: number) => 'Rp ' + n.toLocaleString('id-ID');

  useEffect(() => { loadSummary(); }, []);

  const loadSummary = async () => {
    setLoading(true);
    try {
      const data = await closingApi.summary(today, 'HQ');
      setSummary(data);
    } catch { /* empty */ }
    setLoading(false);
  };

  const cashCount = parseInt(cashCounted.replace(/[^0-9]/g, ''), 10) || 0;
  const variance = summary ? summary.cashExpected - cashCount : 0;
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
      setReport(result.report);
      setStep('done');
    } catch { alert('Gagal submit closing'); }
    setLoading(false);
    setShowConfirm(false);
  };

  if (loading && !summary) return <div className="p-4"><LoadingSkeleton rows={6} /></div>;
  if (!summary) return <div className="p-4 text-center text-gray-500">Gagal memuat data closing</div>;

  // ── Done ──
  if (step === 'done' && report) {
    return (
      <div className="p-4 space-y-4 animate-fade-in">
        <div className="text-center py-8">
          <div className="text-6xl mb-4">🔒</div>
          <h2 className="text-2xl font-bold text-charcoal mb-2">Closing Berhasil</h2>
          <p className="text-gray-500">{today} — Cabang HQ</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-100 p-4 space-y-3">
          <div className="flex justify-between"><span className="text-gray-500">Total Transaksi</span><span className="font-semibold">{report.totalTransactions}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Total Nominal</span><span className="font-semibold">{fmt(report.totalNominal)}</span></div>
          <hr />
          <div className="flex justify-between"><span className="text-gray-500">Kas Expected</span><span>{fmt(report.cashExpected)}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Kas Dihitung</span><span>{fmt(report.cashCounted)}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Selisih</span><span className={report.variance !== 0 ? 'text-red-600 font-semibold' : 'text-green-600'}>{fmt(report.variance)}</span></div>
          {report.varianceReason && <div className="flex justify-between"><span className="text-gray-500">Alasan</span><span>{report.varianceReason}</span></div>}
        </div>

        <button className="w-full bg-gray-100 text-charcoal py-3 rounded-xl font-medium">Cetak Laporan</button>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-charcoal">Daily Closing</h2>
      <p className="text-sm text-gray-500">{today} — Cabang HQ</p>

      {/* Step 1: Summary */}
      {step === 'summary' && (
        <div className="space-y-3 animate-fade-in">
          <div className="bg-white rounded-xl border border-gray-100 p-4 space-y-3">
            <h3 className="font-semibold text-charcoal">Ringkasan Hari Ini</h3>
            <div className="flex justify-between"><span className="text-gray-500">Total Transaksi</span><span className="font-semibold">{summary.totalTransactions}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Total Nominal</span><span className="font-semibold">{fmt(summary.totalNominal)}</span></div>
            <hr />
            <div className="flex justify-between"><span className="text-gray-500">Tunai</span><span>{fmt(summary.byMethod.cash)}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">QRIS</span><span>{fmt(summary.byMethod.qris)}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Transfer</span><span>{fmt(summary.byMethod.bankTransfer)}</span></div>
          </div>

          {/* Blockers */}
          {summary.criticalExceptionCount > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <p className="text-red-700 font-medium">⚠ Ada {summary.criticalExceptionCount} exception kritis</p>
              <p className="text-sm text-red-600">Hubungi Accounting Admin sebelum closing</p>
            </div>
          )}

          {summary.unpostedCount > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
              <p className="text-yellow-700 text-sm">Ada {summary.unpostedCount} transaksi belum diposting. Closing tetap bisa dilakukan.</p>
            </div>
          )}

          <button
            onClick={() => setStep('count')}
            disabled={summary.criticalExceptionCount > 0}
            className="w-full bg-gold text-white py-4 rounded-xl font-semibold text-lg disabled:opacity-40 disabled:cursor-not-allowed active:bg-gold/90"
          >
            Lanjut Hitung Kas
          </button>
        </div>
      )}

      {/* Step 2: Cash Count */}
      {step === 'count' && (
        <div className="space-y-4 animate-fade-in">
          <div className="bg-ivory-warm rounded-xl p-4 text-center">
            <p className="text-sm text-gray-500 mb-1">Kas Expected</p>
            <p className="text-2xl font-bold text-charcoal">{fmt(summary.cashExpected)}</p>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <label className="text-sm text-gray-500 block mb-2">Kas Dihitung (Fisik)</label>
            <input
              type="text"
              inputMode="numeric"
              value={cashCounted}
              onChange={e => setCashCounted(e.target.value)}
              placeholder="0"
              className="w-full text-2xl font-bold text-charcoal text-center outline-none bg-transparent"
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
            className="w-full bg-gold text-white py-4 rounded-xl font-semibold text-lg disabled:opacity-40 active:bg-gold/90"
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
              <label className="text-sm font-medium text-charcoal">Alasan Selisih *</label>
              <select
                value={varianceReason}
                onChange={e => setVarianceReason(e.target.value)}
                className="w-full p-3 border border-gray-200 rounded-xl bg-white text-charcoal"
              >
                <option value="">Pilih alasan...</option>
                {VARIANCE_REASONS.map(r => <option key={r} value={r}>{r}</option>)}
              </select>

              {varianceReason === 'Lainnya' && (
                <textarea
                  value={varianceNote}
                  onChange={e => setVarianceNote(e.target.value)}
                  placeholder="Jelaskan alasan..."
                  className="w-full p-3 border border-gray-200 rounded-xl bg-white text-charcoal h-24 resize-none"
                />
              )}
            </div>
          )}

          <button
            onClick={() => setShowConfirm(true)}
            disabled={absVariance > 0 && !varianceReason}
            className="w-full bg-charcoal text-white py-4 rounded-xl font-semibold text-lg disabled:opacity-40 active:bg-charcoal/90"
          >
            Konfirmasi Closing
          </button>
        </div>
      )}

      {/* Confirm Modal */}
      <Modal
        open={showConfirm}
        onClose={() => setShowConfirm(false)}
        title="Konfirmasi Closing"
        actions={
          <>
            <button onClick={() => setShowConfirm(false)} className="flex-1 py-3 bg-gray-100 rounded-xl font-medium">
              Batal
            </button>
            <button onClick={handleSubmit} className="flex-1 py-3 bg-charcoal text-white rounded-xl font-medium">
              Ya, Closing
            </button>
          </>
        }
      >
        <p>Closing tidak bisa di-ubah setelah dikonfirmasi.</p>
        <p className="mt-2 font-medium">Kas: {fmt(cashCount)} | Selisih: {fmt(absVariance)}</p>
      </Modal>
    </div>
  );
}
