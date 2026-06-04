import { useState, useEffect } from 'react';
import { fetchJSON } from '../api/client';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import Modal from '../components/common/Modal';

interface Voucher {
  id: string;
  code: string;
  name: string;
  type: 'PERCENTAGE' | 'FIXED' | 'FREE_SERVICE';
  value: number;
  minPurchase: number;
  maxDiscount?: number;
  startDate: string;
  endDate: string;
  usageLimit: number;
  usedCount: number;
  isActive: boolean;
  applicableTreatments?: string[];
}

const TYPE_LABELS: Record<string, string> = {
  PERCENTAGE: 'Diskon %',
  FIXED: 'Diskon Rp',
  FREE_SERVICE: 'Gratis Treatment',
};

const TYPE_COLORS: Record<string, string> = {
  PERCENTAGE: 'bg-blue-100 text-blue-700',
  FIXED: 'bg-green-100 text-green-700',
  FREE_SERVICE: 'bg-purple-100 text-purple-700',
};

export default function PosVoucherPage() {
  const [vouchers, setVouchers] = useState<Voucher[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [filter, setFilter] = useState<'all' | 'active' | 'expired'>('all');
  const [search, setSearch] = useState('');

  // Create form
  const [form, setForm] = useState({
    code: '',
    name: '',
    type: 'PERCENTAGE' as 'PERCENTAGE' | 'FIXED' | 'FREE_SERVICE',
    value: '',
    minPurchase: '',
    maxDiscount: '',
    startDate: new Date().toISOString().split('T')[0],
    endDate: '',
    usageLimit: '',
  });

  const formatRp = (n: number) => 'Rp ' + (n || 0).toLocaleString('id-ID');

  useEffect(() => {
    loadVouchers();
  }, []);

  async function loadVouchers() {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchJSON('/master/voucher');
      const list = Array.isArray(result) ? result : result?.items || result?.data || [];
      setVouchers(list);
    } catch (err: any) {
      setError(err.message || 'Gagal memuat voucher');
    }
    setLoading(false);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.code || !form.name || !form.value || !form.endDate) {
      setError('Harap isi semua field wajib');
      return;
    }

    setCreating(true);
    setError(null);
    try {
      await fetchJSON('/master/voucher', {
        method: 'POST',
        body: JSON.stringify({
          code: form.code.toUpperCase(),
          name: form.name,
          type: form.type,
          value: parseFloat(form.value),
          min_purchase: parseFloat(form.minPurchase) || 0,
          max_discount: form.maxDiscount ? parseFloat(form.maxDiscount) : undefined,
          start_date: form.startDate,
          end_date: form.endDate,
          usage_limit: parseInt(form.usageLimit) || 100,
        }),
      });
      setShowCreate(false);
      setForm({
        code: '',
        name: '',
        type: 'PERCENTAGE',
        value: '',
        minPurchase: '',
        maxDiscount: '',
        startDate: new Date().toISOString().split('T')[0],
        endDate: '',
        usageLimit: '',
      });
      await loadVouchers();
    } catch (err: any) {
      setError(err.message || 'Gagal membuat voucher');
    }
    setCreating(false);
  }

  function toggleActive(voucher: Voucher) {
    // Optimistic update
    setVouchers((prev) =>
      prev.map((v) => (v.id === voucher.id ? { ...v, isActive: !v.isActive } : v))
    );
    // API call
    fetchJSON(`/master/voucher/${voucher.id}`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: !voucher.isActive }),
    }).catch(() => {
      // Revert on error
      setVouchers((prev) =>
        prev.map((v) => (v.id === voucher.id ? { ...v, isActive: v.isActive } : v))
      );
    });
  }

  const now = new Date();
  const filteredVouchers = vouchers.filter((v) => {
    if (filter === 'active') return v.isActive && new Date(v.endDate) >= now;
    if (filter === 'expired') return !v.isActive || new Date(v.endDate) < now;
    return true;
  }).filter((v) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return v.code.toLowerCase().includes(q) || v.name.toLowerCase().includes(q);
  });

  return (
    <div className="p-4 space-y-4">
      {/* Error Toast */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">✕</button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-[var(--charcoal)]">Voucher & Promo</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-[var(--gold)] text-white px-4 py-2 rounded-xl text-sm font-medium active:bg-[var(--gold)]/90 transition-colors"
        >
          + Buat Voucher
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" strokeLinecap="round" />
        </svg>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Cari kode atau nama voucher..."
          className="w-full pl-10 pr-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
        />
      </div>

      {/* Filter Tabs */}
      <div className="flex bg-gray-100 rounded-xl p-1">
        {([['all', 'Semua'], ['active', 'Aktif'], ['expired', 'Kedaluwarsa']] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`flex-1 py-2 rounded-lg text-xs font-medium transition-colors ${
              filter === key ? 'bg-white text-[var(--charcoal)] shadow-sm' : 'text-gray-500'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Vouchers List */}
      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : filteredVouchers.length ? (
        <div className="space-y-3">
          {filteredVouchers.map((voucher) => {
            const isExpired = new Date(voucher.endDate) < now;
            return (
              <div
                key={voucher.id}
                className={`bg-white rounded-xl p-4 border shadow-sm ${
                  !voucher.isActive || isExpired ? 'border-gray-100 opacity-60' : 'border-gray-100'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono font-bold text-[var(--charcoal)] bg-gray-50 px-2 py-0.5 rounded">
                        {voucher.code}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${TYPE_COLORS[voucher.type]}`}>
                        {TYPE_LABELS[voucher.type]}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-[var(--charcoal)] mt-1">{voucher.name}</p>
                  </div>
                  <button
                    onClick={() => toggleActive(voucher)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      voucher.isActive ? 'bg-[var(--gold)]' : 'bg-gray-200'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        voucher.isActive ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-500">
                  <div>
                    <span className="text-gray-400">Nilai</span>
                    <p className="font-medium text-[var(--charcoal)]">
                      {voucher.type === 'PERCENTAGE' ? `${voucher.value}%` : voucher.type === 'FIXED' ? formatRp(voucher.value) : 'Gratis'}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-400">Min. Pembelian</span>
                    <p className="font-medium text-[var(--charcoal)]">{formatRp(voucher.minPurchase)}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">Berlaku</span>
                    <p className="font-medium text-[var(--charcoal)]">
                      {new Date(voucher.startDate).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })} — {new Date(voucher.endDate).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-400">Penggunaan</span>
                    <p className="font-medium text-[var(--charcoal)]">{voucher.usedCount} / {voucher.usageLimit}</p>
                  </div>
                </div>

                {isExpired && (
                  <div className="mt-2 text-[10px] text-red-500 font-medium">⚠ Kedaluwarsa</div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-white rounded-xl p-8 border border-gray-100 text-center">
          <span className="text-4xl">🎟️</span>
          <p className="text-gray-400 text-sm mt-3">
            {search ? 'Voucher tidak ditemukan' : 'Belum ada voucher'}
          </p>
        </div>
      )}

      {/* Create Voucher Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Buat Voucher Baru">
        <form onSubmit={handleCreate} className="space-y-3 text-left">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Kode Voucher *</label>
            <input
              type="text"
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '') })}
              placeholder="HEMAT20"
              maxLength={20}
              required
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Nama Promo *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Diskon Spesial 20%"
              required
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tipe Diskon *</label>
            <select
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value as any })}
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            >
              <option value="PERCENTAGE">Diskon Persentase (%)</option>
              <option value="FIXED">Diskon Nominal (Rp)</option>
              <option value="FREE_SERVICE">Gratis Treatment</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Nilai *</label>
              <input
                type="number"
                value={form.value}
                onChange={(e) => setForm({ ...form, value: e.target.value })}
                placeholder={form.type === 'PERCENTAGE' ? '20' : '50000'}
                required
                min="0"
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Min. Pembelian</label>
              <input
                type="number"
                value={form.minPurchase}
                onChange={(e) => setForm({ ...form, minPurchase: e.target.value })}
                placeholder="0"
                min="0"
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
              />
            </div>
          </div>
          {form.type === 'PERCENTAGE' && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Maks. Diskon (Rp)</label>
              <input
                type="number"
                value={form.maxDiscount}
                onChange={(e) => setForm({ ...form, maxDiscount: e.target.value })}
                placeholder="100000"
                min="0"
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
              />
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Mulai *</label>
              <input
                type="date"
                value={form.startDate}
                onChange={(e) => setForm({ ...form, startDate: e.target.value })}
                required
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Berakhir *</label>
              <input
                type="date"
                value={form.endDate}
                onChange={(e) => setForm({ ...form, endDate: e.target.value })}
                required
                min={form.startDate}
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Batas Penggunaan</label>
            <input
              type="number"
              value={form.usageLimit}
              onChange={(e) => setForm({ ...form, usageLimit: e.target.value })}
              placeholder="100"
              min="1"
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            />
          </div>
          <button
            type="submit"
            disabled={creating}
            className="w-full py-3 rounded-xl bg-[var(--gold)] text-white font-semibold text-sm active:bg-[var(--gold)]/90 disabled:opacity-50 transition-colors shadow-sm"
          >
            {creating ? 'Menyimpan...' : 'Simpan Voucher'}
          </button>
        </form>
      </Modal>
    </div>
  );
}
