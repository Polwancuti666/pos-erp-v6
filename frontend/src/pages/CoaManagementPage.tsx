import { useState, useEffect, useCallback } from 'react';
import { fetchJSON } from '../api/client';

// ── Types ────────────────────────────────────────────────────────────────────

interface COAAccount {
  id: string; account_code: string; account_name: string; account_type: string;
  parent_code: string | null; level: number; is_active: boolean;
  usage_count?: number; mapping_status?: string; mapped_to_type?: string;
  mapping_confidence?: number;
}

interface MappingItem {
  id: number; coa_id: string; mapping_type: string; item_type: string;
  confidence: number; account_code: string; account_name: string;
}

type Tab = 'accounts' | 'add' | 'mapping' | 'audit';

const tabs: { key: Tab; label: string }[] = [
  { key: 'accounts', label: '📋 Daftar Akun' },
  { key: 'add', label: '➕ Tambah Akun' },
  { key: 'mapping', label: '🔗 Mapping Review' },
  { key: 'audit', label: '📝 Audit Log' },
];

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(amount);

const Spinner = () => (
  <div className="flex justify-center py-8">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#C9A96E]"></div>
  </div>
);

const statusBadge = (status: string) => {
  const map: Record<string, string> = {
    mapped: 'bg-green-100 text-green-700',
    unmapped: 'bg-gray-100 text-gray-500',
    needs_review: 'bg-yellow-100 text-yellow-700',
  };
  return map[status] || 'bg-gray-100 text-gray-500';
};

// ── 1. DAFTAR AKUN ───────────────────────────────────────────────────────────

function AccountsSection() {
  const [accounts, setAccounts] = useState<COAAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState<number | ''>('');
  const [editing, setEditing] = useState<COAAccount | null>(null);
  const [editField, setEditField] = useState<'name' | 'code' | null>(null);
  const [editValue, setEditValue] = useState('');
  const [editResult, setEditResult] = useState<{ type: 'success' | 'error' | 'warning'; msg: string } | null>(null);

  const loadAccounts = useCallback(() => {
    setLoading(true);
    let params = '';
    if (search) params += `search=${encodeURIComponent(search)}&`;
    if (levelFilter !== '') params += `level=${levelFilter}&`;
    fetchJSON(`/coa/accounts?${params}`)
      .then(r => setAccounts(r.accounts || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [search, levelFilter]);

  useEffect(() => { loadAccounts(); }, [loadAccounts]);

  const startEdit = (acc: COAAccount, field: 'name' | 'code') => {
    setEditing(acc);
    setEditField(field);
    setEditValue(field === 'name' ? acc.account_name : acc.account_code);
    setEditResult(null);
  };

  const saveEdit = async () => {
    if (!editing || !editField) return;
    try {
      const result = await fetchJSON<any>(`/coa/accounts/${editing.id}/${editField}`, {
        method: 'PUT',
        body: JSON.stringify(editField === 'name' ? { account_name: editValue } : { account_code: editValue }),
      });
      setEditResult({ type: 'success', msg: result.warning || 'Berhasil disimpan' });
      setEditing(null);
      setEditField(null);
      loadAccounts();
    } catch (err: any) {
      setEditResult({ type: 'error', msg: err.message || 'Gagal menyimpan' });
    }
  };

  const toggleStatus = async (acc: COAAccount) => {
    try {
      const result = await fetchJSON<any>(`/coa/accounts/${acc.id}/status`, {
        method: 'PUT',
        body: JSON.stringify({ is_active: !acc.is_active }),
      });
      if (result.warning) {
        if (!confirm(result.warning + '\n\nTetap lanjutkan?')) return;
      }
      loadAccounts();
    } catch {}
  };

  return (
    <div>
      <div className="flex flex-wrap gap-3 mb-4">
        <input className="border rounded px-3 py-2 flex-1 min-w-[200px]" placeholder="🔍 Cari kode atau nama akun..." value={search} onChange={e => setSearch(e.target.value)} />
        <select className="border rounded px-3 py-2" value={levelFilter} onChange={e => setLevelFilter(e.target.value === '' ? '' : Number(e.target.value))}>
          <option value="">Semua Level</option>
          <option value={1}>Level 1 — Kelompok</option>
          <option value={2}>Level 2 — Golongan</option>
          <option value={3}>Level 3 — Sub-golongan</option>
          <option value={4}>Level 4 — Akun Detail</option>
        </select>
      </div>

      {editResult && (
        <div className={`p-3 rounded-lg mb-4 ${editResult.type === 'error' ? 'bg-red-50 text-red-700' : editResult.type === 'warning' ? 'bg-yellow-50 text-yellow-700' : 'bg-green-50 text-green-700'}`}>
          {editResult.msg}
          <button onClick={() => setEditResult(null)} className="ml-2 text-sm underline">Tutup</button>
        </div>
      )}

      {loading ? <Spinner /> : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="text-left p-2">Kode</th>
                <th className="text-left">Nama Akun</th>
                <th className="text-center">Level</th>
                <th className="text-center">Tipe</th>
                <th className="text-center">Status</th>
                <th className="text-center">Usage</th>
                <th className="text-center">Mapping</th>
                <th className="text-center">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map(acc => (
                <tr key={acc.id} className="border-b hover:bg-gray-50">
                  <td className="p-2 font-mono text-xs">
                    {editing?.id === acc.id && editField === 'code' ? (
                      <div className="flex gap-1">
                        <input className="border rounded px-2 py-1 text-xs w-24" value={editValue} onChange={e => setEditValue(e.target.value)} />
                        <button onClick={saveEdit} className="bg-green-600 text-white px-2 py-1 rounded text-xs">✓</button>
                        <button onClick={() => setEditing(null)} className="bg-gray-400 text-white px-2 py-1 rounded text-xs">✕</button>
                      </div>
                    ) : acc.account_code}
                  </td>
                  <td>
                    {editing?.id === acc.id && editField === 'name' ? (
                      <div className="flex gap-1">
                        <input className="border rounded px-2 py-1 text-xs flex-1" value={editValue} onChange={e => setEditValue(e.target.value)} />
                        <button onClick={saveEdit} className="bg-green-600 text-white px-2 py-1 rounded text-xs">✓</button>
                        <button onClick={() => setEditing(null)} className="bg-gray-400 text-white px-2 py-1 rounded text-xs">✕</button>
                      </div>
                    ) : (
                      <span style={{ paddingLeft: `${(acc.level - 1) * 16}px` }}>
                        {acc.level > 1 && <span className="text-gray-400 mr-1">└</span>}
                        {acc.account_name}
                      </span>
                    )}
                  </td>
                  <td className="text-center">{acc.level}</td>
                  <td className="text-center">
                    <span className="text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-700">{acc.account_type}</span>
                  </td>
                  <td className="text-center">
                    <button onClick={() => toggleStatus(acc)} className={`text-xs px-2 py-0.5 rounded cursor-pointer ${acc.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {acc.is_active ? 'Aktif' : 'Nonaktif'}
                    </button>
                  </td>
                  <td className="text-center text-xs">{acc.usage_count || 0}</td>
                  <td className="text-center">
                    <span className={`text-xs px-2 py-0.5 rounded ${statusBadge(acc.mapping_status || 'unmapped')}`}>
                      {acc.mapping_status || 'unmapped'}
                    </span>
                  </td>
                  <td className="text-center">
                    <div className="flex gap-1 justify-center">
                      <button onClick={() => startEdit(acc, 'name')} className="text-blue-600 hover:underline text-xs" title="Edit nama">✏️ Nama</button>
                      <button onClick={() => startEdit(acc, 'code')} className="text-purple-600 hover:underline text-xs" title="Edit kode">🔢 Kode</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {accounts.length === 0 && <p className="text-gray-500 text-center py-8">Tidak ada akun ditemukan</p>}
        </div>
      )}
    </div>
  );
}

// ── 2. TAMBAH AKUN ───────────────────────────────────────────────────────────

function AddAccountSection() {
  const [level1, setLevel1] = useState<COAAccount[]>([]);
  const [level2, setLevel2] = useState<COAAccount[]>([]);
  const [level3, setLevel3] = useState<COAAccount[]>([]);
  const [sel1, setSel1] = useState('');
  const [sel2, setSel2] = useState('');
  const [sel3, setSel3] = useState('');
  const [accountName, setAccountName] = useState('');
  const [accountCode, setAccountCode] = useState('');
  const [autoCode, setAutoCode] = useState('');
  const [codeAvailable, setCodeAvailable] = useState<boolean | null>(null);
  const [nameExists, setNameExists] = useState<{ exists: boolean; code?: string } | null>(null);
  const [result, setResult] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchJSON('/coa/accounts?level=1&limit=100').then(r => setLevel1(r.accounts || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (sel1) {
      fetchJSON(`/coa/accounts?parent_code=${sel1}&limit=100`).then(r => setLevel2(r.accounts || [])).catch(() => {});
      setSel2(''); setSel3(''); setLevel3([]);
    }
  }, [sel1]);

  useEffect(() => {
    if (sel2) {
      fetchJSON(`/coa/accounts?parent_code=${sel2}&limit=100`).then(r => setLevel3(r.accounts || [])).catch(() => {});
      setSel3('');
    }
  }, [sel2]);

  useEffect(() => {
    if (sel3) {
      fetchJSON(`/coa/accounts/suggest-code?parent_code=${encodeURIComponent(sel3)}`)
        .then(r => { setAutoCode(r.suggested_code || ''); setAccountCode(r.suggested_code || ''); })
        .catch(() => {});
    }
  }, [sel3]);

  useEffect(() => {
    if (accountCode && accountCode.split('.').length === 4) {
      fetchJSON(`/coa/accounts/check-code/${encodeURIComponent(accountCode)}`)
        .then(r => setCodeAvailable(r.available)).catch(() => {});
    }
  }, [accountCode]);

  useEffect(() => {
    if (accountName.length > 2) {
      const timer = setTimeout(() => {
        fetchJSON(`/coa/accounts/check-name/${encodeURIComponent(accountName)}`)
          .then(r => setNameExists(r)).catch(() => {});
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [accountName]);

  const handleSave = async () => {
    if (!sel3 || !accountName || !accountCode) return;
    setSaving(true);
    try {
      const r = await fetchJSON<any>('/coa/accounts', {
        method: 'POST',
        body: JSON.stringify({ parent_code: sel3, account_code: accountCode, account_name: accountName, is_active: true }),
      });
      setResult({ type: 'success', data: r });
      setAccountName(''); setAccountCode('');
    } catch (err: any) {
      setResult({ type: 'error', msg: err.message });
    }
    setSaving(false);
  };

  const parentType = level1.find(a => a.account_code === sel1)?.account_type || '';

  return (
    <div className="max-w-2xl">
      <h3 className="text-lg font-semibold mb-4">➕ Tambah Akun Baru</h3>
      <p className="text-sm text-gray-500 mb-4">Tambahkan akun COA baru setelah onboarding. Akun baru harus mengikuti struktur 4 Level yang sudah ada.</p>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Level 1 — Kelompok Akun</label>
          <select className="w-full border rounded px-3 py-2" value={sel1} onChange={e => setSel1(e.target.value)}>
            <option value="">Pilih Kelompok...</option>
            {level1.map(a => <option key={a.account_code} value={a.account_code}>{a.account_code} — {a.account_name}</option>)}
          </select>
        </div>

        {sel1 && (
          <div>
            <label className="block text-sm font-medium mb-1">Level 2 — Golongan</label>
            <select className="w-full border rounded px-3 py-2" value={sel2} onChange={e => setSel2(e.target.value)}>
              <option value="">Pilih Golongan...</option>
              {level2.map(a => <option key={a.account_code} value={a.account_code}>{a.account_code} — {a.account_name}</option>)}
            </select>
          </div>
        )}

        {sel2 && (
          <div>
            <label className="block text-sm font-medium mb-1">Level 3 — Sub-golongan</label>
            <select className="w-full border rounded px-3 py-2" value={sel3} onChange={e => setSel3(e.target.value)}>
              <option value="">Pilih Sub-golongan...</option>
              {level3.map(a => <option key={a.account_code} value={a.account_code}>{a.account_code} — {a.account_name}</option>)}
            </select>
          </div>
        )}

        {sel3 && (
          <>
            <div>
              <label className="block text-sm font-medium mb-1">Tipe Akun (otomatis dari parent)</label>
              <span className="inline-block bg-blue-50 text-blue-700 px-3 py-2 rounded text-sm">{parentType}</span>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Nama Akun</label>
              <input className="w-full border rounded px-3 py-2" placeholder="Contoh: Eyelash Extension Classic" value={accountName} onChange={e => setAccountName(e.target.value)} />
              <p className="text-xs text-gray-400 mt-1">💡 Gunakan nama yang sama persis dengan nama layanan di POS agar mapping otomatis berhasil</p>
              {nameExists?.exists && (
                <p className="text-xs text-yellow-600 mt-1">⚠️ Nama ini sudah dipakai kode: {nameExists.code}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Kode Akun</label>
              <div className="flex gap-2">
                <input className="flex-1 border rounded px-3 py-2 font-mono" value={accountCode} onChange={e => setAccountCode(e.target.value)} />
                {autoCode && <span className="text-xs text-gray-400 self-center">Auto: {autoCode}</span>}
              </div>
              {codeAvailable === false && <p className="text-xs text-red-600 mt-1">❌ Kode sudah digunakan</p>}
              {codeAvailable === true && <p className="text-xs text-green-600 mt-1">✅ Kode tersedia</p>}
            </div>

            <button
              onClick={handleSave}
              disabled={saving || !accountName || !accountCode || codeAvailable === false}
              className="bg-[#C9A96E] text-white px-6 py-2 rounded-lg disabled:opacity-50"
            >
              {saving ? 'Menyimpan...' : '💾 Simpan Akun'}
            </button>
          </>
        )}
      </div>

      {result && (
        <div className={`mt-4 p-4 rounded-lg ${result.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {result.type === 'success' ? (
            <>
              <p>✅ Akun berhasil ditambahkan!</p>
              {result.data?.match_result?.matched && <p className="text-sm mt-1">🔗 Mapping otomatis: {result.data.match_result.item}</p>}
              {result.data?.name_warning && <p className="text-sm text-yellow-600 mt-1">⚠️ Nama akun sudah ada dengan kode berbeda</p>}
            </>
          ) : (
            <p>❌ {result.msg}</p>
          )}
        </div>
      )}
    </div>
  );
}

// ── 3. MAPPING REVIEW ────────────────────────────────────────────────────────

function MappingReviewSection() {
  const [data, setData] = useState<{ auto_mapped: MappingItem[]; needs_review: MappingItem[]; not_found: COAAccount[] }>({ auto_mapped: [], needs_review: [], not_found: [] });
  const [loading, setLoading] = useState(true);
  const [subTab, setSubTab] = useState<'auto' | 'review' | 'notfound'>('auto');
  const [goLiveResult, setGoLiveResult] = useState<any>(null);

  const loadData = () => {
    setLoading(true);
    fetchJSON('/coa/mapping-review')
      .then(r => setData(r))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const confirmAllAuto = async () => {
    await fetchJSON('/coa/mapping-review/confirm-all-auto', { method: 'POST' });
    loadData();
  };

  const handleGoLive = async () => {
    const r = await fetchJSON<any>('/coa/mapping-review/go-live', { method: 'POST' });
    setGoLiveResult(r);
  };

  const overrideMapping = async (mappingId: number, accountCode: string) => {
    await fetchJSON(`/coa/mapping-review/${mappingId}`, {
      method: 'PUT',
      body: JSON.stringify({ account_code: accountCode }),
    });
    loadData();
  };

  if (loading) return <Spinner />;

  const totalItems = data.auto_mapped.length + data.needs_review.length + data.not_found.length;
  const confirmedItems = data.auto_mapped.filter((m: any) => m.is_confirmed).length;
  const progress = totalItems > 0 ? Math.round((confirmedItems / totalItems) * 100) : 0;

  const subTabs = [
    { key: 'auto', label: `✅ Berhasil (${data.auto_mapped.length})`, color: 'green' },
    { key: 'review', label: `⚠️ Perlu Review (${data.needs_review.length})`, color: 'yellow' },
    { key: 'notfound', label: `❌ Tidak Ditemukan (${data.not_found.length})`, color: 'red' },
  ] as const;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">🔗 Mapping Review</h3>
        <div className="flex gap-2">
          <button onClick={confirmAllAuto} className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm">✓ Konfirmasi Semua Auto</button>
          <button onClick={handleGoLive} className="bg-[#C9A96E] text-white px-4 py-2 rounded-lg text-sm">🚀 Go-Live</button>
        </div>
      </div>

      <div className="bg-gray-100 rounded-full h-3 mb-4">
        <div className="bg-[#C9A96E] h-3 rounded-full transition-all" style={{ width: `${progress}%` }} />
      </div>
      <p className="text-sm text-gray-500 mb-4">{confirmedItems} dari {totalItems} mapping sudah dikonfirmasi</p>

      {goLiveResult && (
        <div className={`p-4 rounded-lg mb-4 ${goLiveResult.success ? 'bg-green-50 text-green-700' : 'bg-yellow-50 text-yellow-700'}`}>
          {goLiveResult.success ? '🎉 Sistem siap go-live!' : `⚠️ Masih ada ${goLiveResult.pendingItems} item yang perlu review`}
          <button onClick={() => setGoLiveResult(null)} className="ml-2 text-sm underline">Tutup</button>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        {subTabs.map(t => (
          <button key={t.key} onClick={() => setSubTab(t.key)} className={`px-4 py-2 rounded-lg text-sm font-medium ${subTab === t.key ? 'bg-[#C9A96E] text-white' : 'bg-gray-100 text-gray-600'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {subTab === 'auto' && (
        <div className="space-y-2">
          {data.auto_mapped.length === 0 ? (
            <p className="text-gray-500 text-center py-8">Belum ada mapping otomatis</p>
          ) : data.auto_mapped.map((item: any) => (
            <div key={item.id} className="flex items-center justify-between bg-green-50 p-3 rounded-lg">
              <div>
                <p className="font-medium">{item.account_name}</p>
                <p className="text-xs text-gray-500">{item.account_code} → {item.mapping_type}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-green-700">{item.confidence}%</span>
                <span className="text-green-600">✓</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {subTab === 'review' && (
        <div className="space-y-2">
          {data.needs_review.length === 0 ? (
            <p className="text-gray-500 text-center py-8">Semua mapping sudah dikonfirmasi ✅</p>
          ) : data.needs_review.map((item: any) => (
            <div key={item.id} className="flex items-center justify-between bg-yellow-50 p-3 rounded-lg">
              <div>
                <p className="font-medium">{item.account_name}</p>
                <p className="text-xs text-gray-500">{item.account_code} — Confidence: {item.confidence}%</p>
              </div>
              <input
                className="border rounded px-2 py-1 text-xs w-32"
                placeholder="Kode COA..."
                onBlur={e => { if (e.target.value) overrideMapping(item.id, e.target.value); }}
              />
            </div>
          ))}
        </div>
      )}

      {subTab === 'notfound' && (
        <div className="space-y-2">
          {data.not_found.length === 0 ? (
            <p className="text-gray-500 text-center py-8">Semua akun sudah ter-mapping ✅</p>
          ) : data.not_found.map(acc => (
            <div key={acc.id} className="flex items-center justify-between bg-red-50 p-3 rounded-lg">
              <div>
                <p className="font-medium">{acc.account_name}</p>
                <p className="text-xs text-gray-500">{acc.account_code} — {acc.account_type}</p>
              </div>
              <div className="flex gap-2">
                <span className="text-red-600 text-sm">✗ Belum di-mapping</span>
                <button className="text-blue-600 text-sm underline">Tambah Akun</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── 4. AUDIT LOG ─────────────────────────────────────────────────────────────

function AuditLogSection() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchJSON('/coa/audit-log?limit=100')
      .then(r => setLogs(r.logs || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">📝 Audit Log</h3>
      {logs.length === 0 ? (
        <p className="text-gray-500 text-center py-8">Belum ada perubahan</p>
      ) : (
        <div className="space-y-2">
          {logs.map(log => (
            <div key={log.id} className="bg-gray-50 p-3 rounded-lg">
              <div className="flex justify-between">
                <span className="font-medium text-sm">{log.account_code} — {log.account_name}</span>
                <span className="text-xs text-gray-400">{new Date(log.changed_at).toLocaleString('id-ID')}</span>
              </div>
              <p className="text-sm text-gray-600 mt-1">
                <span className="font-mono bg-blue-100 px-1 rounded text-xs">{log.action}</span>
                {' '}{log.field_changed}: <span className="line-through text-red-500">{log.old_value}</span> → <span className="text-green-600">{log.new_value}</span>
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── MAIN PAGE ────────────────────────────────────────────────────────────────

export default function CoaManagementPage() {
  const [activeTab, setActiveTab] = useState<Tab>('accounts');

  const renderSection = () => {
    switch (activeTab) {
      case 'accounts': return <AccountsSection />;
      case 'add': return <AddAccountSection />;
      case 'mapping': return <MappingReviewSection />;
      case 'audit': return <AuditLogSection />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-800">Manajemen COA</h1>
          <p className="text-sm text-gray-500 mt-1">Kelola Chart of Accounts, tambah akun, dan review mapping</p>
        </div>
      </div>

      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex overflow-x-auto gap-1 py-2">
            {tabs.map(tab => (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${activeTab === tab.key ? 'bg-[#C9A96E] text-white shadow-sm' : 'text-gray-600 hover:bg-gray-100'}`}>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-6">{renderSection()}</div>
        </div>
      </div>
    </div>
  );
}
