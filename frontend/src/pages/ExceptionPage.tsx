import { useState, useEffect } from 'react';
import { exceptionApi } from '@/api/client';
import StatusBadge from '@/components/common/StatusBadge';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';

interface ExceptionItem {
  exception_id: string;
  exception_type: string;
  reference_id: string;
  created_at: string;
  owner_roles: string[];
  sla_hours: number;
  status: string;
  resolved_by: string | null;
  resolution: string | null;
}

interface ExceptionResponse {
  total: number;
  items: ExceptionItem[];
}

const TYPE_LABELS: Record<string, string> = {
  SYNC_FAILURE: 'Gagal Sinkronisasi',
  UNMAPPED_COA: 'COA Belum Di-mapping',
  PAYMENT_REVIEW_REQUIRED: 'Pembayaran Perlu Review',
  RECONCILIATION_MISMATCH: 'Ketidakcocokan Rekonsiliasi',
  DUPLICATE_EVENT: 'Duplikat Event',
  PAYLOAD_VALIDATION: 'Validasi Payload Gagal',
};

const PRIORITY_MAP: Record<string, { color: string; label: string }> = {
  PAYMENT_REVIEW_REQUIRED: { color: 'bg-red-50 border-red-200', label: 'Critical' },
  RECONCILIATION_MISMATCH: { color: 'bg-red-50 border-red-200', label: 'Critical' },
  SYNC_FAILURE: { color: 'bg-yellow-50 border-yellow-200', label: 'High' },
  UNMAPPED_COA: { color: 'bg-yellow-50 border-yellow-200', label: 'High' },
  PAYLOAD_VALIDATION: { color: 'bg-yellow-50 border-yellow-200', label: 'High' },
  DUPLICATE_EVENT: { color: 'bg-white border-gray-200', label: 'Medium' },
};

export default function ExceptionPage() {
  const [exceptions, setExceptions] = useState<ExceptionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => { loadExceptions(); }, [filter]);

  const loadExceptions = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filter !== 'all') params.status = filter;
      const data: ExceptionResponse = await exceptionApi.list(params);
      setExceptions(data.items || []);
    } catch { /* empty */ }
    setLoading(false);
  };

  const isOverdue = (exc: ExceptionItem) => {
    const created = new Date(exc.created_at).getTime();
    const deadline = created + exc.sla_hours * 3600000;
    return Date.now() > deadline && exc.status === 'OPEN';
  };

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-charcoal">Exception Queue</h2>

      {/* Filters */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {['all', 'OPEN', 'IN_REVIEW', 'RESOLVED'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap ${
              filter === f ? 'bg-gold text-white' : 'bg-gray-100 text-gray-600'
            }`}
          >
            {f === 'all' ? 'Semua' : f}
          </button>
        ))}
      </div>

      {loading ? <LoadingSkeleton /> : (
        <div className="space-y-2">
          {exceptions.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <p className="text-4xl mb-2">✅</p>
              <p>Tidak ada exception</p>
            </div>
          )}
          {exceptions.map(exc => {
            const prio = PRIORITY_MAP[exc.exception_type] || { color: 'bg-white border-gray-200', label: 'Medium' };
            const overdue = isOverdue(exc);
            return (
              <div
                key={exc.exception_id}
                className={`rounded-xl border p-4 ${prio.color} ${overdue ? 'ring-2 ring-red-400' : ''}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <p className="text-sm font-mono text-gray-500">{exc.exception_id}</p>
                    <p className="font-semibold text-charcoal">{TYPE_LABELS[exc.exception_type] || exc.exception_type}</p>
                  </div>
                  <StatusBadge
                    label={prio.label}
                    variant={prio.label === 'Critical' ? 'danger' : prio.label === 'High' ? 'warning' : 'neutral'}
                  />
                </div>
                <p className="text-sm text-gray-600">Ref: {exc.reference_id}</p>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-gray-500">
                    {new Date(exc.created_at).toLocaleString('id-ID')}
                    {overdue && <span className="ml-2 text-red-600 font-medium">⚠ Terlambat</span>}
                  </span>
                  <StatusBadge
                    label={exc.status}
                    variant={exc.status === 'RESOLVED' ? 'success' : exc.status === 'ESCALATED' ? 'danger' : 'info'}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
