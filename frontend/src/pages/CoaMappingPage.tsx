import { useState, useEffect } from 'react';
import { coaApi } from '@/api/client';
import { CoaMapping, CoaAccount, MappingType, MappingStatusSummary } from '@/types';
import StatusBadge from '@/components/common/StatusBadge';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';

const TABS: { value: MappingType | 'IMPORT'; label: string }[] = [
  { value: 'SERVICE', label: 'Layanan' },
  { value: 'PAYMENT_METHOD', label: 'Pembayaran' },
  { value: 'DISCOUNT', label: 'Diskon' },
  { value: 'ROUNDING', label: 'Pembulatan' },
  { value: 'IMPORT', label: 'Bulk Import' },
];

export default function CoaMappingPage() {
  const [activeTab, setActiveTab] = useState<MappingType | 'IMPORT'>('SERVICE');
  const [mappings, setMappings] = useState<CoaMapping[]>([]);
  const [accounts, setAccounts] = useState<CoaAccount[]>([]);
  const [summary, setSummary] = useState<MappingStatusSummary | null>(null);
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

  const unmappedCount = (type: MappingType) => {
    if (!summary) return 0;
    const key = type.toLowerCase().replace('_', '') as keyof MappingStatusSummary;
    return summary[key]?.unmapped || 0;
  };

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-charcoal">COA Mapping</h2>

      {/* Status Summary */}
      {summary && (
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <div className="flex items-center gap-4 text-sm">
            {(['SERVICE', 'PAYMENT_METHOD', 'DISCOUNT', 'ROUNDING'] as MappingType[]).map(type => {
              const count = unmappedCount(type);
              return (
                <div key={type} className="flex items-center gap-1">
                  {count > 0 ? (
                    <span className="text-red-600 font-medium">{count} belum di-mapping</span>
                  ) : (
                    <span className="text-green-600">✓ Lengkap</span>
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
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap ${
              activeTab === tab.value ? 'bg-gold text-white' : 'bg-gray-100 text-gray-600'
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
          ) : mappings.map(m => (
            <div key={m.id} className="bg-white rounded-xl border border-gray-100 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-charcoal">{m.itemName}</p>
                  <p className="text-sm text-gray-500">{m.itemCode}</p>
                </div>
                <StatusBadge label={m.isActive ? 'Aktif' : 'Nonaktif'} variant={m.isActive ? 'success' : 'neutral'} />
              </div>
              <div className="mt-2 flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-500">COA</p>
                  <p className="text-sm font-mono text-charcoal">{m.accountCode} — {m.accountName}</p>
                </div>
                <button onClick={() => handleDelete(m.id)} className="text-red-500 text-sm">Hapus</button>
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
      // In real app, parse CSV/Excel here
      const rows: any[] = []; // parsed rows
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
          <button onClick={handleUpload} disabled={!file || validating} className="bg-gold text-white px-6 py-2 rounded-lg text-sm disabled:opacity-40">
            {validating ? 'Validasi...' : 'Validasi'}
          </button>
          <button className="bg-gray-100 text-charcoal px-6 py-2 rounded-lg text-sm">Download Template</button>
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
          <button onClick={handleApply} className="w-full bg-gold text-white py-3 rounded-xl font-medium">
            Apply Import ({results.filter(r => r.valid).length} baris valid)
          </button>
        </div>
      )}
    </div>
  );
}
