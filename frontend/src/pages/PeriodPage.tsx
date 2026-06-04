import { useState, useEffect } from 'react';
import { api } from '../api/client';

interface FinancialPeriod {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: 'open' | 'closed' | 'locked';
  branch_id: string;
  branch_name: string;
  year: number;
  month: number;
  closed_at?: string;
  closed_by?: string;
}

interface PeriodClosing {
  id: string;
  period: string;
  status: string;
  branch_id: string;
  branch_name: string;
  closed_at: string;
  closed_by: string;
  reviewed_at?: string;
  reviewed_by?: string;
  checklist: Array<{ item: string; completed: boolean }>;
}

interface PeriodStatus {
  current_period: string;
  is_locked: boolean;
  days_remaining: number;
}

export default function PeriodPage() {
  const [periods, setPeriods] = useState<FinancialPeriod[]>([]);
  const [closings, setClosings] = useState<PeriodClosing[]>([]);
  const [status, setStatus] = useState<PeriodStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Unlock modal
  const [unlockModal, setUnlockModal] = useState<FinancialPeriod | null>(null);
  const [unlockReason, setUnlockReason] = useState('');
  const [unlockBy, setUnlockBy] = useState('');

  // Create closing modal
  const [showCreateClosing, setShowCreateClosing] = useState(false);
  const [closingPeriod, setClosingPeriod] = useState('');
  const [closingBranch, setClosingBranch] = useState('');

  const fetchData = () => {
    Promise.all([
      api.getFinancialPeriods(),
      api.getPeriodClosings(),
      api.getPeriodStatus(),
    ])
      .then(([p, c, s]) => {
        setPeriods(Array.isArray(p) ? p : p.items || p.data || []);
        setClosings(Array.isArray(c) ? c : c.items || c.data || []);
        setStatus(s.data || s.items || s);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'bg-green-100 text-green-700 border-green-300';
      case 'closed': return 'bg-gray-100 text-gray-700 border-gray-300';
      case 'locked': return 'bg-red-100 text-red-700 border-red-300';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getClosingStatusColor = (status: string) => {
    switch (status) {
      case 'draft': return 'bg-yellow-100 text-yellow-700 border-yellow-300';
      case 'reviewed': return 'bg-blue-100 text-blue-700 border-blue-300';
      case 'closed': return 'bg-green-100 text-green-700 border-green-300';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  // ── Lock Period ──────────────────────────────────────────────
  const handleLock = async (period: FinancialPeriod) => {
    if (!confirm(`Lock period ${period.name}? Transactions will be blocked.`)) return;
    setActionLoading(`lock-${period.id}`);
    try {
      await api.lockPeriod(period.id);
      fetchData();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // ── Unlock Period ────────────────────────────────────────────
  const handleUnlock = async () => {
    if (!unlockModal || !unlockReason.trim()) {
      alert('Reason is required to unlock');
      return;
    }
    setActionLoading(`unlock-${unlockModal.id}`);
    try {
      await api.unlockPeriod(unlockModal.id, {
        period_id: unlockModal.id,
        unlocked_by: unlockBy,
        reason: unlockReason,
      });
      setUnlockModal(null);
      setUnlockReason('');
      setUnlockBy('');
      fetchData();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // ── Create Closing ───────────────────────────────────────────
  const handleCreateClosing = async () => {
    setActionLoading('create-closing');
    try {
      await api.createPeriodClosing(closingBranch, closingPeriod);
      setShowCreateClosing(false);
      setClosingPeriod('');
      setClosingBranch('');
      fetchData();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // ── Toggle Checklist ─────────────────────────────────────────
  const handleToggleChecklist = async (closing: PeriodClosing, itemName: string, currentCompleted: boolean) => {
    setActionLoading(`check-${closing.id}-${itemName}`);
    try {
      await api.updateChecklistItem(closing.id, {
        closing_id: closing.id,
        check_name: itemName,
        status: currentCompleted ? 'pending' : 'completed',
      });
      fetchData();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // ── Review Closing ───────────────────────────────────────────
  const handleReview = async (closing: PeriodClosing) => {
    const pending = closing.checklist.filter(c => !c.completed).length;
    if (pending > 0) {
      alert(`Masih ada ${pending} checklist yang belum selesai!`);
      return;
    }
    if (!confirm(`Review closing ${closing.period}?`)) return;
    setActionLoading(`review-${closing.id}`);
    try {
      await api.reviewPeriodClosing(closing.id);
      fetchData();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // ── Close Period ─────────────────────────────────────────────
  const handleClose = async (closing: PeriodClosing) => {
    if (!confirm(`CLOSE period ${closing.period}? Ini akan LOCK financial period terkait dan TIDAK BISA di-undo.`)) return;
    setActionLoading(`close-${closing.id}`);
    try {
      await api.closePeriod(closing.id);
      fetchData();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#C9A96E]"></div></div>;
  if (error) return <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg">Error: {error}</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Period & Closing</h1>

      {/* Current Status */}
      {status && (
        <div className="bg-gradient-to-r from-[#C9A96E] to-[#C08081] text-white rounded-xl p-6 shadow-lg">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm opacity-90">Current Period</p>
              <p className="text-xl font-bold mt-1">{status.current_period}</p>
            </div>
            <div>
              <p className="text-sm opacity-90">Lock Status</p>
              <p className="text-xl font-bold mt-1">{status.is_locked ? '🔒 Locked' : '🔓 Open'}</p>
            </div>
            <div>
              <p className="text-sm opacity-90">Days Remaining</p>
              <p className="text-xl font-bold mt-1">{status.days_remaining} days</p>
            </div>
          </div>
        </div>
      )}

      {/* Financial Periods */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="bg-[#C9A96E] px-6 py-3 flex items-center justify-between">
          <h2 className="text-white font-semibold">Financial Periods</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Period</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Branch</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Start Date</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">End Date</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Status</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {periods.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No financial periods found</td></tr>
              ) : periods.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-semibold">{p.name}</td>
                  <td className="px-4 py-3 text-gray-600">{p.branch_name || '-'}</td>
                  <td className="px-4 py-3">{new Date(p.start_date).toLocaleDateString()}</td>
                  <td className="px-4 py-3">{new Date(p.end_date).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <span className={`px-3 py-1 rounded-full text-sm border ${getStatusColor(p.status)}`}>
                      {p.status === 'locked' ? '🔒 ' : ''}{p.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      {p.status === 'open' && (
                        <button
                          onClick={() => handleLock(p)}
                          disabled={actionLoading === `lock-${p.id}`}
                          className="px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
                        >
                          {actionLoading === `lock-${p.id}` ? '⏳' : '🔒 Lock'}
                        </button>
                      )}
                      {p.status === 'locked' && (
                        <button
                          onClick={() => setUnlockModal(p)}
                          disabled={actionLoading === `unlock-${p.id}`}
                          className="px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
                        >
                          {actionLoading === `unlock-${p.id}` ? '⏳' : '🔓 Unlock'}
                        </button>
                      )}
                      {p.closed_at && (
                        <span className="text-xs text-gray-400">
                          by {p.closed_by || '-'}
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Period Closings */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="bg-[#C08081] px-6 py-3 flex items-center justify-between">
          <h2 className="text-white font-semibold">Period Closings</h2>
          <button
            onClick={() => setShowCreateClosing(true)}
            className="px-4 py-1.5 bg-white text-[#C08081] hover:bg-gray-100 text-sm font-medium rounded-lg transition-colors"
          >
            ➕ New Closing
          </button>
        </div>
        <div className="p-4 space-y-4">
          {closings.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No closing records found</p>
          ) : (
            closings.map((c) => {
              const pendingCount = c.checklist.filter(item => !item.completed).length;
              const completedCount = c.checklist.filter(item => item.completed).length;
              const allDone = pendingCount === 0;

              return (
                <div key={c.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-3">
                      <h3 className="font-semibold text-[#C9A96E] text-lg">{c.period}</h3>
                      <span className={`px-2 py-0.5 rounded-full text-xs border ${getClosingStatusColor(c.status)}`}>
                        {c.status}
                      </span>
                      {c.branch_name && <span className="text-sm text-gray-500">📍 {c.branch_name}</span>}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-400">{completedCount}/{c.checklist.length} done</span>
                      {c.status === 'draft' && (
                        <button
                          onClick={() => handleReview(c)}
                          disabled={!allDone || actionLoading === `review-${c.id}`}
                          className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                            allDone
                              ? 'bg-blue-500 hover:bg-blue-600 text-white'
                              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                          }`}
                          title={allDone ? 'Review this closing' : `${pendingCount} checklist items still pending`}
                        >
                          {actionLoading === `review-${c.id}` ? '⏳' : '📋 Review'}
                        </button>
                      )}
                      {c.status === 'reviewed' && (
                        <button
                          onClick={() => handleClose(c)}
                          disabled={actionLoading === `close-${c.id}`}
                          className="px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
                        >
                          {actionLoading === `close-${c.id}` ? '⏳' : '✅ Close Period'}
                        </button>
                      )}
                      {c.status === 'closed' && c.closed_at && (
                        <span className="text-xs text-gray-400">
                          Closed by {c.closed_by || '-'} on {new Date(c.closed_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
                    <div
                      className={`h-2 rounded-full transition-all ${allDone ? 'bg-green-500' : 'bg-[#C9A96E]'}`}
                      style={{ width: `${(completedCount / c.checklist.length) * 100}%` }}
                    />
                  </div>

                  {/* Checklist */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {c.checklist.map((item, i) => (
                      <button
                        key={i}
                        onClick={() => c.status === 'draft' && handleToggleChecklist(c, item.item, item.completed)}
                        disabled={c.status !== 'draft' || actionLoading === `check-${c.id}-${item.item}`}
                        className={`flex items-center gap-2 text-left p-2 rounded-lg transition-colors ${
                          c.status === 'draft' ? 'hover:bg-gray-50 cursor-pointer' : 'cursor-default'
                        }`}
                      >
                        <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${
                          item.completed ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
                        }`}>
                          {item.completed ? '✓' : '○'}
                        </span>
                        <span className={`text-sm ${item.completed ? 'text-gray-700' : 'text-gray-400'}`}>
                          {item.item}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ── Unlock Modal ─────────────────────────────────────────── */}
      {unlockModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4">
            <div className="bg-green-500 text-white px-6 py-4 rounded-t-xl">
              <h3 className="font-semibold text-lg">🔓 Unlock Period</h3>
              <p className="text-sm opacity-90">{unlockModal.name}</p>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Unlocked By</label>
                <input
                  type="text"
                  value={unlockBy}
                  onChange={(e) => setUnlockBy(e.target.value)}
                  placeholder="Your name"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason (required) *</label>
                <textarea
                  value={unlockReason}
                  onChange={(e) => setUnlockReason(e.target.value)}
                  placeholder="Why do you need to unlock this period?"
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                />
              </div>
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
                ⚠️ Unlocking allows transactions to be posted to this period again. This action is logged in the audit trail.
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t">
              <button
                onClick={() => { setUnlockModal(null); setUnlockReason(''); setUnlockBy(''); }}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUnlock}
                disabled={!unlockReason.trim() || actionLoading?.startsWith('unlock-')}
                className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {actionLoading?.startsWith('unlock-') ? '⏳ Unlocking...' : '🔓 Unlock Period'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Create Closing Modal ─────────────────────────────────── */}
      {showCreateClosing && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4">
            <div className="bg-[#C08081] text-white px-6 py-4 rounded-t-xl">
              <h3 className="font-semibold text-lg">➕ New Period Closing</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Period (YYYY-MM)</label>
                <input
                  type="month"
                  value={closingPeriod}
                  onChange={(e) => setClosingPeriod(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#C08081] focus:border-transparent"
                />
                <p className="text-xs text-gray-400 mt-1">Leave empty for current month</p>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t">
              <button
                onClick={() => { setShowCreateClosing(false); setClosingPeriod(''); }}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateClosing}
                disabled={actionLoading === 'create-closing'}
                className="px-4 py-2 bg-[#C08081] hover:bg-[#a86b6c] text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {actionLoading === 'create-closing' ? '⏳ Creating...' : '➕ Create Closing'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
