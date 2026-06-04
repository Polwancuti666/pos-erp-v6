import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { receiptApi, transactionApi } from '../api/client';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import { parseUTCDate, formatDateTime } from '../utils/dateUtils';

interface ReceiptItem {
  item_name: string;
  qty: number;
  unit_price: number;
  total: number;
  item_type?: string;
}

interface Receipt {
  doc_key: string;
  customer_name: string;
  customer_phone?: string;
  therapist_name: string;
  status: string;
  subtotal: number;
  discount: number;
  tax: number;
  total: number;
  created_at: string;
  payment_method: string;
  branch_name: string;
  branch_address?: string;
  cashier_name: string;
  items: ReceiptItem[];
}

const formatRp = (n: number) => 'Rp ' + (n || 0).toLocaleString('id-ID');

export default function PosReceiptPage() {
  const { transactionId } = useParams();
  const navigate = useNavigate();
  const [receipts, setReceipts] = useState<any[]>([]);
  const [selectedReceipt, setSelectedReceipt] = useState<Receipt | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const receiptRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (transactionId) {
      loadSingleReceipt(transactionId);
    } else {
      loadReceipts();
    }
  }, [transactionId]);

  async function loadSingleReceipt(id: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await receiptApi.get(id);
      setSelectedReceipt(data as Receipt);
    } catch (err: any) {
      setError(err.message || 'Gagal memuat struk');
    }
    setLoading(false);
  }

  async function loadReceipts() {
    setLoading(true);
    setError(null);
    try {
      const result = await transactionApi.list('status=paid&limit=30');
      const list = Array.isArray(result) ? result : result?.items || result?.data || [];
      setReceipts(list);
    } catch (err: any) {
      setError(err.message || 'Gagal memuat riwayat struk');
    }
    setLoading(false);
  }

  function handlePrint() {
    if (!selectedReceipt) return;
    const url = receiptApi.getHtml(selectedReceipt.doc_key);
    const printWindow = window.open(url, '_blank', 'width=380,height=600');
    if (printWindow) {
      printWindow.onload = () => {
        printWindow.print();
      };
    }
  }

  function handleShare() {
    if (!selectedReceipt) return;
    const text = generateReceiptText(selectedReceipt);
    if (navigator.share) {
      navigator.share({ title: `Struk ${selectedReceipt.doc_key}`, text }).catch(() => {});
    } else {
      navigator.clipboard.writeText(text).then(() => {
        alert('Struk disalin ke clipboard');
      });
    }
  }

  function generateReceiptText(r: Receipt): string {
    const date = parseUTCDate(r.created_at).toLocaleString('id-ID', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
    const payLabel = `${r.payment_method} - ${formatRp(r.total)}`;
    const status = (r.status || '').toLowerCase();
    const statusLabel = ['paid', 'completed', 'selesai'].includes(status) ? 'paid' : status;

    let text = `═══════════════════════\n`;
    text += `      ${r.branch_name}\n`;
    text += `      Struk Transaksi\n`;
    text += `═══════════════════════\n\n`;
    text += `No. Transaksi  ${r.doc_key}\n`;
    text += `Tanggal        ${date}\n`;
    text += `Customer       ${r.customer_name}\n`;
    text += `Therapist      ${r.therapist_name}\n`;
    text += `───────────────────────\n`;
    for (const item of r.items) {
      const qty = item.qty === Math.floor(item.qty) ? item.qty : item.qty;
      text += `${item.item_name}\n`;
      text += `  ${qty} x ${formatRp(item.unit_price)}          ${formatRp(item.total)}\n`;
    }
    text += `───────────────────────\n`;
    text += `Subtotal       ${formatRp(r.subtotal)}\n`;
    text += `Diskon         ${formatRp(r.discount)}\n`;
    text += `Pajak          ${formatRp(r.tax)}\n`;
    text += `───────────────────────\n`;
    text += `Total          ${formatRp(r.total)}\n`;
    text += `Pembayaran     ${payLabel}\n`;
    text += `Status         ${statusLabel}\n\n`;
    text += `   Terima kasih atas kunjungan Anda.\n`;
    text += `═══════════════════════\n`;
    return text;
  }

  // ── Loading ──
  if (loading) {
    return (
      <div className="p-4 space-y-4">
        <h1 className="text-lg font-bold text-[var(--charcoal)]">Struk</h1>
        <LoadingSkeleton rows={5} />
      </div>
    );
  }

  // ── Single Receipt View ──
  if (selectedReceipt) {
    const r = selectedReceipt;
    const dateStr = parseUTCDate(r.created_at).toLocaleString('id-ID', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
    const payLabel = `${r.payment_method} - ${formatRp(r.total)}`;
    const status = (r.status || '').toLowerCase();
    const statusLabel = ['paid', 'completed', 'selesai'].includes(status) ? 'paid' : status;

    return (
      <div className="p-4 space-y-4">
        {/* Error Toast */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">✕</button>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setSelectedReceipt(null); loadReceipts(); }}
            className="text-sm text-gray-500 active:text-gray-700"
          >
            ← Kembali
          </button>
          <div className="flex-1" />
          <button
            onClick={handleShare}
            className="px-4 py-2 rounded-xl border border-gray-200 text-sm font-medium text-gray-600 active:bg-gray-50 transition-colors"
          >
            📤 Bagikan
          </button>
          <button
            onClick={handlePrint}
            className="px-4 py-2 rounded-xl bg-[var(--gold)] text-white text-sm font-medium active:bg-[var(--gold)]/90 transition-colors"
          >
            🖨️ Cetak
          </button>
        </div>

        {/* Receipt Preview — matches Beauty & Shine struk format */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div ref={receiptRef} className="p-6 font-sans text-sm text-black max-w-[340px] mx-auto">

            {/* Header */}
            <div className="text-center mb-3">
              <h2 className="text-xl font-bold">{r.branch_name}</h2>
              <p className="text-xs text-gray-500">Struk Transaksi</p>
            </div>

            <div className="border-t border-dashed border-gray-300 my-3" />

            {/* Transaction Info */}
            <div className="space-y-0.5 text-xs">
              <div className="flex justify-between">
                <span>No. Transaksi</span>
                <span className="font-bold">{r.doc_key}</span>
              </div>
              <div className="flex justify-between">
                <span>Tanggal</span>
                <span>{dateStr}</span>
              </div>
              <div className="flex justify-between">
                <span>Customer</span>
                <span>{r.customer_name}</span>
              </div>
              <div className="flex justify-between">
                <span>Therapist</span>
                <span>{r.therapist_name}</span>
              </div>
            </div>

            <div className="border-t border-dashed border-gray-300 my-3" />

            {/* Items */}
            <div className="space-y-2">
              {r.items.map((item, i) => {
                const qty = item.qty === Math.floor(item.qty) ? item.qty : item.qty;
                return (
                  <div key={i}>
                    <div className="font-bold text-sm">{item.item_name}</div>
                    <div className="flex justify-between text-xs text-gray-600">
                      <span>{qty} x {formatRp(item.unit_price)}</span>
                      <span>{formatRp(item.total)}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="border-t border-dashed border-gray-300 my-3" />

            {/* Summary */}
            <div className="space-y-0.5 text-xs">
              <div className="flex justify-between">
                <span>Subtotal</span>
                <span>{formatRp(r.subtotal)}</span>
              </div>
              <div className="flex justify-between">
                <span>Diskon</span>
                <span>{formatRp(r.discount)}</span>
              </div>
              <div className="flex justify-between">
                <span>Pajak</span>
                <span>{formatRp(r.tax)}</span>
              </div>
            </div>

            <div className="border-t border-dashed border-gray-300 my-3" />

            {/* Total */}
            <div className="flex justify-between text-lg font-bold">
              <span>Total</span>
              <span>{formatRp(r.total)}</span>
            </div>

            {/* Payment */}
            <div className="space-y-0.5 text-xs mt-2">
              <div className="flex justify-between">
                <span>Pembayaran</span>
                <span>{payLabel}</span>
              </div>
              <div className="flex justify-between">
                <span>Status</span>
                <span>{statusLabel}</span>
              </div>
            </div>

            {/* Footer */}
            <div className="text-center mt-5 text-xs text-gray-500">
              Terima kasih atas kunjungan Anda.
            </div>
          </div>
        </div>

        {/* Back button */}
        <button
          onClick={() => { setSelectedReceipt(null); loadReceipts(); }}
          className="w-full py-3 rounded-xl border border-gray-200 text-sm font-medium text-gray-500 active:bg-gray-50 transition-colors"
        >
          ← Kembali ke Riwayat
        </button>
      </div>
    );
  }

  // ── Receipt List View ──
  return (
    <div className="p-4 space-y-4">
      {/* Error Toast */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      <h1 className="text-lg font-bold text-[var(--charcoal)]">Riwayat Struk</h1>

      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : receipts.length ? (
        <div className="space-y-2">
          {receipts.map((r: any) => (
            <button
              key={r.id || r.doc_key}
              onClick={async () => {
                const txId = r.doc_key || r.id;
                try {
                  const fullData = await receiptApi.get(txId);
                  setSelectedReceipt(fullData as Receipt);
                } catch {
                  try {
                    const fullData = await transactionApi.get(txId);
                    setSelectedReceipt(fullData as Receipt);
                  } catch { /* ignore */ }
                }
              }}
              className="w-full bg-white rounded-xl p-4 border border-gray-100 shadow-sm flex items-center justify-between text-left active:bg-gray-50 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-mono font-bold text-[var(--charcoal)]">{r.doc_key || r.posCode || '-'}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
                    {r.payment_method || r.paymentMethod || 'CASH'}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-400">
                  <span>{r.customer_name || r.customerName || 'Walk-in'}</span>
                  <span>•</span>
                  <span>{formatDateTime(r.created_at || r.createdAt, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-sm font-bold text-[var(--charcoal)]">{formatRp(r.total || 0)}</span>
                <p className="text-[10px] text-gray-400">{r.items?.length || 0} item</p>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl p-8 border border-gray-100 text-center">
          <span className="text-4xl">🧾</span>
          <p className="text-gray-400 text-sm mt-3">Belum ada riwayat struk</p>
        </div>
      )}
    </div>
  );
}
