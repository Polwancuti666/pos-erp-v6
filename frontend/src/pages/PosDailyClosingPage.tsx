import { useState, useEffect } from 'react';
import { closingApi } from '../api/client';
import LoadingSkeleton from '../components/common/LoadingSkeleton';

interface ClosingSummary {
  date: string;
  branchCode: string;
  totalTransactions: number;
  totalNominal: number;
  byMethod: { cash: number; qris: number; bankTransfer: number };
  cashExpected: number;
  unpostedCount: number;
  openExceptionCount: number;
  alreadyClosed: boolean;
  closingId: string | null;
}

interface ClosingHistory {
  id: string;
  date: string;
  totalNominal: number;
  totalTransactions: number;
  cashExpected: number;
  cashCounted: number;
  variance: number;
  closedAt: string;
  managerName: string;
  status: string;
}

export default function PosDailyClosingPage() {
  const [summary, setSummary] = useState<ClosingSummary | null>(null);
  const [history, setHistory] = useState<ClosingHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<'summary' | 'count' | 'confirm' | 'done'>('summary');

  // Cash count state
  const [cashCount, setCashCount] = useState('');
  const [varianceReason, setVarianceReason] = useState('');
  const [varianceNote, setVarianceNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submittedReport, setSubmittedReport] = useState<any>(null);

  const formatRp = (n: number) => 'Rp ' + (n || 0).toLocaleString('id-ID');

  function getBranchCode(): string {
    // Get branch name from localStorage (set by branch selector)
    const branchId = localStorage.getItem('pos_branch_id') || '';
    // For now, pass the branch ID directly; backend resolves it
    return branchId;
  }

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      // Use local date (getFullYear/getMonth/getDate) NOT toISOString (which returns UTC)
      const now = new Date();
      const today = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
      const branchCode = getBranchCode();

      const [summaryResult, historyResult] = await Promise.allSettled([
        closingApi.summary(`date=${today}&branchCode=${branchCode}`),
        closingApi.history(`branchCode=${branchCode}`),
      ]);

      if (summaryResult.status === 'fulfilled') {
        setSummary(summaryResult.value as ClosingSummary);
      }

      if (historyResult.status === 'fulfilled') {
        const h = historyResult.value;
        const list = Array.isArray(h) ? h : [];
        setHistory(list.slice(0, 10));
      }
    } catch (err: any) {
      setError(err.message || 'Gagal memuat data closing');
    }
    setLoading(false);
  }

  const variance = cashCount ? parseInt(cashCount.replace(/\D/g, ''), 10) - (summary?.cashExpected || 0) : 0;
  const hasVariance = variance !== 0 && cashCount !== '';

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const staff = JSON.parse(localStorage.getItem('pos_staff') || '{}');
      // Use local date (not UTC from toISOString)
      const now = new Date();
      const today = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');

      const result = await closingApi.submit({
        date: summary?.date || today,
        branchCode: getBranchCode(),
        cashCounted: parseInt(cashCount.replace(/\D/g, ''), 10),
        varianceReason: hasVariance ? varianceReason : undefined,
        varianceNote: hasVariance ? varianceNote : undefined,
        managerId: staff.id || 'pos-user',
        managerName: staff.name || staff.full_name || 'Kasir',
      });
      setSubmittedReport(result);
      setStep('done');
    } catch (err: any) {
      // Parse error message for blocking errors
      try {
        const jsonStart = err.message?.indexOf('{') ?? -1;
        const errData = jsonStart >= 0 ? JSON.parse(err.message.substring(jsonStart)) : {};
        if (errData.error === 'CLOSING_BLOCKED') {
          setError(errData.message || 'Closing diblokir karena selisih terlalu besar');
        } else if (errData.error === 'ALREADY_CLOSED') {
          setError(errData.message || 'Closing sudah disubmit sebelumnya');
        } else {
          setError(errData.message || err.message || 'Gagal submit closing');
        }
      } catch {
        setError(err.message || 'Gagal submit closing');
      }
    }
    setSubmitting(false);
  }

  function formatCashInput(value: string) {
    const digits = value.replace(/\D/g, '');
    if (!digits) return '';
    return parseInt(digits, 10).toLocaleString('id-ID');
  }

  if (loading) {
    return (
      <div className="p-4 space-y-4">
        <h1 className="text-lg font-bold text-[var(--charcoal)]">Closing Harian</h1>
        <LoadingSkeleton rows={5} />
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Error Toast */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      <h1 className="text-lg font-bold text-[var(--charcoal)]">Closing Harian</h1>

      {/* Step: Summary */}
      {step === 'summary' && summary && (
        <>
          {/* Already closed notice */}
          {summary.alreadyClosed && (
            <div className="bg-green-50 border border-green-200 text-green-800 text-sm px-4 py-3 rounded-xl">
              <p className="font-medium">✅ Closing sudah disubmit</p>
              <p className="text-xs mt-1">Closing untuk hari ini sudah dilakukan sebelumnya</p>
            </div>
          )}

          {/* Warning for unposted / exceptions */}
          {(summary.unpostedCount > 0 || summary.openExceptionCount > 0) && (
            <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm px-4 py-3 rounded-xl">
              <p className="font-medium">⚠️ Perhatian</p>
              {summary.unpostedCount > 0 && (
                <p className="text-xs mt-1">{summary.unpostedCount} transaksi belum diposting</p>
              )}
              {summary.openExceptionCount > 0 && (
                <p className="text-xs mt-1">{summary.openExceptionCount} exception belum diselesaikan</p>
              )}
            </div>
          )}

          {/* Summary Card */}
          <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">Tanggal</span>
              <span className="text-sm font-medium text-[var(--charcoal)]">
                {new Date(summary.date + 'T00:00:00').toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
              </span>
            </div>
            <div className="border-t border-gray-100" />
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">Total Transaksi</span>
              <span className="text-sm font-bold text-[var(--charcoal)]">{summary.totalTransactions}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">Total Nominal</span>
              <span className="text-sm font-bold text-[var(--charcoal)]">{formatRp(summary.totalNominal)}</span>
            </div>
          </div>

          {/* Breakdown by Method */}
          <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
            <h3 className="text-xs font-semibold text-gray-500 mb-3">Rincian Metode Pembayaran</h3>
            <div className="space-y-2">
              {[
                { label: '💵 Tunai', value: summary.byMethod.cash },
                { label: '📱 QRIS', value: summary.byMethod.qris },
                { label: '🏦 Transfer', value: summary.byMethod.bankTransfer },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{item.label}</span>
                  <span className="text-sm font-medium text-[var(--charcoal)]">{formatRp(item.value)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Expected Cash */}
          <div className="bg-gradient-to-r from-[var(--gold)]/10 to-[var(--rose)]/10 rounded-xl p-4 border border-[var(--gold)]/20">
            <p className="text-xs text-gray-500">Uang Tunai Seharusnya</p>
            <p className="text-2xl font-bold text-[var(--charcoal)] mt-1">{formatRp(summary.cashExpected)}</p>
          </div>

          <button
            onClick={() => setStep('count')}
            disabled={summary.totalTransactions === 0 || summary.alreadyClosed}
            className="w-full py-3.5 rounded-xl bg-[var(--gold)] text-white font-semibold text-sm active:bg-[var(--gold)]/90 disabled:opacity-50 transition-colors shadow-sm"
          >
            {summary.alreadyClosed ? 'Sudah Di-closing' : 'Lanjut Hitung Uang'}
          </button>
        </>
      )}

      {/* Step: Cash Count */}
      {step === 'count' && (
        <>
          <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
            <h3 className="text-sm font-semibold text-[var(--charcoal)] mb-3">Hitung Uang Tunai</h3>
            <p className="text-xs text-gray-400 mb-4">
              Seharusnya: <span className="font-medium text-[var(--charcoal)]">{formatRp(summary?.cashExpected || 0)}</span>
            </p>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Jumlah Uang Tunai</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">Rp</span>
                <input
                  type="text"
                  inputMode="numeric"
                  value={cashCount}
                  onChange={(e) => setCashCount(formatCashInput(e.target.value))}
                  placeholder="0"
                  className="w-full pl-10 pr-3 py-3 rounded-xl border border-gray-200 bg-white text-lg font-bold text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent text-right"
                />
              </div>
            </div>

            {/* Variance Display */}
            {cashCount && (
              <div className={`mt-4 p-3 rounded-xl ${hasVariance ? (variance > 0 ? 'bg-blue-50' : 'bg-red-50') : 'bg-green-50'}`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-600">Selisih</span>
                  <span className={`text-lg font-bold ${hasVariance ? (variance > 0 ? 'text-blue-600' : 'text-red-600') : 'text-green-600'}`}>
                    {variance > 0 ? '+' : ''}{formatRp(variance)}
                  </span>
                </div>
                {!hasVariance && <p className="text-xs text-green-600 mt-1">✓ Sesuai</p>}
              </div>
            )}

            {/* Variance Reason (required if variance) */}
            {hasVariance && (
              <div className="mt-4 space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Alasan Selisih *</label>
                  <select
                    value={varianceReason}
                    onChange={(e) => setVarianceReason(e.target.value)}
                    required
                    className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
                  >
                    <option value="">Pilih alasan</option>
                    <option value="KEMBALIAN_LEBIH">Kembalian lebih</option>
                    <option value="KEMBALIAN_KURANG">Kembalian kurang</option>
                    <option value="UANG_PALSU">Uang palsu / rusak</option>
                    <option value="TIP">Tip dari customer</option>
                    <option value="KESALAHAN_KASIR">Kesalahan kasir</option>
                    <option value="LAINNYA">Lainnya</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Catatan</label>
                  <textarea
                    value={varianceNote}
                    onChange={(e) => setVarianceNote(e.target.value)}
                    placeholder="Jelaskan alasan selisih..."
                    rows={2}
                    className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent resize-none"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setStep('summary')}
              className="flex-1 py-3 rounded-xl border border-gray-200 text-sm font-medium text-gray-600 active:bg-gray-50 transition-colors"
            >
              Kembali
            </button>
            <button
              onClick={() => setStep('confirm')}
              disabled={!cashCount || (hasVariance && !varianceReason)}
              className="flex-1 py-3 rounded-xl bg-[var(--gold)] text-white font-semibold text-sm active:bg-[var(--gold)]/90 disabled:opacity-50 transition-colors shadow-sm"
            >
              Lanjut
            </button>
          </div>
        </>
      )}

      {/* Step: Confirm */}
      {step === 'confirm' && summary && (
        <>
          <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm space-y-3">
            <h3 className="text-sm font-semibold text-[var(--charcoal)]">Konfirmasi Closing</h3>
            <div className="border-t border-gray-100" />
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Total Transaksi</span>
                <span className="font-medium text-[var(--charcoal)]">{summary.totalTransactions}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Total Nominal</span>
                <span className="font-medium text-[var(--charcoal)]">{formatRp(summary.totalNominal)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Uang Tunai Seharusnya</span>
                <span className="font-medium text-[var(--charcoal)]">{formatRp(summary.cashExpected)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Uang Tunai Dihitung</span>
                <span className="font-medium text-[var(--charcoal)]">{formatRp(parseInt(cashCount.replace(/\D/g, ''), 10))}</span>
              </div>
              <div className="border-t border-gray-100" />
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Selisih</span>
                <span className={`font-bold ${variance === 0 ? 'text-green-600' : variance > 0 ? 'text-blue-600' : 'text-red-600'}`}>
                  {variance > 0 ? '+' : ''}{formatRp(variance)}
                </span>
              </div>
              {hasVariance && varianceReason && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Alasan</span>
                  <span className="font-medium text-[var(--charcoal)]">{varianceReason.replace(/_/g, ' ')}</span>
                </div>
              )}
            </div>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-xs px-4 py-3 rounded-xl">
            ⚠️ Closing tidak dapat dibatalkan setelah disubmit. Pastikan semua data sudah benar.
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setStep('count')}
              className="flex-1 py-3 rounded-xl border border-gray-200 text-sm font-medium text-gray-600 active:bg-gray-50 transition-colors"
            >
              Kembali
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="flex-1 py-3 rounded-xl bg-[var(--gold)] text-white font-semibold text-sm active:bg-[var(--gold)]/90 disabled:opacity-50 transition-colors shadow-sm"
            >
              {submitting ? 'Menyimpan...' : 'Submit Closing'}
            </button>
          </div>
        </>
      )}

      {/* Step: Done */}
      {step === 'done' && (
        <div className="text-center py-8">
          <div className="text-6xl mb-4">✅</div>
          <h2 className="text-xl font-bold text-[var(--charcoal)]">Closing Berhasil!</h2>
          <p className="text-sm text-gray-500 mt-2">Laporan closing telah disubmit dan tersimpan</p>
          {submittedReport && (
            <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm mt-4 text-left space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">ID Laporan</span>
                <span className="font-mono text-[var(--charcoal)]">{submittedReport.doc_key || submittedReport.id || '-'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Total Transaksi</span>
                <span className="text-[var(--charcoal)]">{submittedReport.totalTransactions || 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Total Nominal</span>
                <span className="text-[var(--charcoal)]">{formatRp(submittedReport.totalNominal || 0)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Selisih</span>
                <span className={`font-medium ${(submittedReport.variance || 0) === 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatRp(submittedReport.variance || 0)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Waktu</span>
                <span className="text-[var(--charcoal)]">{new Date().toLocaleString('id-ID')}</span>
              </div>
            </div>
          )}
          <button
            onClick={() => {
              setStep('summary');
              setCashCount('');
              setVarianceReason('');
              setVarianceNote('');
              setSubmittedReport(null);
              loadData();
            }}
            className="mt-6 px-8 py-3 rounded-xl bg-[var(--gold)] text-white font-semibold text-sm active:bg-[var(--gold)]/90 transition-colors shadow-sm"
          >
            Selesai
          </button>
        </div>
      )}

      {/* Closing History */}
      {step === 'summary' && history.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[var(--charcoal)] mb-3">Riwayat Closing</h3>
          <div className="space-y-2">
            {history.map((h) => (
              <div key={h.id} className="bg-white rounded-xl p-3 border border-gray-100 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-[var(--charcoal)]">
                    {new Date(h.date + 'T00:00:00').toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </span>
                  <span className="text-sm font-bold text-[var(--charcoal)]">{formatRp(h.totalNominal)}</span>
                </div>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs text-gray-400">{h.totalTransactions} transaksi • {h.managerName}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
                    {h.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No data state */}
      {step === 'summary' && !summary && !loading && (
        <div className="bg-white rounded-xl p-8 border border-gray-100 text-center">
          <span className="text-4xl">📊</span>
          <p className="text-gray-400 text-sm mt-3">Tidak ada data closing hari ini</p>
          <button
            onClick={loadData}
            className="mt-4 px-6 py-2 rounded-xl border border-gray-200 text-sm text-gray-600 active:bg-gray-50"
          >
            Refresh
          </button>
        </div>
      )}
    </div>
  );
}
