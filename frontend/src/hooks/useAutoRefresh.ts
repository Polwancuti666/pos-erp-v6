import { useState, useEffect, useCallback, useRef } from 'react';

interface AutoRefreshState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

export function useAutoRefresh<T>(
  fetchFn: () => Promise<T>,
  intervalMs: number = 300000, // 5 minutes default
  immediate: boolean = true,
) {
  const [state, setState] = useState<AutoRefreshState<T>>({
    data: null,
    loading: immediate,
    error: null,
    lastUpdated: null,
  });

  const fetchRef = useRef(fetchFn);
  fetchRef.current = fetchFn;

  const refresh = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const data = await fetchRef.current();
      setState({ data, loading: false, error: null, lastUpdated: new Date() });
    } catch (err) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Gagal memuat data',
      }));
    }
  }, []);

  useEffect(() => {
    if (immediate) refresh();
    const interval = setInterval(refresh, intervalMs);
    return () => clearInterval(interval);
  }, [refresh, intervalMs, immediate]);

  return { ...state, refresh };
}
