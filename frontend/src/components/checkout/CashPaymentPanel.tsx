import { useState, useMemo } from 'react';

interface Props {
  total: number;
  onConfirm: (amountReceived: number) => void;
  loading?: boolean;
}

const QUICK_AMOUNTS = [10000, 50000, 100000];

export default function CashPaymentPanel({ total, onConfirm, loading }: Props) {
  const [amountStr, setAmountStr] = useState('');

  const amountReceived = useMemo(() => {
    const parsed = parseInt(amountStr.replace(/[^0-9]/g, ''), 10);
    return isNaN(parsed) ? 0 : parsed;
  }, [amountStr]);

  const change = amountReceived - total;
  const isValid = amountReceived >= total;

  const formatRp = (n: number) => 'Rp ' + n.toLocaleString('id-ID');

  return (
    <div className="p-4 space-y-4">
      {/* Total */}
      <div className="bg-ivory-warm rounded-xl p-4 text-center">
        <p className="text-sm text-gray-500 mb-1">Total Tagihan</p>
        <p className="text-2xl font-bold text-charcoal">{formatRp(total)}</p>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <label className="text-sm text-gray-500 block mb-2">Uang Diterima</label>
        <input
          type="text"
          inputMode="numeric"
          value={amountStr}
          onChange={e => setAmountStr(e.target.value)}
          placeholder="0"
          className="w-full text-2xl font-bold text-charcoal text-center outline-none bg-transparent"
        />
      </div>

      {/* Quick buttons */}
      <div className="flex gap-2">
        {QUICK_AMOUNTS.map(amt => (
          <button
            key={amt}
            onClick={() => setAmountStr(String(amt))}
            className="flex-1 py-2 bg-gray-100 rounded-lg text-sm font-medium text-charcoal active:bg-gray-200"
          >
            +{formatRp(amt)}
          </button>
        ))}
        <button
          onClick={() => setAmountStr(String(total))}
          className="flex-1 py-2 bg-gold/10 text-gold rounded-lg text-sm font-medium active:bg-gold/20"
        >
          Uang Pas
        </button>
      </div>

      {/* Change */}
      {amountReceived > 0 && (
        <div className={`rounded-xl p-4 text-center ${isValid ? 'bg-green-50' : 'bg-red-50'}`}>
          <p className="text-sm text-gray-500 mb-1">{isValid ? 'Kembalian' : 'Kurang'}</p>
          <p className={`text-xl font-bold ${isValid ? 'text-green-600' : 'text-red-600'}`}>
            {formatRp(Math.abs(change))}
          </p>
        </div>
      )}

      {/* Confirm */}
      <button
        disabled={!isValid || loading}
        onClick={() => onConfirm(amountReceived)}
        className="w-full py-4 bg-gold text-white rounded-xl font-semibold text-lg disabled:opacity-40 disabled:cursor-not-allowed active:bg-gold/90 transition-colors"
      >
        {loading ? 'Memproses...' : 'Konfirmasi Pembayaran'}
      </button>
    </div>
  );
}
