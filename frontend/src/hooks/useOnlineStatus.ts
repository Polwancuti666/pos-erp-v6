import { useState, useEffect, useCallback } from 'react';
import { getPendingTransactionCount, getQueuedRequests } from '../utils/offlineDB';

interface OnlineStatus {
  isOnline: boolean;
  wasOffline: boolean;
  pendingCount: number;
  syncNow: () => Promise<void>;
}

export function useOnlineStatus(): OnlineStatus {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [wasOffline, setWasOffline] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  const updatePendingCount = useCallback(async () => {
    try {
      const txns = await getPendingTransactionCount();
      const queue = await getQueuedRequests();
      setPendingCount(txns + queue.length);
    } catch {
      setPendingCount(0);
    }
  }, []);

  const syncNow = useCallback(async () => {
    try {
      const { getQueuedRequests: getQR, removeQueuedRequest } = await import('../utils/offlineDB');
      const queue = await getQR();
      for (const req of queue) {
        try {
          await fetch(req.url, {
            method: req.method,
            headers: req.headers,
            body: req.body,
          });
          if (req.id) await removeQueuedRequest(req.id);
        } catch {
          // Still offline, stop trying
          break;
        }
      }
      await updatePendingCount();
    } catch {
      // ignore
    }
  }, [updatePendingCount]);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setWasOffline(true);
      // Auto-sync when coming back online
      syncNow();
      // Clear wasOffline after 5 seconds
      setTimeout(() => setWasOffline(false), 5000);
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Listen for service worker messages
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'QUEUE_REQUEST') {
        import('../utils/offlineDB').then(({ queueApiRequest }) => {
          queueApiRequest(event.data.payload);
          updatePendingCount();
        });
      }
      if (event.data?.type === 'SYNC_START') {
        syncNow();
      }
    };
    navigator.serviceWorker?.addEventListener('message', handleMessage);

    // Initial count
    updatePendingCount();

    // Periodic count update
    const interval = setInterval(updatePendingCount, 10000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      navigator.serviceWorker?.removeEventListener('message', handleMessage);
      clearInterval(interval);
    };
  }, [syncNow, updatePendingCount]);

  return { isOnline, wasOffline, pendingCount, syncNow };
}
