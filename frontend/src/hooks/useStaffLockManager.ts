import { useState, useEffect, useCallback, useRef } from 'react';
import { transactionApi } from '@/api/client';
import { ERROR_MESSAGES } from '@/types';

interface StaffLockState {
  remaining: number;      // seconds
  isExpired: boolean;
  replaced: boolean;
  newStaffName: string | null;
  cancelled: boolean;
  color: 'green' | 'yellow' | 'red';
}

export function useStaffLockManager(
  transactionId: string | null,
  expiresAt: string | null,
  onStaffReplaced?: (newStaffName: string) => void,
  onTransactionCancelled?: () => void,
) {
  const [state, setState] = useState<StaffLockState>({
    remaining: 0,
    isExpired: false,
    replaced: false,
    newStaffName: null,
    cancelled: false,
    color: 'green',
  });

  const replacementCalled = useRef(false);

  useEffect(() => {
    if (!expiresAt || !transactionId) return;

    const interval = setInterval(() => {
      const now = Date.now();
      const expiry = new Date(expiresAt).getTime();
      const remaining = Math.max(0, Math.floor((expiry - now) / 1000));

      let color: 'green' | 'yellow' | 'red' = 'green';
      if (remaining <= 60) color = 'red';
      else if (remaining <= 180) color = 'yellow';

      setState(prev => ({ ...prev, remaining, color, isExpired: remaining <= 0 }));

      if (remaining <= 0 && !replacementCalled.current) {
        replacementCalled.current = true;
        requestReplacement(transactionId);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [expiresAt, transactionId]);

  const requestReplacement = useCallback(async (txId: string) => {
    try {
      const result = await transactionApi.requestStaffReplacement(txId);
      if (result.replaced) {
        setState(prev => ({
          ...prev,
          replaced: true,
          newStaffName: result.newStaffName,
        }));
        onStaffReplaced?.(result.newStaffName);
      } else {
        setState(prev => ({ ...prev, cancelled: true }));
        onTransactionCancelled?.();
      }
    } catch {
      setState(prev => ({ ...prev, cancelled: true }));
      onTransactionCancelled?.();
    }
  }, [onStaffReplaced, onTransactionCancelled]);

  const formatTime = useCallback((seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }, []);

  return { ...state, formatTime };
}
