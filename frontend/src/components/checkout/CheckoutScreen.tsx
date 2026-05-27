import { useState, useCallback } from 'react';
import CustomerBar from './CustomerBar';
import CartArea from './CartArea';
import SummaryBar from './SummaryBar';
import PaymentMethodSelector from './PaymentMethodSelector';
import CashPaymentPanel from './CashPaymentPanel';
import QrisPaymentPanel from './QrisPaymentPanel';
import BankTransferPanel from './BankTransferPanel';
import StaffLockCountdown from './StaffLockCountdown';
import ErrorToast from './ErrorToast';
import { useStaffLockManager } from '../../hooks/useStaffLockManager';
import type {
  Transaction,
  CartItem,
  Customer,
  PaymentMethod,
  PaymentIntent,
  ToastMessage,
} from '../../types';

export default function CheckoutScreen() {
  const staffLock = useStaffLockManager();

  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [selectedPaymentMethod, setSelectedPaymentMethod] =
    useState<PaymentMethod | null>(null);
  const [paymentIntent, setPaymentIntent] = useState<PaymentIntent | null>(
    null
  );
  const [isProcessing, setIsProcessing] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback(
    (toast: Omit<ToastMessage, 'id'>) => {
      const id = Date.now().toString();
      setToasts((prev) => [...prev, { ...toast, id }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, toast.duration || 5000);
    },
    []
  );

  const subtotal = cartItems.reduce((sum, item) => sum + item.subtotal, 0);
  const totalDiscount = cartItems.reduce(
    (sum, item) => sum + item.discount + (item.promoDiscount || 0),
    0
  );
  const tax = Math.round((subtotal - totalDiscount) * 0.11);
  const total = subtotal - totalDiscount + tax;

  const handleAddItem = useCallback((item: CartItem) => {
    setCartItems((prev) => {
      const existing = prev.find((i) => i.serviceId === item.serviceId);
      if (existing) {
        return prev.map((i) =>
          i.serviceId === item.serviceId
            ? { ...i, quantity: i.quantity + 1, subtotal: (i.quantity + 1) * i.price }
            : i
        );
      }
      return [...prev, item];
    });
  }, []);

  const handleRemoveItem = useCallback((itemId: string) => {
    setCartItems((prev) => prev.filter((i) => i.id !== itemId));
  }, []);

  const handleUpdateQuantity = useCallback((itemId: string, quantity: number) => {
    if (quantity <= 0) {
      handleRemoveItem(itemId);
      return;
    }
    setCartItems((prev) =>
      prev.map((i) =>
        i.id === itemId
          ? { ...i, quantity, subtotal: quantity * i.price }
          : i
      )
    );
  }, [handleRemoveItem]);

  const handleSelectPayment = useCallback((method: PaymentMethod) => {
    setSelectedPaymentMethod(method);
  }, []);

  const handleSubmitCheckout = useCallback(async () => {
    setIsProcessing(true);
    try {
      // API call would go here
      addToast({
        type: 'success',
        title: 'Checkout berhasil',
        message: 'Transaksi sedang diproses',
      });
    } catch {
      addToast({
        type: 'error',
        title: 'Gagal checkout',
        message: 'Silakan coba lagi',
      });
    } finally {
      setIsProcessing(false);
    }
  }, [addToast]);

  const handleConfirmCash = useCallback(
    async (amount: number) => {
      setIsProcessing(true);
      try {
        const change = amount - total;
        addToast({
          type: 'success',
          title: 'Pembayaran tunai diterima',
          message: `Kembalian: Rp ${change.toLocaleString('id-ID')}`,
        });
      } catch {
        addToast({
          type: 'error',
          title: 'Gagal konfirmasi pembayaran',
        });
      } finally {
        setIsProcessing(false);
      }
    },
    [total, addToast]
  );

  return (
    <div className="space-y-4">
      {/* Staff Lock Countdown */}
      {staffLock.isLocked && (
        <StaffLockCountdown
          staffName={staffLock.staffName || ''}
          remainingSeconds={staffLock.remainingSeconds}
          isExpiringSoon={staffLock.isExpiringSoon}
          isCritical={staffLock.isCritical}
          onRelease={staffLock.releaseLock}
        />
      )}

      {/* Customer Bar */}
      <CustomerBar customer={customer} onCustomerChange={setCustomer} />

      {/* Cart Area */}
      <CartArea
        items={cartItems}
        onAddItem={handleAddItem}
        onRemoveItem={handleRemoveItem}
        onUpdateQuantity={handleUpdateQuantity}
      />

      {/* Summary Bar */}
      <SummaryBar
        subtotal={subtotal}
        discount={totalDiscount}
        tax={tax}
        total={total}
        itemCount={cartItems.length}
      />

      {/* Payment Method Selector */}
      <PaymentMethodSelector
        selected={selectedPaymentMethod}
        onSelect={handleSelectPayment}
        disabled={cartItems.length === 0}
      />

      {/* Payment Panels */}
      {selectedPaymentMethod === 'CASH' && (
        <CashPaymentPanel
          total={total}
          onConfirm={handleConfirmCash}
          isProcessing={isProcessing}
        />
      )}

      {selectedPaymentMethod === 'QRIS' && (
        <QrisPaymentPanel
          paymentIntent={paymentIntent}
          transactionId={transaction?.id || null}
          onPaymentComplete={() => {
            addToast({ type: 'success', title: 'Pembayaran QRIS berhasil' });
          }}
        />
      )}

      {selectedPaymentMethod === 'BANK_TRANSFER' && (
        <BankTransferPanel
          paymentIntent={paymentIntent}
          isProcessing={isProcessing}
        />
      )}

      {/* Submit Button */}
      {cartItems.length > 0 && !selectedPaymentMethod && (
        <button
          onClick={handleSubmitCheckout}
          disabled={isProcessing || cartItems.length === 0}
          className="btn-primary w-full text-lg py-4"
        >
          {isProcessing ? 'Memproses...' : `Bayar Rp ${total.toLocaleString('id-ID')}`}
        </button>
      )}

      {/* Error Toasts */}
      <ErrorToast toasts={toasts} onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))} />
    </div>
  );
}
