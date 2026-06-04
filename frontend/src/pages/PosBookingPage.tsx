import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, fetchJSON } from '../api/client';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import Modal from '../components/common/Modal';

interface Booking {
  id: string;
  docKey: string;
  customerName: string;
  customerPhone: string;
  treatmentName: string;
  staffName: string;
  bedName: string;
  date: string;
  time: string;
  duration: number;
  status: 'CONFIRMED' | 'PENDING' | 'CANCELLED' | 'COMPLETED' | 'NO_SHOW';
  notes?: string;
}

interface Treatment {
  id: string;
  name: string;
  price: number;
  duration: number;
  category: string;
}

interface Bed {
  id: string;
  name: string;
  status: string;
}

const STATUS_LABELS: Record<string, string> = {
  CONFIRMED: 'Terkonfirmasi',
  PENDING: 'Menunggu',
  CANCELLED: 'Dibatalkan',
  COMPLETED: 'Selesai',
  NO_SHOW: 'Tidak Hadir',
  booked: 'Booked',
  open: 'Sedang Berjalan',
};

const STATUS_COLORS: Record<string, string> = {
  CONFIRMED: 'bg-blue-100 text-blue-700',
  PENDING: 'bg-yellow-100 text-yellow-700',
  CANCELLED: 'bg-red-100 text-red-600',
  COMPLETED: 'bg-green-100 text-green-700',
  NO_SHOW: 'bg-gray-100 text-gray-600',
  booked: 'bg-blue-100 text-blue-700',
  open: 'bg-green-100 text-green-700',
};

export default function PosBookingPage() {
  const navigate = useNavigate();
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [treatments, setTreatments] = useState<Treatment[]>([]);
  const [beds, setBeds] = useState<Bed[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'calendar'>('list');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  // Customer search
  const [customerSearch, setCustomerSearch] = useState('');
  const [customerResults, setCustomerResults] = useState<any[]>([]);
  const [searchingCustomer, setSearchingCustomer] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);

  // Create form state
  const [form, setForm] = useState({
    customerName: '',
    customerPhone: '',
    treatmentId: '',
    staffName: '',
    bedId: '',
    date: new Date().toISOString().split('T')[0],
    time: '10:00',
    notes: '',
  });

  const [showCreateCustomer, setShowCreateCustomer] = useState(false);
  const [creatingCustomer, setCreatingCustomer] = useState(false);
  const [newCustomerForm, setNewCustomerForm] = useState({ name: '', phone: '', email: '' });

  async function handleCreateCustomer(e: React.FormEvent) {
    e.preventDefault();
    if (!newCustomerForm.name) return;
    setCreatingCustomer(true);
    try {
      const created = await api.createCustomer({
        name: newCustomerForm.name,
        phone: newCustomerForm.phone || undefined,
        email: newCustomerForm.email || undefined,
      });
      selectCustomer(created);
      setShowCreateCustomer(false);
      setNewCustomerForm({ name: '', phone: '', email: '' });
    } catch (err: any) {
      setError(err.message || 'Gagal membuat customer');
    }
    setCreatingCustomer(false);
  }

  // Debounced customer search
  useEffect(() => {
    if (customerSearch.length < 2) {
      setCustomerResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setSearchingCustomer(true);
      try {
        const res = await api.getCustomers(customerSearch);
        const list = Array.isArray(res) ? res : res?.items || res?.data || [];
        setCustomerResults(list.slice(0, 8));
      } catch { setCustomerResults([]); }
      setSearchingCustomer(false);
    }, 300);
    return () => clearTimeout(timer);
  }, [customerSearch]);

  function selectCustomer(c: any) {
    setSelectedCustomer(c);
    setForm({
      ...form,
      customerName: c.name || c.customer_name || '',
      customerPhone: c.phone || c.customer_phone || '',
    });
    setCustomerSearch('');
    setCustomerResults([]);
  }

  function clearCustomer() {
    setSelectedCustomer(null);
    setForm({ ...form, customerName: '', customerPhone: '' });
  }

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [txData, treatData, bedData] = await Promise.allSettled([
        api.getTransactions('status=booked,open&limit=50'),
        api.getTreatments(),
        api.getBeds(),
      ]);

      const txResult = txData.status === 'fulfilled' ? txData.value : [];
      const txList = Array.isArray(txResult) ? txResult : txResult?.items || txResult?.data || [];

      setBookings(
        txList.map((t: any) => ({
          id: t.id || t.transaction_id,
          docKey: t.doc_key || '',
          customerName: t.customer?.name || t.customer_name || '-',
          customerPhone: t.customer?.phone || t.customer_phone || '-',
          treatmentName: t.items?.[0]?.service?.name || t.treatment_name || '-',
          staffName: t.items?.[0]?.staff?.name || t.staff_name || '-',
          bedName: t.bed?.name || t.bed_name || '-',
          date: t.booking_date || t.createdAt?.split('T')[0] || new Date().toISOString().split('T')[0],
          time: t.booking_time || t.createdAt?.split('T')[1]?.substring(0, 5) || '10:00',
          duration: t.items?.[0]?.service?.duration || 60,
          status: t.booking_status || t.state || 'PENDING',
          notes: t.notes || '',
        }))
      );

      if (treatData.status === 'fulfilled') {
        const tr = treatData.value;
        setTreatments(Array.isArray(tr) ? tr : tr?.items || tr?.data || []);
      }
      if (bedData.status === 'fulfilled') {
        const br = bedData.value;
        setBeds(Array.isArray(br) ? br : br?.items || br?.data || []);
      }
    } catch (err: any) {
      setError(err.message || 'Gagal memuat data booking');
    }
    setLoading(false);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.customerName || !form.treatmentId || !form.date || !form.time) {
      setError('Harap isi semua field wajib');
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const staff = JSON.parse(localStorage.getItem('pos_staff') || '{}');
      await fetchJSON('/pos/booking', {
        method: 'POST',
        body: JSON.stringify({
          customer_name: form.customerName,
          customer_phone: form.customerPhone || undefined,
          treatment_ids: form.treatmentId ? [form.treatmentId] : [],
          bed_id: form.bedId || undefined,
          therapist_id: staff.id || undefined,
          notes: form.notes || undefined,
          booking_date: form.date,
          booking_time: form.time,
        }),
      });
      setShowCreate(false);
      setSelectedCustomer(null);
      setCustomerSearch('');
      setCustomerResults([]);
      setForm({
        customerName: '',
        customerPhone: '',
        treatmentId: '',
        staffName: '',
        bedId: '',
        date: new Date().toISOString().split('T')[0],
        time: '10:00',
        notes: '',
      });
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Gagal membuat booking');
    }
    setCreating(false);
  }

  async function handleConvertToTransaction(docKey: string) {
    try {
      const result = await fetchJSON(`/pos/booking/${docKey}/to-transaction`, { method: 'POST' });
      navigate(`/kasir/${result.id || docKey}`);
    } catch (err: any) {
      setError(err.message || 'Gagal membuat transaksi');
    }
  }

  // Calendar helpers
  const filteredBookings = viewMode === 'calendar'
    ? bookings.filter((b) => b.date === selectedDate)
    : bookings;

  const datesWithBookings = new Set(bookings.map((b) => b.date));

  function getCalendarDays() {
    const today = new Date();
    const days = [];
    for (let i = 0; i < 28; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      days.push(d.toISOString().split('T')[0]);
    }
    return days;
  }

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
        <h1 className="text-lg font-bold text-[var(--charcoal)]">Booking</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-[var(--gold)] text-white px-4 py-2 rounded-xl text-sm font-medium active:bg-[var(--gold)]/90 transition-colors"
        >
          + Booking Baru
        </button>
      </div>

      {/* View Toggle */}
      <div className="flex bg-gray-100 rounded-xl p-1">
        {(['list', 'calendar'] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              viewMode === mode ? 'bg-white text-[var(--charcoal)] shadow-sm' : 'text-gray-500'
            }`}
          >
            {mode === 'list' ? '📋 Daftar' : '📅 Kalender'}
          </button>
        ))}
      </div>

      {/* Calendar View */}
      {viewMode === 'calendar' && (
        <div className="overflow-x-auto -mx-4 px-4">
          <div className="flex gap-2 pb-2">
            {getCalendarDays().map((day) => {
              const d = new Date(day + 'T00:00:00');
              const isSelected = day === selectedDate;
              const hasBooking = datesWithBookings.has(day);
              return (
                <button
                  key={day}
                  onClick={() => setSelectedDate(day)}
                  className={`flex flex-col items-center min-w-[48px] py-2 rounded-xl transition-colors ${
                    isSelected ? 'bg-[var(--gold)] text-white' : 'bg-white border border-gray-100 text-gray-600'
                  }`}
                >
                  <span className="text-[10px]">{d.toLocaleDateString('id-ID', { weekday: 'short' })}</span>
                  <span className="text-sm font-bold">{d.getDate()}</span>
                  {hasBooking && (
                    <div className={`w-1.5 h-1.5 rounded-full mt-0.5 ${isSelected ? 'bg-white' : 'bg-[var(--rose)]'}`} />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Bookings List */}
      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : filteredBookings.length ? (
        <div className="space-y-3">
          {filteredBookings.map((booking) => (
            <div
              key={booking.id}
              className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-[var(--charcoal)]">{booking.customerName}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[booking.status] || 'bg-gray-100 text-gray-600'}`}>
                      {STATUS_LABELS[booking.status] || booking.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{booking.treatmentName}</p>
                </div>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-500">
                <div className="flex items-center gap-1.5">
                  <span>📅</span>
                  <span>{new Date(booking.date + 'T00:00:00').toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>🕐</span>
                  <span>{booking.time} ({booking.duration} mnt)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>👤</span>
                  <span>{booking.staffName || '-'}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>🛏️</span>
                  <span>{booking.bedName || '-'}</span>
                </div>
              </div>
              {(booking.status === 'PENDING' || booking.status === 'CONFIRMED') && (
                <button
                  onClick={() => handleConvertToTransaction(booking.docKey)}
                  className="mt-3 w-full py-2 rounded-lg bg-[var(--gold)]/10 text-[var(--gold)] text-sm font-medium active:bg-[var(--gold)]/20 transition-colors"
                >
                  💳 Buat Transaksi
                </button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl p-8 border border-gray-100 text-center">
          <span className="text-4xl">📅</span>
          <p className="text-gray-400 text-sm mt-3">
            {viewMode === 'calendar' ? 'Tidak ada booking di tanggal ini' : 'Belum ada booking'}
          </p>
        </div>
      )}

      {/* Create Booking Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Booking Baru">
        <form onSubmit={handleCreate} className="space-y-3 text-left">
          {/* Error inside modal */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-xs px-3 py-2 rounded-lg">
              {error}
            </div>
          )}
          {/* Customer Search / Select */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Customer *</label>
            {selectedCustomer ? (
              <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl border border-[var(--gold)]/30 bg-[var(--gold)]/5">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-[var(--charcoal)] truncate">{selectedCustomer.name || selectedCustomer.customer_name}</p>
                  <p className="text-xs text-gray-500">{selectedCustomer.phone || selectedCustomer.customer_phone || '-'} {selectedCustomer.tier ? `• ${selectedCustomer.tier}` : ''}</p>
                </div>
                <button type="button" onClick={clearCustomer} className="text-gray-400 hover:text-red-500 text-sm px-1">✕</button>
              </div>
            ) : (
              <div className="relative">
                <input
                  type="text"
                  value={customerSearch}
                  onChange={(e) => setCustomerSearch(e.target.value)}
                  placeholder="🔍 Cari customer (nama / telepon)..."
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
                />
                {searchingCustomer && (
                  <div className="absolute right-3 top-3">
                    <div className="w-4 h-4 border-2 border-[var(--gold)] border-t-transparent rounded-full animate-spin" />
                  </div>
                )}
                {customerResults.length > 0 && (
                  <div className="absolute z-10 top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-lg max-h-48 overflow-y-auto">
                    {customerResults.map((c: any) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => selectCustomer(c)}
                        className="w-full text-left px-3 py-2.5 hover:bg-[var(--gold)]/5 border-b border-gray-50 last:border-0 transition-colors"
                      >
                        <p className="text-sm font-medium text-[var(--charcoal)]">{c.name || c.customer_name}</p>
                        <p className="text-xs text-gray-400">{c.phone || c.customer_phone || '-'} {c.tier ? `• ${c.tier}` : ''}</p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {/* Manual fallback + Create Customer */}
            {!selectedCustomer && (
              <div className="mt-2 space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={form.customerName}
                    onChange={(e) => setForm({ ...form, customerName: e.target.value })}
                    placeholder="Atau ketik nama manual"
                    className="w-full px-3 py-2 rounded-xl border border-gray-100 bg-gray-50 text-xs text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
                  />
                  <input
                    type="tel"
                    value={form.customerPhone}
                    onChange={(e) => setForm({ ...form, customerPhone: e.target.value })}
                    placeholder="No. telepon manual"
                    inputMode="tel"
                    className="w-full px-3 py-2 rounded-xl border border-gray-100 bg-gray-50 text-xs text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setNewCustomerForm({ name: form.customerName, phone: form.customerPhone, email: '' });
                    setShowCreateCustomer(true);
                  }}
                  className="w-full py-2 rounded-xl border border-dashed border-[var(--gold)]/40 text-[var(--gold)] text-xs font-medium active:bg-[var(--gold)]/5 transition-colors"
                >
                  ＋ Buat Customer Baru
                </button>
              </div>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Treatment *</label>
            <select
              value={form.treatmentId}
              onChange={(e) => setForm({ ...form, treatmentId: e.target.value })}
              required
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            >
              <option value="">Pilih treatment</option>
              {treatments.map((t: any) => (
                <option key={t.id} value={t.id}>{t.name} — Rp {(t.price || 0).toLocaleString('id-ID')}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Staff</label>
            <input
              type="text"
              value={form.staffName}
              onChange={(e) => setForm({ ...form, staffName: e.target.value })}
              placeholder="Nama staff (opsional)"
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Bed / Ruangan</label>
            <select
              value={form.bedId}
              onChange={(e) => setForm({ ...form, bedId: e.target.value })}
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            >
              <option value="">Pilih bed (opsional)</option>
              {beds.map((b: any) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Tanggal *</label>
              <input
                type="date"
                value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
                required
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Jam *</label>
              <input
                type="time"
                value={form.time}
                onChange={(e) => setForm({ ...form, time: e.target.value })}
                required
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Catatan</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder="Catatan tambahan (opsional)"
              rows={2}
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent resize-none"
            />
          </div>
          <button
            type="submit"
            disabled={creating}
            className="w-full py-3 rounded-xl bg-[var(--gold)] text-white font-semibold text-sm active:bg-[var(--gold)]/90 disabled:opacity-50 transition-colors shadow-sm"
          >
            {creating ? 'Menyimpan...' : 'Simpan Booking'}
          </button>
        </form>
      </Modal>

      {/* Create Customer Modal */}
      <Modal open={showCreateCustomer} onClose={() => setShowCreateCustomer(false)} title="Buat Customer Baru">
        <form onSubmit={handleCreateCustomer} className="space-y-3 text-left">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Nama *</label>
            <input
              type="text"
              value={newCustomerForm.name}
              onChange={(e) => setNewCustomerForm({ ...newCustomerForm, name: e.target.value })}
              required
              placeholder="Nama lengkap"
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Telepon</label>
            <input
              type="tel"
              value={newCustomerForm.phone}
              onChange={(e) => setNewCustomerForm({ ...newCustomerForm, phone: e.target.value })}
              placeholder="No. telepon"
              inputMode="tel"
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
            <input
              type="email"
              value={newCustomerForm.email}
              onChange={(e) => setNewCustomerForm({ ...newCustomerForm, email: e.target.value })}
              placeholder="Email (opsional)"
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            />
          </div>
          <button
            type="submit"
            disabled={creatingCustomer}
            className="w-full py-3 rounded-xl bg-[var(--gold)] text-white font-semibold text-sm active:bg-[var(--gold)]/90 disabled:opacity-50 transition-colors shadow-sm"
          >
            {creatingCustomer ? 'Menyimpan...' : 'Simpan Customer'}
          </button>
        </form>
      </Modal>
    </div>
  );
}
