import { useState, useEffect, useCallback } from 'react';
import { paymentApi } from '@/api/client';

interface QrisState {
  remaining: number;      // seconds
  color: 'green' | 'yellow' | 'red';
  isExpired: boolean;
  isPaid: boolean;
  status: string;
}

export function useQrisCountdown(
  paymentIntentId: string | null,
  expiresAt: string | null,
  onPaid?: () => void,
  onExpired?: () => void,
) {
  const [state, setState] = useState<QrisState>({
    remaining: 0,
    color: 'green',
    isExpired: false,
    isPaid: false,
    status: 'PENDING',
  });

  // Countdown timer
  useEffect(() => {
    if (!expiresAt || state.isPaid) return;

    const interval = setInterval(() => {
      const now = Date.now();
      const expiry = new Date(expiresAt).getTime();
      const remaining = Math.max(0, Math.floor((expiry - now) / 1000));

      let color: 'green' | 'yellow' | 'red' = 'green';
      if (remaining <= 300) color = 'red';       // < 5 min
      else if (remaining <= 600) color = 'yellow'; // 5-10 min

      setState(prev => ({ ...prev, remaining, color, isExpired: remaining <= 0 }));

      if (remaining <= 0) {
        clearInterval(interval);
        onExpired?.();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [expiresAt, state.isPaid, onExpired]);

  // Polling QRIS status every 3 seconds
  useEffect(() => {
    if (!paymentIntentId || state.isPaid || state.isExpired) return;

    const poll = setInterval(async () => {
      try {
        const result = await paymentApi.getQrisStatus(paymentIntentId);
        if (result.status === 'PAID' || result.status === 'GATEWAY_PAID') {
          setState(prev => ({ ...prev, isPaid: true, status: 'PAID' }));
          clearInterval(poll);
          onPaid?.();
        }
      } catch {
        // Silently retry on next interval
      }
    }, 3000);

    return () => clearInterval(poll);
  }, [paymentIntentId, state.isPaid, state.isExpired, onPaid]);

  const formatTime = useCallback((seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }, []);

  return { ...state, formatTime };
}
