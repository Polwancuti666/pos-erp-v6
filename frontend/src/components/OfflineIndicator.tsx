import { useOnlineStatus } from '../hooks/useOnlineStatus';

export default function OfflineIndicator() {
  const { isOnline, wasOffline, pendingCount, syncNow } = useOnlineStatus();

  // Show indicator when offline, or when just came back online with pending items
  if (isOnline && !wasOffline && pendingCount === 0) return null;

  return (
    <div
      className={`fixed top-0 left-0 right-0 z-[100] px-4 py-2 text-center text-sm font-medium transition-all ${
        isOnline
          ? 'bg-green-600 text-white'
          : 'bg-red-600 text-white animate-pulse'
      }`}
    >
      <div className="flex items-center justify-center gap-3">
        {isOnline ? (
          <>
            <span>🟢 Online</span>
            {pendingCount > 0 && (
              <button
                onClick={syncNow}
                className="bg-white/20 hover:bg-white/30 px-3 py-1 rounded-full text-xs transition-colors"
              >
                🔄 Sync {pendingCount} pending
              </button>
            )}
          </>
        ) : (
          <>
            <span>🔴 Offline</span>
            {pendingCount > 0 && (
              <span className="bg-white/20 px-3 py-1 rounded-full text-xs">
                {pendingCount} queued for sync
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
}
