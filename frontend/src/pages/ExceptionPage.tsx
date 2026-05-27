import { useState, useEffect } from 'react';
import { exceptionApi } from '@/api/client';
import { ExceptionItem, EXCEPTION_TYPE_LABELS } from '@/types';
import StatusBadge from '@/components/common/StatusBadge';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';

const PRIORITY_COLORS = {
  critical: 'bg-red-50 border-red-200',
  high: 'bg-yellow-50 border-yellow-200',
  medium: 'bg-white border-gray-200',
};

export default function ExceptionPage() {
  const [exceptions, setExceptions] = useState<ExceptionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadExceptions();
  }, [filter]);

  const loadExceptions = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filter !== 'all') params.status = filter;
      const data = await exceptionApi.list(params);
      setExceptions(data);
    } catch { /* empty */ }
    setLoading(false);
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
          {exceptions.map(exc => (
            <div
              key={exc.exceptionId}
              className={`rounded-xl border p-4 ${PRIORITY_COLORS[exc.priority]} ${exc.isOverdue ? 'ring-2 ring-red-400' : ''}`}
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className="text-sm font-mono text-gray-500">{exc.exceptionId}</p>
                  <p className="font-semibold text-charcoal">{EXCEPTION_TYPE_LABELS[exc.exceptionType]}</p>
                </div>
                <StatusBadge
                  label={exc.priority.toUpperCase()}
                  variant={exc.priority === 'critical' ? 'danger' : exc.priority === 'high' ? 'warning' : 'neutral'}
                />
              </div>
              {exc.posCode && <p className="text-sm text-gray-600">POS: {exc.posCode}</p>}
              <div className="flex items-center justify-between mt-2">
                <span className="text-xs text-gray-500">
                  {new Date(exc.createdAt).toLocaleString('id-ID')}
                  {exc.isOverdue && <span className="ml-2 text-red-600 font-medium">⚠ Terlambat</span>}
                </span>
                <StatusBadge
                  label={exc.status}
                  variant={exc.status === 'RESOLVED' ? 'success' : exc.status === 'ESCALATED' ? 'danger' : 'info'}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
