import { useState, useEffect, useRef } from 'react';
import { api, fetchJSON } from '../api/client';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import Modal from '../components/common/Modal';

interface TreatmentRecord {
  id: string;
  transactionId: string;
  posCode: string;
  customerName: string;
  treatmentName: string;
  staffName: string;
  date: string;
  beforePhotos: string[];
  afterPhotos: string[];
  notes: string;
  consentSigned: boolean;
  allergies?: string;
  skinType?: string;
  reactions?: string;
}

interface Treatment {
  id: string;
  name: string;
  category: string;
}

export default function PosTreatmentRecordPage() {
  const [records, setRecords] = useState<TreatmentRecord[]>([]);
  const [treatments, setTreatments] = useState<Treatment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<TreatmentRecord | null>(null);
  const [search, setSearch] = useState('');

  // Form state
  const [form, setForm] = useState({
    customerName: '',
    treatmentId: '',
    notes: '',
    allergies: '',
    skinType: '',
    reactions: '',
    consentSigned: false,
  });
  const [beforePhotos, setBeforePhotos] = useState<string[]>([]);
  const [afterPhotos, setAfterPhotos] = useState<string[]>([]);
  const beforeInputRef = useRef<HTMLInputElement>(null);
  const afterInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [txResult, treatResult] = await Promise.allSettled([
        api.getTransactions('limit=50'),
        api.getTreatments(),
      ]);

      if (txResult.status === 'fulfilled') {
        const tx = txResult.value;
        const list = Array.isArray(tx) ? tx : tx?.items || tx?.data || [];
        setRecords(
          list
            .filter((t: any) => t.state === 'PAID')
            .map((t: any) => ({
              id: t.id || t.transaction_id,
              transactionId: t.id || t.transaction_id,
              posCode: t.posCode || t.pos_code || '-',
              customerName: t.customer?.name || t.customer_name || '-',
              treatmentName: t.items?.[0]?.service?.name || '-',
              staffName: t.items?.[0]?.staff?.name || '-',
              date: t.createdAt || t.created_at || new Date().toISOString(),
              beforePhotos: t.treatment_record?.before_photos || [],
              afterPhotos: t.treatment_record?.after_photos || [],
              notes: t.treatment_record?.notes || '',
              consentSigned: t.treatment_record?.consent_signed || false,
              allergies: t.treatment_record?.allergies || '',
              skinType: t.treatment_record?.skin_type || '',
              reactions: t.treatment_record?.reactions || '',
            }))
        );
      }

      if (treatResult.status === 'fulfilled') {
        const tr = treatResult.value;
        setTreatments(Array.isArray(tr) ? tr : tr?.items || tr?.data || []);
      }
    } catch (err: any) {
      setError(err.message || 'Gagal memuat data');
    }
    setLoading(false);
  }

  function handlePhotoSelect(e: React.ChangeEvent<HTMLInputElement>, type: 'before' | 'after') {
    const files = e.target.files;
    if (!files) return;

    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const result = ev.target?.result as string;
        if (type === 'before') {
          setBeforePhotos((prev) => [...prev, result]);
        } else {
          setAfterPhotos((prev) => [...prev, result]);
        }
      };
      reader.readAsDataURL(file);
    });
    // Reset input
    e.target.value = '';
  }

  function removePhoto(index: number, type: 'before' | 'after') {
    if (type === 'before') {
      setBeforePhotos((prev) => prev.filter((_, i) => i !== index));
    } else {
      setAfterPhotos((prev) => prev.filter((_, i) => i !== index));
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.customerName || !form.treatmentId) {
      setError('Harap isi nama customer dan treatment');
      return;
    }
    if (!form.consentSigned) {
      setError('Persetujuan customer (consent) harus ditandatangani');
      return;
    }

    setCreating(true);
    setError(null);
    try {
      await fetchJSON('/pos/treatment-record', {
        method: 'POST',
        body: JSON.stringify({
          customer_name: form.customerName,
          treatment_id: form.treatmentId,
          notes: form.notes,
          allergies: form.allergies,
          skin_type: form.skinType,
          reactions: form.reactions,
          consent_signed: form.consentSigned,
          before_photos: beforePhotos,
          after_photos: afterPhotos,
        }),
      });
      setShowCreate(false);
      resetForm();
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Gagal menyimpan catatan treatment');
    }
    setCreating(false);
  }

  function resetForm() {
    setForm({
      customerName: '',
      treatmentId: '',
      notes: '',
      allergies: '',
      skinType: '',
      reactions: '',
      consentSigned: false,
    });
    setBeforePhotos([]);
    setAfterPhotos([]);
  }

  const filteredRecords = records.filter((r) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      r.customerName.toLowerCase().includes(q) ||
      r.treatmentName.toLowerCase().includes(q) ||
      r.posCode.toLowerCase().includes(q)
    );
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
        <h1 className="text-lg font-bold text-[var(--charcoal)]">Catatan Treatment</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-[var(--gold)] text-white px-4 py-2 rounded-xl text-sm font-medium active:bg-[var(--gold)]/90 transition-colors"
        >
          + Catatan Baru
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
          placeholder="Cari customer, treatment, atau kode..."
          className="w-full pl-10 pr-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
        />
      </div>

      {/* Records List */}
      {loading ? (
        <LoadingSkeleton rows={4} />
      ) : filteredRecords.length ? (
        <div className="space-y-3">
          {filteredRecords.map((record) => (
            <button
              key={record.id}
              onClick={() => setSelectedRecord(record)}
              className="w-full bg-white rounded-xl p-4 border border-gray-100 shadow-sm text-left active:bg-gray-50 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-[var(--charcoal)]">{record.customerName}</span>
                    {record.consentSigned && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
                        ✓ Consent
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{record.treatmentName} • {record.staffName}</p>
                </div>
                <span className="text-xs text-gray-400 font-mono">{record.posCode}</span>
              </div>
              <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
                <span>📅 {new Date(record.date).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })}</span>
                {record.beforePhotos.length > 0 && <span>📸 {record.beforePhotos.length} foto</span>}
                {record.notes && <span>📝 Ada catatan</span>}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl p-8 border border-gray-100 text-center">
          <span className="text-4xl">📋</span>
          <p className="text-gray-400 text-sm mt-3">
            {search ? 'Catatan tidak ditemukan' : 'Belum ada catatan treatment'}
          </p>
        </div>
      )}

      {/* Detail Modal */}
      <Modal open={!!selectedRecord} onClose={() => setSelectedRecord(null)} title="Detail Catatan Treatment">
        {selectedRecord && (
          <div className="space-y-3 text-left">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-400 text-xs">Customer</span>
                <p className="font-medium text-[var(--charcoal)]">{selectedRecord.customerName}</p>
              </div>
              <div>
                <span className="text-gray-400 text-xs">Kode</span>
                <p className="font-medium text-[var(--charcoal)] font-mono">{selectedRecord.posCode}</p>
              </div>
              <div>
                <span className="text-gray-400 text-xs">Treatment</span>
                <p className="font-medium text-[var(--charcoal)]">{selectedRecord.treatmentName}</p>
              </div>
              <div>
                <span className="text-gray-400 text-xs">Staff</span>
                <p className="font-medium text-[var(--charcoal)]">{selectedRecord.staffName}</p>
              </div>
            </div>

            {selectedRecord.skinType && (
              <div>
                <span className="text-gray-400 text-xs">Tipe Kulit</span>
                <p className="text-sm text-[var(--charcoal)]">{selectedRecord.skinType}</p>
              </div>
            )}
            {selectedRecord.allergies && (
              <div>
                <span className="text-gray-400 text-xs">Alergi</span>
                <p className="text-sm text-[var(--charcoal)]">{selectedRecord.allergies}</p>
              </div>
            )}
            {selectedRecord.notes && (
              <div>
                <span className="text-gray-400 text-xs">Catatan</span>
                <p className="text-sm text-[var(--charcoal)]">{selectedRecord.notes}</p>
              </div>
            )}
            {selectedRecord.reactions && (
              <div>
                <span className="text-gray-400 text-xs">Reaksi</span>
                <p className="text-sm text-red-600">{selectedRecord.reactions}</p>
              </div>
            )}

            {/* Photos */}
            {selectedRecord.beforePhotos.length > 0 && (
              <div>
                <span className="text-gray-400 text-xs">Foto Sebelum</span>
                <div className="flex gap-2 mt-1 overflow-x-auto">
                  {selectedRecord.beforePhotos.map((photo, i) => (
                    <img key={i} src={photo} alt={`Before ${i + 1}`} className="w-20 h-20 object-cover rounded-lg" />
                  ))}
                </div>
              </div>
            )}
            {selectedRecord.afterPhotos.length > 0 && (
              <div>
                <span className="text-gray-400 text-xs">Foto Sesudah</span>
                <div className="flex gap-2 mt-1 overflow-x-auto">
                  {selectedRecord.afterPhotos.map((photo, i) => (
                    <img key={i} src={photo} alt={`After ${i + 1}`} className="w-20 h-20 object-cover rounded-lg" />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => { setShowCreate(false); resetForm(); }} title="Catatan Treatment Baru">
        <form onSubmit={handleCreate} className="space-y-3 text-left">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Nama Customer *</label>
            <input
              type="text"
              value={form.customerName}
              onChange={(e) => setForm({ ...form, customerName: e.target.value })}
              placeholder="Nama customer"
              required
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            />
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
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tipe Kulit</label>
            <select
              value={form.skinType}
              onChange={(e) => setForm({ ...form, skinType: e.target.value })}
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            >
              <option value="">Pilih tipe kulit</option>
              <option value="NORMAL">Normal</option>
              <option value="KERING">Kering</option>
              <option value="BERMINYAK">Berminyak</option>
              <option value="KOMBINASI">Kombinasi</option>
              <option value="SENSITIF">Sensitif</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Alergi</label>
            <input
              type="text"
              value={form.allergies}
              onChange={(e) => setForm({ ...form, allergies: e.target.value })}
              placeholder="Riwayat alergi (opsional)"
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent"
            />
          </div>

          {/* Before Photos */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Foto Sebelum Treatment</label>
            <div className="flex gap-2 flex-wrap">
              {beforePhotos.map((photo, i) => (
                <div key={i} className="relative">
                  <img src={photo} alt={`Before ${i + 1}`} className="w-16 h-16 object-cover rounded-lg" />
                  <button
                    type="button"
                    onClick={() => removePhoto(i, 'before')}
                    className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => beforeInputRef.current?.click()}
                className="w-16 h-16 border-2 border-dashed border-gray-200 rounded-lg flex items-center justify-center text-gray-400 active:bg-gray-50"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
              </button>
              <input
                ref={beforeInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                multiple
                onChange={(e) => handlePhotoSelect(e, 'before')}
                className="hidden"
              />
            </div>
          </div>

          {/* After Photos */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Foto Sesudah Treatment</label>
            <div className="flex gap-2 flex-wrap">
              {afterPhotos.map((photo, i) => (
                <div key={i} className="relative">
                  <img src={photo} alt={`After ${i + 1}`} className="w-16 h-16 object-cover rounded-lg" />
                  <button
                    type="button"
                    onClick={() => removePhoto(i, 'after')}
                    className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => afterInputRef.current?.click()}
                className="w-16 h-16 border-2 border-dashed border-gray-200 rounded-lg flex items-center justify-center text-gray-400 active:bg-gray-50"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
              </button>
              <input
                ref={afterInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                multiple
                onChange={(e) => handlePhotoSelect(e, 'after')}
                className="hidden"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Catatan Treatment</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder="Catatan kondisi kulit, produk yang digunakan, dll."
              rows={3}
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent resize-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Reaksi / Efek Samping</label>
            <textarea
              value={form.reactions}
              onChange={(e) => setForm({ ...form, reactions: e.target.value })}
              placeholder="Catatan reaksi kulit setelah treatment (opsional)"
              rows={2}
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent resize-none"
            />
          </div>

          {/* Consent */}
          <div className="bg-gray-50 rounded-xl p-3">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={form.consentSigned}
                onChange={(e) => setForm({ ...form, consentSigned: e.target.checked })}
                className="mt-1 w-4 h-4 rounded border-gray-300 text-[var(--gold)] focus:ring-[var(--gold)]"
              />
              <div>
                <span className="text-sm font-medium text-[var(--charcoal)]">Persetujuan Customer</span>
                <p className="text-xs text-gray-500 mt-0.5">
                  Customer menyetujui treatment yang akan dilakukan dan memahami risiko yang mungkin terjadi.
                </p>
              </div>
            </label>
          </div>

          <button
            type="submit"
            disabled={creating}
            className="w-full py-3 rounded-xl bg-[var(--gold)] text-white font-semibold text-sm active:bg-[var(--gold)]/90 disabled:opacity-50 transition-colors shadow-sm"
          >
            {creating ? 'Menyimpan...' : 'Simpan Catatan'}
          </button>
        </form>
      </Modal>
    </div>
  );
}
