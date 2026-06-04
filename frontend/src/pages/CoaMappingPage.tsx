import { useState, useEffect } from 'react';
import { coaApi } from '@/api/client';
import { CoaMapping, CoaAccount, MappingType } from '@/types';
import StatusBadge from '@/components/common/StatusBadge';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';

const TABS: { value: MappingType | 'IMPORT'; label: string }[] = [
  { value: 'SERVICE', label: 'Layanan' },
  { value: 'PAYMENT_METHOD', label: 'Pembayaran' },
  { value: 'DISCOUNT', label: 'Diskon' },
  { value: 'ROUNDING', label: 'Pembulatan' },
  { value: 'IMPORT', label: 'Bulk Import' },
];

// Map API mapping_type to our tab types
const TYPE_MAP: Record<string, MappingType> = {
  'service_revenue': 'SERVICE',
  'payment_method': 'PAYMENT_METHOD',
  'discount': 'DISCOUNT',
  'rounding': 'ROUNDING',
  'cash_account': 'SERVICE',
  'bank_account': 'SERVICE',
  'staff_expense': 'SERVICE',
};

export default function CoaMappingPage() {
  const [activeTab, setActiveTab] = useState<MappingType | 'IMPORT'>('SERVICE');
  const [mappings, setMappings] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [summary, setSummary] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [s, a] = await Promise.all([coaApi.statusSummary(), coaApi.searchAccounts()]);
      setSummary(s);
      setAccounts(a);
      if (activeTab !== 'IMPORT') {
        const m = await coaApi.listMappings(activeTab);
        setMappings(m);
      }
    } catch { /* empty */ }
    setLoading(false);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Hapus mapping ini?')) return;
    try { await coaApi.deleteMapping(id); await loadData(); } catch { alert('Gagal menghapus'); }
  };

  const getUnmappedCount = (type: MappingType) => {
    const item = summary.find((s: any) => TYPE_MAP[s.mapping_type] === type);
    return item?.unmapped_count || 0;
  };

  const getTotalMappings = (type: MappingType) => {
    const items = summary.filter((s: any) => TYPE_MAP[s.mapping_type] === type);
    return items.reduce((acc: number, item: any) => acc + (item.total_mappings || 0), 0);
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-[var(--charcoal)]">COA Mapping</h2>

      {/* Status Summary */}
      {summary.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {(['SERVICE', 'PAYMENT_METHOD', 'DISCOUNT', 'ROUNDING'] as MappingType[]).map(type => {
              const unmapped = getUnmappedCount(type);
              const total = getTotalMappings(type);
              const label = TABS.find(t => t.value === type)?.label || type;
              return (
                <div key={type} className="text-center p-3 rounded-lg bg-gray-50">
                  <div className="text-xs text-gray-500 mb-1">{label}</div>
                  <div className="text-lg font-bold text-[var(--charcoal)]">{total}</div>
                  {unmapped > 0 && (
                    <div className="text-xs text-red-500 mt-1">{unmapped} belum di-mapping</div>
                  )}
                  {unmapped === 0 && total > 0 && (
                    <div className="text-xs text-green-600 mt-1">✓ Lengkap</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto pb-2">
        {TABS.map(tab => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
              activeTab === tab.value
                ? 'bg-[var(--gold)] text-white shadow-sm'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'IMPORT' ? (
        <BulkImportPanel onSuccess={loadData} />
      ) : loading ? (
        <LoadingSkeleton />
      ) : (
        <div className="space-y-2">
          {mappings.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <p className="text-4xl mb-2">📋</p>
              <p>Belum ada mapping</p>
            </div>
          ) : mappings.map((m: any) => (
            <div key={m.mapping_id} className="bg-white rounded-xl border border-gray-100 p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-[var(--charcoal)]">{m.source_key}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{m.mapping_type}</p>
                </div>
                <StatusBadge label="Aktif" variant="success" />
              </div>
              <div className="mt-3 flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-500">COA</p>
                  <p className="text-sm font-mono text-[var(--charcoal)]">{m.account_code} — {m.account_name}</p>
                </div>
                <button onClick={() => handleDelete(m.mapping_id)} className="text-red-500 text-sm hover:text-red-700">
                  Hapus
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function BulkImportPanel({ onSuccess }: { onSuccess: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [validating, setValidating] = useState(false);
  const [results, setResults] = useState<any[] | null>(null);

  const handleUpload = async () => {
    if (!file) return;
    setValidating(true);
    try {
      const rows: any[] = [];
      const data = await coaApi.bulkValidate(rows);
      setResults(data.results);
    } catch { alert('Gagal validasi'); }
    setValidating(false);
  };

  const handleApply = async () => {
    if (!results) return;
    try {
      const validRows = results.filter(r => r.valid).map(r => r.row);
      await coaApi.bulkApply(validRows, []);
      onSuccess();
      alert('Import berhasil!');
    } catch { alert('Gagal import'); }
  };

  return (
    <div className="space-y-4">
      <div className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center">
        <p className="text-gray-500 mb-4">Upload file CSV/Excel</p>
        <input type="file" accept=".csv,.xlsx" onChange={e => setFile(e.target.files?.[0] || null)} className="mb-4" />
        <div className="flex gap-2 justify-center">
          <button onClick={handleUpload} disabled={!file || validating} className="bg-[var(--gold)] text-white px-6 py-2 rounded-lg text-sm disabled:opacity-40">
            {validating ? 'Validasi...' : 'Validasi'}
          </button>
          <button className="bg-gray-100 text-[var(--charcoal)] px-6 py-2 rounded-lg text-sm">Download Template</button>
        </div>
      </div>

      {results && (
        <div className="space-y-2">
          {results.map((r, i) => (
            <div key={i} className={`p-3 rounded-lg text-sm ${r.valid ? 'bg-green-50' : 'bg-red-50'}`}>
              <span className={r.valid ? 'text-green-700' : 'text-red-700'}>
                {r.valid ? '✓' : '✗'} {r.itemCode} → {r.accountCode}
                {!r.valid && <span className="ml-2 text-xs">({r.reason})</span>}
              </span>
            </div>
          ))}
          <button onClick={handleApply} className="w-full bg-[var(--gold)] text-white py-3 rounded-xl font-medium">
            Apply Import ({results.filter(r => r.valid).length} baris valid)
          </button>
        </div>
      )}
    </div>
  );
}
