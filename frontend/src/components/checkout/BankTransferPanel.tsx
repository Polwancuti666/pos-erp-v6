interface Props {
  bankName: string;
  accountNumber: string;
  amount: number;
}

export default function BankTransferPanel({ bankName, accountNumber, amount }: Props) {
  const formatRp = (n: number) => 'Rp ' + n.toLocaleString('id-ID');

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="p-4 space-y-4">
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        <div>
          <p className="text-xs text-gray-500">Bank</p>
          <p className="text-lg font-semibold text-charcoal">{bankName}</p>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-500">Nomor Rekening</p>
            <p className="text-lg font-mono font-semibold text-charcoal">{accountNumber}</p>
          </div>
          <button
            onClick={() => copyToClipboard(accountNumber)}
            className="px-3 py-2 bg-gray-100 rounded-lg text-sm font-medium active:bg-gray-200"
          >
            Salin
          </button>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-500">Nominal</p>
            <p className="text-lg font-bold text-gold">{formatRp(amount)}</p>
          </div>
          <button
            onClick={() => copyToClipboard(String(amount))}
            className="px-3 py-2 bg-gray-100 rounded-lg text-sm font-medium active:bg-gray-200"
          >
            Salin
          </button>
        </div>
      </div>

      <div className="bg-yellow-50 rounded-xl p-4 text-center">
        <p className="text-sm text-yellow-700">
          Menunggu Konfirmasi Transfer<br />
          <span className="text-xs text-yellow-600">Cashier akan memverifikasi setelah transfer diterima</span>
        </p>
      </div>
    </div>
  );
}
