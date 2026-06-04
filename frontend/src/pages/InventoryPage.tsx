import { useState, useEffect } from 'react';
import { api } from '../api/client';

type Tab = 'stock' | 'batches' | 'bom' | 'lowstock' | 'alerts';

interface StockCard { id: string; product: string; product_name?: string; sku: string; quantity: number; balance?: number; unit: string; min_stock: number; last_updated: string; last_movement_date?: string; }
interface Batch { id: string; product: string; product_name?: string; batch_no: string; quantity: number; qty?: number; expiry: string; expiry_date?: string; status: string; }
interface BOM { id: string; treatment: string; ingredients: Array<{ product: string; quantity: number; unit: string }>; }
interface LowStock { id: string; product: string; product_name?: string; sku: string; current: number; balance?: number; minimum: number; }

const tabs: { key: Tab; label: string }[] = [
  { key: 'stock', label: 'Stock Card' },
  { key: 'batches', label: 'Batches' },
  { key: 'bom', label: 'BOM' },
  { key: 'lowstock', label: 'Low Stock' },
  { key: 'alerts', label: '⚠️ Alerts' },
];

export default function InventoryPage() {
  const [activeTab, setActiveTab] = useState<Tab>('stock');
  const [data, setData] = useState<Record<Tab, any[]>>({
    stock: [], batches: [], bom: [], lowstock: [], alerts: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [alertSummary, setAlertSummary] = useState({ out_of_stock: 0, critical: 0, low: 0, total_alerts: 0 });
  const [editingThreshold, setEditingThreshold] = useState<{ id: string; name: string; threshold: number } | null>(null);
  const [savingThreshold, setSavingThreshold] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const fetchers: Record<Tab, () => Promise<any>> = {
      stock: api.getStockCards,
      batches: api.getBatches,
      bom: api.getBOMs,
      lowstock: api.getLowStock,
      alerts: api.getInventoryAlerts,
    };
    fetchers[activeTab]()
      .then((res) => {
        const items = Array.isArray(res) ? res : res.items || res.data || [];
        setData((prev) => ({ ...prev, [activeTab]: items }));
        if (activeTab === 'alerts' && res.summary) {
          setAlertSummary(res.summary);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [activeTab]);

  const getStockColor = (qty: number, min: number) => {
    if (qty <= 0) return 'text-red-600 bg-red-50';
    if (qty < min) return 'text-orange-600 bg-orange-50';
    return 'text-green-600 bg-green-50';
  };

  const renderTable = () => {
    if (loading) return <div className="flex justify-center py-8"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#C9A96E]"></div></div>;
    if (error) return <div className="bg-red-50 text-red-700 p-4 rounded-lg">{error}</div>;
    const items = data[activeTab];
    if (!items.length) return <div className="text-gray-500 text-center py-8">No data found</div>;

    switch (activeTab) {
      case 'stock':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Product</th>
                <th className="px-4 py-3 text-left text-sm">SKU</th>
                <th className="px-4 py-3 text-right text-sm">Quantity</th>
                <th className="px-4 py-3 text-left text-sm">Unit</th>
                <th className="px-4 py-3 text-left text-sm">Last Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((s: StockCard) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{s.product_name || s.product}</td>
                  <td className="px-4 py-3 font-mono text-sm">{s.sku}</td>
                  <td className={`px-4 py-3 text-right font-semibold ${getStockColor(s.balance || s.quantity, s.min_stock || 5)}`}>
                    {s.balance || s.quantity}
                  </td>
                  <td className="px-4 py-3">{s.unit}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{new Date(s.last_movement_date || s.last_updated).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'batches':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Product</th>
                <th className="px-4 py-3 text-left text-sm">Batch No</th>
                <th className="px-4 py-3 text-right text-sm">Quantity</th>
                <th className="px-4 py-3 text-left text-sm">Expiry</th>
                <th className="px-4 py-3 text-left text-sm">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((b: Batch) => (
                <tr key={b.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{b.product_name || b.product}</td>
                  <td className="px-4 py-3 font-mono">{b.batch_no}</td>
                  <td className="px-4 py-3 text-right">{b.qty || b.quantity}</td>
                  <td className="px-4 py-3">{new Date(b.expiry_date || b.expiry).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-sm ${
                      b.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {b.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'bom':
        return (
          <div className="space-y-4 p-4">
            {items.map((bom: BOM) => (
              <div key={bom.id} className="border border-gray-200 rounded-lg p-4">
                <h3 className="font-semibold text-[#C9A96E] mb-3">{bom.treatment}</h3>
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-sm">Ingredient</th>
                      <th className="px-3 py-2 text-right text-sm">Quantity</th>
                      <th className="px-3 py-2 text-left text-sm">Unit</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {bom.ingredients.map((ing, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 text-sm">{ing.product}</td>
                        <td className="px-3 py-2 text-sm text-right">{ing.quantity}</td>
                        <td className="px-3 py-2 text-sm">{ing.unit}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        );
      case 'lowstock':
        return (
          <table className="w-full">
            <thead className="bg-red-500 text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Product</th>
                <th className="px-4 py-3 text-left text-sm">SKU</th>
                <th className="px-4 py-3 text-right text-sm">Current</th>
                <th className="px-4 py-3 text-right text-sm">Minimum</th>
                <th className="px-4 py-3 text-right text-sm">Deficit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((l: LowStock) => (
                <tr key={l.id} className="hover:bg-red-50">
                  <td className="px-4 py-3 font-semibold">{l.product_name || l.product}</td>
                  <td className="px-4 py-3 font-mono text-sm">{l.sku}</td>
                  <td className="px-4 py-3 text-right font-bold text-red-600">{l.balance || l.current}</td>
                  <td className="px-4 py-3 text-right">{l.minimum || '-'}</td>
                  <td className="px-4 py-3 text-right text-red-600 font-bold">{l.minimum - l.current}</td>
                </tr>
              ))}
            </tbody>
          </table>
        );

      case 'alerts':
        return (
          <>
            {/* Summary Cards */}
            <div className="p-4 grid grid-cols-3 gap-4">
              <div className="bg-red-50 rounded-xl p-4 text-center">
                <p className="text-3xl font-bold text-red-600">{alertSummary.out_of_stock}</p>
                <p className="text-sm text-red-500">Out of Stock</p>
              </div>
              <div className="bg-orange-50 rounded-xl p-4 text-center">
                <p className="text-3xl font-bold text-orange-600">{alertSummary.critical}</p>
                <p className="text-sm text-orange-500">Critical</p>
              </div>
              <div className="bg-yellow-50 rounded-xl p-4 text-center">
                <p className="text-3xl font-bold text-yellow-600">{alertSummary.low}</p>
                <p className="text-sm text-yellow-500">Low</p>
              </div>
            </div>

            {items.length === 0 ? (
              <div className="text-center py-8 text-green-600">✅ Semua stok dalam kondisi aman</div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-800 text-white">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm">Status</th>
                    <th className="px-4 py-3 text-left text-sm">Product</th>
                    <th className="px-4 py-3 text-left text-sm">SKU</th>
                    <th className="px-4 py-3 text-right text-sm">Stok</th>
                    <th className="px-4 py-3 text-right text-sm">Min. Threshold</th>
                    <th className="px-4 py-3 text-center text-sm">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {items.map((item: any) => {
                    const levelColors: Record<string, string> = {
                      out_of_stock: 'bg-red-100 text-red-700',
                      critical: 'bg-orange-100 text-orange-700',
                      low: 'bg-yellow-100 text-yellow-700',
                      ok: 'bg-green-100 text-green-700',
                    };
                    const levelLabels: Record<string, string> = {
                      out_of_stock: '⛔ Habis',
                      critical: '🔴 Kritis',
                      low: '🟡 Rendah',
                      ok: '🟢 Aman',
                    };
                    return (
                      <tr key={item.id} className={`hover:bg-gray-50 ${item.alert_level !== 'ok' ? 'bg-red-50/30' : ''}`}>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${levelColors[item.alert_level] || ''}`}>
                            {levelLabels[item.alert_level] || item.alert_level}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-medium">{item.name}</td>
                        <td className="px-4 py-3 font-mono text-sm">{item.sku}</td>
                        <td className="px-4 py-3 text-right font-bold text-lg">{Number(item.balance)}</td>
                        <td className="px-4 py-3 text-right text-gray-500">{Number(item.threshold)}</td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => setEditingThreshold({ id: item.id, name: item.name, threshold: Number(item.threshold) })}
                            className="text-[#C9A96E] hover:text-[#8B6914] text-sm font-medium"
                          >⚙️ Threshold</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}

            {/* Threshold Edit Modal */}
            {editingThreshold && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-sm">
                  <h3 className="text-lg font-bold text-gray-800 mb-2">Set Minimum Stock</h3>
                  <p className="text-sm text-gray-500 mb-4">{editingThreshold.name}</p>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Min. Stock Threshold</label>
                    <input
                      type="number"
                      value={editingThreshold.threshold}
                      onChange={(e) => setEditingThreshold({ ...editingThreshold, threshold: Number(e.target.value) })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-lg font-semibold focus:ring-2 focus:ring-[#C9A96E] focus:border-transparent"
                      min="0"
                    />
                    <p className="text-xs text-gray-400 mt-1">Produk akan muncul alert jika stok di bawah angka ini</p>
                  </div>
                  <div className="flex justify-end gap-3 mt-6">
                    <button onClick={() => setEditingThreshold(null)} className="px-4 py-2 text-gray-600 font-medium" disabled={savingThreshold}>Batal</button>
                    <button
                      onClick={async () => {
                        setSavingThreshold(true);
                        try {
                          await api.updateProductThreshold(editingThreshold.id, editingThreshold.threshold);
                          // Refresh alerts
                          const res = await api.getInventoryAlerts();
                          setData((prev) => ({ ...prev, alerts: res.items || [] }));
                          if (res.summary) setAlertSummary(res.summary);
                          setEditingThreshold(null);
                        } catch (err: any) { alert('Gagal: ' + err.message); }
                        finally { setSavingThreshold(false); }
                      }}
                      disabled={savingThreshold}
                      className="px-6 py-2 bg-[#C9A96E] text-white rounded-lg hover:bg-[#8B6914] font-medium disabled:opacity-50"
                    >{savingThreshold ? 'Saving...' : 'Simpan'}</button>
                  </div>
                </div>
              </div>
            )}
          </>
        );
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Inventory</h1>
      
      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
              activeTab === tab.key
                ? 'bg-[#C9A96E] text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          {renderTable()}
        </div>
      </div>
    </div>
  );
}