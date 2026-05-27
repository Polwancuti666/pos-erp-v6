import { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { transactionApi, paymentApi } from '@/api/client';
import { Transaction, PaymentMethod, CartItem, STATE_LABELS, ERROR_MESSAGES } from '@/types';
import StaffLockCountdown from '@/components/checkout/StaffLockCountdown';
import QrisPaymentPanel from '@/components/checkout/QrisPaymentPanel';
import CashPaymentPanel from '@/components/checkout/CashPaymentPanel';
import BankTransferPanel from '@/components/checkout/BankTransferPanel';
import ErrorToast from '@/components/checkout/ErrorToast';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';

const PAYMENT_METHODS: { value: PaymentMethod; label: string; icon: string }[] = [
  { value: 'CASH', label: 'Tunai', icon: '💵' },
  { value: 'QRIS', label: 'QRIS', icon: '📱' },
  { value: 'BANK_TRANSFER', label: 'Transfer', icon: '🏦' },
];

export default function CheckoutPage() {
  const { transactionId } = useParams();
  const navigate = useNavigate();
  const [tx, setTx] = useState<Transaction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPayment, setSelectedPayment] = useState<PaymentMethod | null>(null);
  const [step, setStep] = useState<'cart' | 'payment' | 'done'>('cart');

  const formatRp = (n: number) => 'Rp ' + n.toLocaleString('id-ID');

  const loadTransaction = useCallback(async (id: string) => {
    try {
      const data = await transactionApi.get(id);
      setTx(data);
    } catch { setError('Gagal memuat transaksi'); }
  }, []);

  const handleSelectPayment = async (method: PaymentMethod) => {
    if (!transactionId) return;
    setLoading(true);
    try {
      await transactionApi.selectPaymentMethod(transactionId, { method });
      setSelectedPayment(method);
      setStep('payment');
      await loadTransaction(transactionId);
    } catch { setError(ERROR_MESSAGES.PAYMENT_METHOD_INACTIVE); }
    setLoading(false);
  };

  const handleConfirmCash = async (amountReceived: number) => {
    if (!transactionId) return;
    setLoading(true);
    try {
      const result = await transactionApi.confirmCash(transactionId, { amountReceived });
      setTx(prev => prev ? { ...prev, state: 'PAID', posCode: result.posCode } : prev);
      setStep('done');
    } catch { setError('Gagal konfirmasi pembayaran'); }
    setLoading(false);
  };

  const handleQrisPaid = useCallback(() => {
    setTx(prev => prev ? { ...prev, state: 'PAID' } : prev);
    setStep('done');
  }, []);

  // ── Render ──
  if (!transactionId) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500 mb-4">Mulai transaksi baru</p>
        <button
          onClick={async () => {
            setLoading(true);
            try {
              const result = await transactionApi.create({ branchCode: 'HQ', deviceId: 'POS-01', cashierId: 'KSR001' });
              navigate(`/checkout/${result.id}`);
            } catch { setError('Gagal membuat transaksi'); }
            setLoading(false);
          }}
          className="bg-gold text-white px-8 py-4 rounded-xl font-semibold text-lg active:bg-gold/90"
        >
          Transaksi Baru
        </button>
      </div>
    );
  }

  if (tx && step === 'done') {
    return (
      <div className="p-4 flex flex-col items-center justify-center min-h-[60vh] animate-fade-in">
        <div className="text-6xl mb-4">✅</div>
        <h2 className="text-2xl font-bold text-charcoal mb-2">Transaksi Berhasil</h2>
        {tx.posCode && (
          <div className="bg-green-50 px-6 py-3 rounded-xl mb-4">
            <p className="text-sm text-gray-500">POS Code</p>
            <p className="text-xl font-mono font-bold text-green-700">{tx.posCode}</p>
          </div>
        )}
        <p className="text-gray-500 mb-6">{formatRp(tx.total)}</p>
        <button
          onClick={() => navigate('/checkout')}
          className="bg-gold text-white px-8 py-4 rounded-xl font-semibold active:bg-gold/90"
        >
          Transaksi Baru
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-[calc(100vh-8rem)]">
      {error && <ErrorToast message={error} onDismiss={() => setError(null)} />}

      {/* Staff Lock */}
      {tx?.staffLock && tx.state === 'RESERVED' && (
        <div className="px-4 pt-3">
          <StaffLockCountdown
            transactionId={tx.id}
            expiresAt={tx.staffLock.lockedUntil}
            staffName={tx.items[0]?.staff?.name || 'Staff'}
            onReplaced={(name) => loadTransaction(tx.id)}
            onCancelled={() => navigate('/checkout')}
          />
        </div>
      )}

      {/* Cart Area */}
      {step === 'cart' && (
        <>
          <div className="flex-1 px-4 py-3 space-y-2 overflow-auto">
            <div className="bg-white rounded-xl border border-gray-100 p-3 flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Pelanggan</p>
                <p className="font-medium text-charcoal">{tx?.customer?.name || 'Tamu'}</p>
              </div>
              <button className="text-sm text-gold font-medium">Ganti</button>
            </div>

            {tx?.items.map((item: CartItem) => (
              <div key={item.id} className="bg-white rounded-xl border border-gray-100 p-3">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-charcoal">{item.service.name}</p>
                    <p className="text-xs text-gray-500">{item.staff?.name || 'Belum pilih staff'}</p>
                  </div>
                  <p className="font-semibold text-charcoal">{formatRp(item.total)}</p>
                </div>
              </div>
            ))}

            {(!tx?.items || tx.items.length === 0) && (
              <div className="text-center py-12 text-gray-400">
                <p className="text-4xl mb-2">🛒</p>
                <p>Keranjang kosong</p>
              </div>
            )}
          </div>

          {/* Summary + Actions */}
          <div className="sticky bottom-16 bg-white border-t border-gray-100 px-4 py-3 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-500">Total</span>
              <span className="text-xl font-bold text-charcoal">{formatRp(tx?.total || 0)}</span>
            </div>

            {tx?.state === 'VALIDATED' && (
              <div className="grid grid-cols-3 gap-2">
                {PAYMENT_METHODS.map(m => (
                  <button
                    key={m.value}
                    onClick={() => handleSelectPayment(m.value)}
                    disabled={loading}
                    className="flex flex-col items-center gap-1 py-3 bg-ivory-warm rounded-xl active:bg-gray-200 transition-colors"
                  >
                    <span className="text-2xl">{m.icon}</span>
                    <span className="text-xs font-medium text-charcoal">{m.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* Payment Step */}
      {step === 'payment' && selectedPayment && (
        <div className="flex-1">
          {selectedPayment === 'CASH' && tx && (
            <CashPaymentPanel total={tx.total} onConfirm={handleConfirmCash} loading={loading} />
          )}
          {selectedPayment === 'QRIS' && tx?.paymentIntent && (
            <QrisPaymentPanel
              paymentIntentId={tx.paymentIntent.id}
              qrisImageUrl={`/api/payment/qris-qr/${tx.paymentIntent.id}`}
              expiresAt={new Date(Date.now() + 20 * 60 * 1000).toISOString()}
              onPaid={handleQrisPaid}
            />
          )}
          {selectedPayment === 'BANK_TRANSFER' && tx && (
            <BankTransferPanel bankName="BCA" accountNumber="1234567890" amount={tx.total} />
          )}

          <div className="px-4 mt-4">
            <button
              onClick={() => { setStep('cart'); setSelectedPayment(null); }}
              className="w-full py-3 text-gray-500 text-sm"
            >
              ← Kembali
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
