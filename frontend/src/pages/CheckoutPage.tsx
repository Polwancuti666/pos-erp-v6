import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { transactionApi, api } from '@/api/client';
import { Transaction, PaymentMethod, CartItem } from '@/types';
import CashPaymentPanel from '@/components/checkout/CashPaymentPanel';
import ErrorToast from '@/components/checkout/ErrorToast';

interface Customer {
  id: string;
  name: string;
  phone?: string;
}

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
  
  // Customer modal state
  const [showCustomerModal, setShowCustomerModal] = useState(false);
  const [customerSearch, setCustomerSearch] = useState('');
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [showAddNew, setShowAddNew] = useState(false);
  const [newCustomer, setNewCustomer] = useState({ name: '', phone: '' });

  const formatRp = (n: number) => 'Rp ' + (n || 0).toLocaleString('id-ID');

  const loadTransaction = useCallback(async (id: string) => {
    try {
      const data = await transactionApi.get(id);
      setTx(data);
      if (data.state === 'PAID') setStep('done');
    } catch { setError('Gagal memuat transaksi'); }
  }, []);

  useEffect(() => {
    if (transactionId) {
      // Reset state when navigating to a new transaction
      setStep('cart');
      setSelectedPayment(null);
      loadTransaction(transactionId);
    }
  }, [transactionId, loadTransaction]);

  // ── Create new transaction ──
  const handleNewTransaction = async () => {
    setLoading(true);
    try {
      const staff = JSON.parse(localStorage.getItem('pos_staff') || '{}');
      const shiftId = localStorage.getItem('pos_shift_id') || undefined;
      // Use branch_id from header selector (localStorage) — this is the source of truth
      // Fallback: staff.branch_code → staff.branch → 'HQ'
      const branchId = localStorage.getItem('pos_branch_id') || undefined;
      const branchCode = staff.branch || localStorage.getItem('pos_branch_code') || 'HQ';
      const result = await transactionApi.create({
        branch_id: branchId,
        branch_code: branchId ? undefined : branchCode,
        device_id: 'POS-01',
        cashier_id: staff.id || 'KSR001',
        shift_id: shiftId,
      });
      navigate(`/kasir/${result.id}`);
    } catch {
      setError('Gagal membuat transaksi');
    }
    setLoading(false);
  };

  // ── Customer search ──
  const searchCustomers = useCallback(async (q: string) => {
    setSearchLoading(true);
    try {
      const res = await api.getCustomers(q);
      setCustomers(res.items || []);
    } catch {
      setCustomers([]);
    }
    setSearchLoading(false);
  }, []);

  // Debounce search
  useEffect(() => {
    if (!showCustomerModal) return;
    const timer = setTimeout(() => searchCustomers(customerSearch), 300);
    return () => clearTimeout(timer);
  }, [customerSearch, showCustomerModal, searchCustomers]);

  // Open customer modal
  const openCustomerModal = () => {
    setShowCustomerModal(true);
    setShowAddNew(false);
    setCustomerSearch('');
    setNewCustomer({ name: '', phone: '' });
    searchCustomers('');
  };

  // Select existing customer
  const selectCustomer = async (customer: Customer) => {
    if (!transactionId) return;
    setLoading(true);
    try {
      await transactionApi.updateCustomer(transactionId, {
        customer_name: customer.name,
        customer_phone: customer.phone,
      });
      await loadTransaction(transactionId);
      setShowCustomerModal(false);
    } catch {
      setError('Gagal ganti pelanggan');
    }
    setLoading(false);
  };

  // Create new customer and select
  const createAndSelectCustomer = async () => {
    if (!newCustomer.name.trim()) {
      setError('Nama pelanggan wajib diisi');
      return;
    }
    setLoading(true);
    try {
      const created = await api.createCustomer({
        name: newCustomer.name.trim(),
        phone: newCustomer.phone.trim() || null,
      });
      await selectCustomer(created);
      setShowCustomerModal(false);
    } catch {
      setError('Gagal membuat pelanggan baru');
    }
    setLoading(false);
  };

  // ── Select payment method (while still DRAFT) ──
  const handleSelectPayment = async (method: PaymentMethod) => {
    if (!transactionId) return;
    // Prevent Rp 0 transactions
    if (!tx || !tx.total || tx.total <= 0) {
      setError('Tidak bisa pilih pembayaran — keranjang masih kosong');
      return;
    }
    setLoading(true);
    try {
      await transactionApi.selectPaymentMethod(transactionId, { method });
      setSelectedPayment(method);
      await loadTransaction(transactionId);

      // For cash, go to payment input step
      if (method === 'CASH') {
        setStep('payment');
      }
      // For QRIS/bank, could handle differently
    } catch {
      setError('Gagal memilih metode pembayaran');
    }
    setLoading(false);
  };

  // ── Submit checkout (DRAFT → VALIDATED) then confirm cash ──
  const handleConfirmCash = async (amountReceived: number) => {
    if (!transactionId) return;
    // Prevent Rp 0 transactions
    if (!tx || !tx.total || tx.total <= 0) {
      setError('Tidak bisa proses pembayaran Rp 0 — pilih treatment dulu');
      return;
    }
    setLoading(true);
    try {
      // Submit checkout first (validates the transaction)
      await transactionApi.submitCheckout(transactionId);
      // Then confirm cash payment
      const result = await transactionApi.confirmCash(transactionId, { amountReceived });
      setTx((prev) => (prev ? { ...prev, state: 'PAID', posCode: result.posCode || result.pos_code } : prev));
      setStep('done');
    } catch (err: any) {
      setError(err?.message || 'Gagal konfirmasi pembayaran');
    }
    setLoading(false);
  };

  // ═══ RENDER ═══

  // ── No transaction yet ──
  if (!transactionId) {
    return (
      <div className="p-4 flex flex-col items-center justify-center min-h-[60vh]">
        <div className="text-6xl mb-4">🛍️</div>
        <h2 className="text-xl font-bold text-[var(--charcoal)] mb-2">Kasir</h2>
        <p className="text-gray-500 mb-6">Mulai transaksi baru</p>
        <button
          onClick={handleNewTransaction}
          disabled={loading}
          className="bg-[var(--gold)] text-white px-8 py-4 rounded-xl font-semibold text-lg active:opacity-90 transition-opacity disabled:opacity-50"
        >
          {loading ? 'Memuat...' : 'Transaksi Baru'}
        </button>
      </div>
    );
  }

  // ── Payment success ──
  if (step === 'done' && tx) {
    return (
      <div className="p-4 flex flex-col items-center justify-center min-h-[60vh] animate-[fadeIn_0.5s_ease]">
        <div className="text-6xl mb-4">✨</div>
        <h2 className="text-2xl font-bold text-[var(--charcoal)] mb-2">Pembayaran Berhasil</h2>
        {tx.posCode && (
          <div className="bg-green-50 px-6 py-3 rounded-xl mb-2">
            <p className="text-sm text-gray-500">POS Code</p>
            <p className="text-xl font-mono font-bold text-green-700">{tx.posCode}</p>
          </div>
        )}
        <p className="text-gray-500 mb-6 text-lg font-semibold">{formatRp(tx.total)}</p>
        <div className="flex gap-3">
          <button
            onClick={() => navigate(`/receipt/${transactionId}`)}
            className="bg-[var(--gold)] text-white px-6 py-3 rounded-xl font-semibold active:opacity-90"
          >
            🧾 Lihat Struk
          </button>
          <button
            onClick={() => navigate('/kasir')}
            className="border border-gray-200 text-gray-600 px-6 py-3 rounded-xl font-semibold active:bg-gray-50"
          >
            Transaksi Baru
          </button>
        </div>
      </div>
    );
  }

  // ── Main checkout flow ──
  return (
    <div className="flex flex-col min-h-[calc(100vh-8rem)]">
      {error && <ErrorToast message={error} onDismiss={() => setError(null)} />}

      {/* Cart Step */}
      {step === 'cart' && (
        <>
          <div className="flex-1 px-4 py-3 space-y-2 overflow-auto">
            {/* Customer */}
            <div className="bg-white rounded-xl border border-gray-100 p-3 flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Pelanggan</p>
                <p className="font-medium text-[var(--charcoal)]">{tx?.customer?.name || 'Tamu'}</p>
              </div>
              <button 
                onClick={openCustomerModal}
                className="text-sm text-[var(--gold)] font-medium"
              >Ganti</button>
            </div>

            {/* Add Treatment */}
            <button
              onClick={() => navigate(`/kasir/${transactionId}/select-treatment`)}
              className="w-full bg-[var(--gold)] text-white py-3 rounded-xl font-semibold text-sm active:opacity-90 transition-opacity"
            >
              + Pilih Treatment
            </button>

            {/* Cart Items */}
            {tx?.items && tx.items.length > 0 ? (
              tx.items.map((item: CartItem) => (
                <div key={item.id} className="bg-white rounded-xl border border-gray-100 p-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-[var(--charcoal)]">{item.service?.name}</p>
                      <p className="text-xs text-gray-500">{item.staff?.name || 'Belum pilih staff'}</p>
                    </div>
                    <p className="font-semibold text-[var(--charcoal)]">{formatRp(item.total || item.price)}</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-12 text-gray-400">
                <p className="text-4xl mb-2">🛒</p>
                <p>Keranjang kosong — pilih treatment dulu</p>
              </div>
            )}
          </div>

          {/* Summary + Payment Selection */}
          <div className="sticky bottom-16 bg-white border-t border-gray-100 px-4 py-3 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-500">Total</span>
              <span className="text-xl font-bold text-[var(--charcoal)]">{formatRp(tx?.total || 0)}</span>
            </div>

            {/* Payment method selection (available when items exist with total > 0, DRAFT state) */}
            {tx?.state === 'DRAFT' && tx.items && tx.items.length > 0 && (tx?.total || 0) > 0 && !selectedPayment && (
              <div className="space-y-2">
                <p className="text-sm text-gray-500 font-medium">Pilih Pembayaran</p>
                <div className="grid grid-cols-3 gap-2">
                  {PAYMENT_METHODS.map((m) => (
                    <button
                      key={m.value}
                      onClick={() => handleSelectPayment(m.value)}
                      disabled={loading}
                      className="flex flex-col items-center gap-1 py-3 bg-[var(--ivory-warm)] rounded-xl active:bg-gray-200 transition-colors disabled:opacity-50"
                    >
                      <span className="text-2xl">{m.icon}</span>
                      <span className="text-xs font-medium text-[var(--charcoal)]">{m.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* After payment method selected (still DRAFT but pm set) */}
            {selectedPayment === 'CASH' && step === 'cart' && (
              <div className="text-center text-sm text-gray-500">
                Metode: 💵 Tunai — masukkan nominal di bawah
              </div>
            )}
          </div>
        </>
      )}

      {/* Cash Payment Step */}
      {step === 'payment' && selectedPayment === 'CASH' && tx && (
        <div className="flex-1 p-4">
          <CashPaymentPanel total={tx.total} onConfirm={handleConfirmCash} loading={loading} />
          <button
            onClick={() => { setStep('cart'); setSelectedPayment(null); }}
            className="w-full py-3 text-gray-500 text-sm mt-4"
          >
            ← Ganti Metode Bayar
          </button>
        </div>
      )}

      {/* QRIS / Transfer placeholder */}
      {step === 'payment' && selectedPayment === 'QRIS' && (
        <div className="flex-1 p-4 text-center py-12">
          <p className="text-4xl mb-4">📱</p>
          <p className="text-gray-500">QRIS — coming soon</p>
          <button onClick={() => { setStep('cart'); setSelectedPayment(null); }} className="text-sm text-gray-400 mt-4">← Kembali</button>
        </div>
      )}
      {step === 'payment' && selectedPayment === 'BANK_TRANSFER' && (
        <div className="flex-1 p-4 text-center py-12">
          <p className="text-4xl mb-4">🏦</p>
          <p className="text-gray-500">Transfer Bank — coming soon</p>
          <button onClick={() => { setStep('cart'); setSelectedPayment(null); }} className="text-sm text-gray-400 mt-4">← Kembali</button>
        </div>
      )}

      {/* Customer Selector Modal */}
      {showCustomerModal && (
        <div className="fixed inset-0 bg-black/50 flex items-end justify-center z-[60]">
          <div className="bg-white rounded-t-2xl w-full max-w-md max-h-[80vh] flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-lg font-bold text-[var(--charcoal)]">
                {showAddNew ? '➕ Pelanggan Baru' : '👤 Pilih Pelanggan'}
              </h3>
              <button 
                onClick={() => setShowCustomerModal(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >×</button>
            </div>

            {!showAddNew ? (
              <>
                {/* Search */}
                <div className="p-4 pb-2">
                  <input
                    type="text"
                    placeholder="Cari nama atau no HP..."
                    value={customerSearch}
                    onChange={(e) => setCustomerSearch(e.target.value)}
                    className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
                    autoFocus
                  />
                </div>

                {/* Customer List */}
                <div className="flex-1 overflow-auto px-4">
                  {searchLoading ? (
                    <div className="text-center py-8 text-gray-400">Mencari...</div>
                  ) : customers.length > 0 ? (
                    <div className="space-y-2 pb-4">
                      {customers.map((c) => (
                        <button
                          key={c.id}
                          onClick={() => selectCustomer(c)}
                          className="w-full text-left bg-gray-50 hover:bg-[var(--gold)]/10 rounded-xl p-3 transition-colors"
                        >
                          <p className="font-medium text-[var(--charcoal)]">{c.name}</p>
                          {c.phone && <p className="text-sm text-gray-500">{c.phone}</p>}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-400">
                      {customerSearch ? 'Tidak ditemukan' : 'Belum ada pelanggan'}
                    </div>
                  )}
                </div>

                {/* Add New Button */}
                <div className="p-4 border-t border-gray-100">
                  <button
                    onClick={() => {
                      setShowAddNew(true);
                      setNewCustomer({ name: customerSearch, phone: '' });
                    }}
                    className="w-full bg-[var(--gold)] text-white py-3 rounded-xl font-semibold text-sm active:opacity-90"
                  >
                    ➕ Tambah Pelanggan Baru
                  </button>
                  <button
                    onClick={() => {
                      selectCustomer({ id: '', name: 'Tamu', phone: '' });
                    }}
                    className="w-full py-3 text-gray-400 text-sm mt-2"
                  >
                    Lewati (Tamu)
                  </button>
                </div>
              </>
            ) : (
              /* Add New Customer Form */
              <div className="flex-1 p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nama *</label>
                  <input
                    type="text"
                    placeholder="Nama pelanggan"
                    value={newCustomer.name}
                    onChange={(e) => setNewCustomer({ ...newCustomer, name: e.target.value })}
                    className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">No. HP</label>
                  <input
                    type="tel"
                    placeholder="08xxx (opsional)"
                    value={newCustomer.phone}
                    onChange={(e) => setNewCustomer({ ...newCustomer, phone: e.target.value })}
                    className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
                  />
                </div>
                <div className="flex gap-3 pt-4">
                  <button
                    onClick={() => setShowAddNew(false)}
                    className="flex-1 border border-gray-200 text-gray-600 py-3 rounded-xl font-medium"
                  >← Kembali</button>
                  <button
                    onClick={createAndSelectCustomer}
                    disabled={loading || !newCustomer.name.trim()}
                    className="flex-1 bg-[var(--gold)] text-white py-3 rounded-xl font-semibold disabled:opacity-50"
                  >{loading ? 'Saving...' : 'Simpan & Pilih'}</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
