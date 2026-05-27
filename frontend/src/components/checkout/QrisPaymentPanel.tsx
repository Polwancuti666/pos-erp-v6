import { useQrisCountdown } from '@/hooks/useQrisCountdown';

interface Props {
  paymentIntentId: string;
  qrisImageUrl: string;
  expiresAt: string;
  onPaid?: () => void;
  onExpired?: () => void;
}

const COLOR_CLASSES = {
  green: 'text-green-600 bg-green-50',
  yellow: 'text-yellow-600 bg-yellow-50',
  red: 'text-red-600 bg-red-50',
};

export default function QrisPaymentPanel({ paymentIntentId, qrisImageUrl, expiresAt, onPaid, onExpired }: Props) {
  const { remaining, color, isExpired, isPaid, formatTime } =
    useQrisCountdown(paymentIntentId, expiresAt, onPaid, onExpired);

  return (
    <div className="flex flex-col items-center gap-4 p-4">
      {/* QR Code */}
      <div className="w-full max-w-[280px] aspect-square bg-white rounded-2xl border-2 border-gray-100 flex items-center justify-center p-4 shadow-sm">
        {isPaid ? (
          <div className="text-center">
            <div className="text-5xl mb-2">✅</div>
            <p className="text-green-600 font-semibold">Pembayaran Berhasil</p>
          </div>
        ) : isExpired ? (
          <div className="text-center">
            <div className="text-5xl mb-2">⏰</div>
            <p className="text-red-600 font-semibold">QR Sudah Kadaluarsa</p>
            <p className="text-sm text-gray-500 mt-1">Silakan buat ulang</p>
          </div>
        ) : (
          <img src={qrisImageUrl} alt="QRIS Code" className="w-full h-full object-contain" />
        )}
      </div>

      {/* Countdown */}
      {!isPaid && (
        <div className={`px-6 py-3 rounded-xl font-mono text-2xl font-bold ${COLOR_CLASSES[color]}`}>
          {formatTime(remaining)}
        </div>
      )}

      {/* Instructions */}
      <p className="text-sm text-gray-500 text-center">
        {isPaid ? 'Transaksi selesai!' :
         isExpired ? 'QR sudah kadaluarsa' :
         'Scan QR code dengan aplikasi pembayaran Anda'}
      </p>
    </div>
  );
}
