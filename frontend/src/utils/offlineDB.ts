/**
 * Offline DB - IndexedDB wrapper for POS offline support.
 *
 * Stores:
 * - Pending transactions (created offline)
 * - Cached master data (treatments, products, customers)
 * - Queued API requests
 */

const DB_NAME = 'beauty-shine-offline';
const DB_VERSION = 1;

const STORES = {
  PENDING_TXNS: 'pending_transactions',
  MASTER_CACHE: 'master_cache',
  API_QUEUE: 'api_queue',
};

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORES.PENDING_TXNS)) {
        db.createObjectStore(STORES.PENDING_TXNS, { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains(STORES.MASTER_CACHE)) {
        db.createObjectStore(STORES.MASTER_CACHE, { keyPath: 'key' });
      }
      if (!db.objectStoreNames.contains(STORES.API_QUEUE)) {
        const store = db.createObjectStore(STORES.API_QUEUE, {
          keyPath: 'id',
          autoIncrement: true,
        });
        store.createIndex('timestamp', 'timestamp');
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// ── Pending Transactions ────────────────────────────────────────

export interface PendingTransaction {
  id: string;
  data: any;
  timestamp: number;
  synced: boolean;
}

export async function savePendingTransaction(txn: any): Promise<void> {
  const db = await openDB();
  const tx = db.transaction(STORES.PENDING_TXNS, 'readwrite');
  const store = tx.objectStore(STORES.PENDING_TXNS);
  store.put({
    id: txn.id || `offline-${Date.now()}`,
    data: txn,
    timestamp: Date.now(),
    synced: false,
  });
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getPendingTransactions(): Promise<PendingTransaction[]> {
  const db = await openDB();
  const tx = db.transaction(STORES.PENDING_TXNS, 'readonly');
  const store = tx.objectStore(STORES.PENDING_TXNS);
  const request = store.getAll();
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result || []);
    request.onerror = () => reject(request.error);
  });
}

export async function removePendingTransaction(id: string): Promise<void> {
  const db = await openDB();
  const tx = db.transaction(STORES.PENDING_TXNS, 'readwrite');
  const store = tx.objectStore(STORES.PENDING_TXNS);
  store.delete(id);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getPendingTransactionCount(): Promise<number> {
  const db = await openDB();
  const tx = db.transaction(STORES.PENDING_TXNS, 'readonly');
  const store = tx.objectStore(STORES.PENDING_TXNS);
  const request = store.count();
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// ── Master Data Cache ───────────────────────────────────────────

export async function cacheMasterData(key: string, data: any): Promise<void> {
  const db = await openDB();
  const tx = db.transaction(STORES.MASTER_CACHE, 'readwrite');
  const store = tx.objectStore(STORES.MASTER_CACHE);
  store.put({ key, data, cachedAt: Date.now() });
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getCachedMasterData(key: string): Promise<any | null> {
  const db = await openDB();
  const tx = db.transaction(STORES.MASTER_CACHE, 'readonly');
  const store = tx.objectStore(STORES.MASTER_CACHE);
  const request = store.get(key);
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result?.data || null);
    request.onerror = () => reject(request.error);
  });
}

// ── API Request Queue ───────────────────────────────────────────

export interface QueuedRequest {
  id?: number;
  url: string;
  method: string;
  headers: Record<string, string>;
  body: string | null;
  timestamp: number;
}

export async function queueApiRequest(req: QueuedRequest): Promise<void> {
  const db = await openDB();
  const tx = db.transaction(STORES.API_QUEUE, 'readwrite');
  const store = tx.objectStore(STORES.API_QUEUE);
  store.add({ ...req, timestamp: Date.now() });
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getQueuedRequests(): Promise<QueuedRequest[]> {
  const db = await openDB();
  const tx = db.transaction(STORES.API_QUEUE, 'readonly');
  const store = tx.objectStore(STORES.API_QUEUE);
  const request = store.getAll();
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result || []);
    request.onerror = () => reject(request.error);
  });
}

export async function clearApiQueue(): Promise<void> {
  const db = await openDB();
  const tx = db.transaction(STORES.API_QUEUE, 'readwrite');
  const store = tx.objectStore(STORES.API_QUEUE);
  store.clear();
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function removeQueuedRequest(id: number): Promise<void> {
  const db = await openDB();
  const tx = db.transaction(STORES.API_QUEUE, 'readwrite');
  const store = tx.objectStore(STORES.API_QUEUE);
  store.delete(id);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
