import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, transactionApi } from '../api/client';

interface Treatment {
  id: string;
  name: string;
  price: number;
  duration_minutes: number;
  category_id?: string;
  category_name?: string;
}

export default function PosTreatmentSelectorPage() {
  const { transactionId } = useParams();
  const navigate = useNavigate();
  const [treatments, setTreatments] = useState<Treatment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadTreatments();
  }, []);

  async function loadTreatments() {
    setLoading(true);
    try {
      const result = await api.getTreatments();
      const items = Array.isArray(result) ? result : result?.items || result?.data || [];
      setTreatments(items);
    } catch (err: any) {
      setError(err.message || 'Gagal memuat treatment');
    }
    setLoading(false);
  }

  async function handleAddTreatment(treatment: Treatment) {
    if (!transactionId) return;
    setAdding(treatment.id);
    try {
      const staff = JSON.parse(localStorage.getItem('pos_staff') || '{}');
      await transactionApi.addItem(transactionId, {
        service_id: treatment.id,
        staff_id: staff.id || 'KSR001',
        quantity: 1,
      });
      navigate(`/kasir/${transactionId}`);
    } catch (err: any) {
      setError(err.message || 'Gagal menambahkan treatment');
    }
    setAdding(null);
  }

  const formatRp = (n: number) => 'Rp ' + (n || 0).toLocaleString('id-ID');

  const filteredTreatments = treatments.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase()) ||
    (t.category_name || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(`/kasir/${transactionId}`)}
          className="text-gray-500"
        >
          ← Kembali
        </button>
        <h1 className="text-lg font-bold text-[var(--charcoal)]">Pilih Treatment</h1>
      </div>

      {/* Search */}
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Cari treatment..."
        className="w-full px-4 py-3 bg-white rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-[var(--gold)]"
      />

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl">
          {error}
          <button onClick={() => setError(null)} className="float-right text-red-400">✕</button>
        </div>
      )}

      {/* Treatment List */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-xl p-4 border border-gray-100 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
              <div className="h-3 bg-gray-200 rounded w-1/4" />
            </div>
          ))}
        </div>
      ) : filteredTreatments.length > 0 ? (
        <div className="space-y-2">
          {filteredTreatments.map((treatment) => (
            <button
              key={treatment.id}
              onClick={() => handleAddTreatment(treatment)}
              disabled={adding === treatment.id}
              className="w-full bg-white rounded-xl p-4 border border-gray-100 shadow-sm text-left active:bg-gray-50 transition-colors disabled:opacity-50"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="font-medium text-[var(--charcoal)]">{treatment.name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    {treatment.category_name && (
                      <span className="text-[10px] px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full">
                        {treatment.category_name}
                      </span>
                    )}
                    <span className="text-xs text-gray-400">
                      {treatment.duration_minutes || 60} menit
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-[var(--charcoal)]">{formatRp(treatment.price)}</p>
                  <p className="text-[10px] text-[var(--gold)] mt-1">
                    {adding === treatment.id ? 'Menambahkan...' : '+ Tambah'}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-gray-400">
          <p className="text-4xl mb-2">💇</p>
          <p>Treatment tidak ditemukan</p>
        </div>
      )}
    </div>
  );
}
