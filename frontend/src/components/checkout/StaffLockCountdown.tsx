import { useStaffLockManager } from '@/hooks/useStaffLockManager';
import { ERROR_MESSAGES } from '@/types';
import Modal from '@/components/common/Modal';

interface Props {
  transactionId: string;
  expiresAt: string | null;
  staffName: string;
  onReplaced?: (name: string) => void;
  onCancelled?: () => void;
}

const COLOR_MAP = {
  green: 'bg-green-500',
  yellow: 'bg-yellow-500',
  red: 'bg-red-500',
};

export default function StaffLockCountdown({ transactionId, expiresAt, staffName, onReplaced, onCancelled }: Props) {
  const { remaining, isExpired, replaced, newStaffName, cancelled, color, formatTime } =
    useStaffLockManager(transactionId, expiresAt, onReplaced, onCancelled);

  if (!expiresAt) return null;

  return (
    <>
      <div className="flex items-center gap-2 px-3 py-2 bg-white rounded-xl border border-gray-100 shadow-sm">
        <div className={`w-2.5 h-2.5 rounded-full ${COLOR_MAP[color]} ${isExpired ? 'animate-pulse' : ''}`} />
        <div className="flex-1">
          <p className="text-xs text-gray-500">Staff Terkunci</p>
          <p className="text-sm font-semibold text-charcoal">
            {staffName} — {formatTime(remaining)}
          </p>
        </div>
      </div>

      {/* Toast: Staff replaced */}
      {replaced && newStaffName && (
        <div className="fixed top-16 inset-x-0 flex justify-center z-50 animate-fade-in">
          <div className="bg-green-600 text-white px-4 py-2 rounded-xl shadow-lg text-sm">
            {ERROR_MESSAGES.STAFF_REPLACED(newStaffName)}
          </div>
        </div>
      )}

      {/* Modal: No staff available */}
      <Modal open={cancelled} onClose={() => {}} title="Transaksi Dibatalkan">
        <p>{ERROR_MESSAGES.NO_STAFF_AVAILABLE}</p>
        <div className="mt-4">
          <button onClick={onCancelled} className="w-full bg-charcoal text-white py-3 rounded-xl font-medium">
            Mulai Transaksi Baru
          </button>
        </div>
      </Modal>
    </>
  );
}
