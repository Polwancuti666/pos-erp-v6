import { useState, useEffect } from 'react';
import { api } from '../api/client';

type Tab = 'journal' | 'trial' | 'ap' | 'bank' | 'asset';

interface JournalEntry { id: string; date: string; entry_date?: string; doc_key?: string; reference: string; description: string; debit: number; credit: number; total_debit?: number; total_credit?: number; status: string; }
interface TrialBalance { account: string; code: string; debit: number; credit: number; }
interface AP { id: string; vendor: string; supplier_name?: string; invoice: string; invoice_no?: string; amount: number; due_date: string; status: string; }
interface BankAccount { id: string; name: string; account_name?: string; account_no: string; bank: string; bank_name?: string; balance: number; }
interface Asset { id: string; name: string; category: string; purchase_date: string; value: number; current_value?: number; purchase_cost?: number; depreciation: number; }


const tabs: { key: Tab; label: string }[] = [
  { key: 'journal', label: 'Journal Entries' },
  { key: 'trial', label: 'Trial Balance' },
  { key: 'ap', label: 'Accounts Payable' },
  { key: 'bank', label: 'Bank Accounts' },
  { key: 'asset', label: 'Assets' },
];

const formatCurrency = (amount: number) =>
  new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(amount);

export default function FinancePage() {
  const [activeTab, setActiveTab] = useState<Tab>('journal');
  const [data, setData] = useState<Record<Tab, any[]>>({
    journal: [], trial: [], ap: [], bank: [], asset: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const fetchers: Record<Tab, () => Promise<any>> = {
      journal: api.getJournalEntries,
      trial: api.getTrialBalance,
      ap: api.getAP,
      bank: api.getBankAccounts,
      asset: api.getAssets,
    };
    fetchers[activeTab]()
      .then((res) => setData((prev) => ({ ...prev, [activeTab]: Array.isArray(res) ? res : res.items || res.data || [] })))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [activeTab]);

  const renderTable = () => {
    if (loading) return <div className="flex justify-center py-8"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#C9A96E]"></div></div>;
    if (error) return <div className="bg-red-50 text-red-700 p-4 rounded-lg">{error}</div>;
    const items = data[activeTab];
    if (!items.length) return <div className="text-gray-500 text-center py-8">No data found</div>;

    switch (activeTab) {
      case 'journal':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Date</th>
                <th className="px-4 py-3 text-left text-sm">Reference</th>
                <th className="px-4 py-3 text-left text-sm">Description</th>
                <th className="px-4 py-3 text-right text-sm">Debit</th>
                <th className="px-4 py-3 text-right text-sm">Credit</th>
                <th className="px-4 py-3 text-left text-sm">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((j: JournalEntry) => (
                <tr key={j.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm">{new Date(j.entry_date || j.date).toLocaleDateString()}</td>
                  <td className="px-4 py-3 font-mono text-sm">{j.doc_key || j.reference}</td>
                  <td className="px-4 py-3">{j.description}</td>
                  <td className="px-4 py-3 text-right text-green-600">{(j.total_debit || j.debit) > 0 ? formatCurrency(j.total_debit || j.debit) : '-'}</td>
                  <td className="px-4 py-3 text-right text-red-600">{(j.total_credit || j.credit) > 0 ? formatCurrency(j.total_credit || j.credit) : '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-sm ${
                      j.status === 'posted' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {j.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'trial':
        const totalDebit = items.reduce((sum: number, t: TrialBalance) => sum + t.debit, 0);
        const totalCredit = items.reduce((sum: number, t: TrialBalance) => sum + t.credit, 0);
        return (
          <div>
            <table className="w-full">
              <thead className="bg-[#C9A96E] text-white">
                <tr>
                  <th className="px-4 py-3 text-left text-sm">Code</th>
                  <th className="px-4 py-3 text-left text-sm">Account</th>
                  <th className="px-4 py-3 text-right text-sm">Debit</th>
                  <th className="px-4 py-3 text-right text-sm">Credit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {items.map((t: TrialBalance, i: number) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-sm">{t.code}</td>
                    <td className="px-4 py-3">{t.account}</td>
                    <td className="px-4 py-3 text-right">{t.debit > 0 ? formatCurrency(t.debit) : '-'}</td>
                    <td className="px-4 py-3 text-right">{t.credit > 0 ? formatCurrency(t.credit) : '-'}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-gray-100 font-bold">
                <tr>
                  <td colSpan={2} className="px-4 py-3 text-right">Total</td>
                  <td className="px-4 py-3 text-right text-green-600">{formatCurrency(totalDebit)}</td>
                  <td className="px-4 py-3 text-right text-red-600">{formatCurrency(totalCredit)}</td>
                </tr>
              </tfoot>
            </table>
            {totalDebit !== totalCredit && (
              <div className="bg-red-50 text-red-700 p-3 mt-2 rounded text-sm">
                ⚠️ Trial balance is out of balance by {formatCurrency(Math.abs(totalDebit - totalCredit))}
              </div>
            )}
          </div>
        );
      case 'ap':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Vendor</th>
                <th className="px-4 py-3 text-left text-sm">Invoice</th>
                <th className="px-4 py-3 text-right text-sm">Amount</th>
                <th className="px-4 py-3 text-left text-sm">Due Date</th>
                <th className="px-4 py-3 text-left text-sm">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((a: AP) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{a.supplier_name || a.vendor}</td>
                  <td className="px-4 py-3 font-mono text-sm">{a.invoice_no || a.invoice}</td>
                  <td className="px-4 py-3 text-right">{formatCurrency(a.amount)}</td>
                  <td className="px-4 py-3">{new Date(a.due_date).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-sm ${
                      a.status === 'paid' ? 'bg-green-100 text-green-700' :
                      a.status === 'overdue' ? 'bg-red-100 text-red-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {a.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );
      case 'bank':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
            {items.map((b: BankAccount) => (
              <div key={b.id} className="border border-gray-200 rounded-lg p-4">
                <h3 className="font-semibold text-[#C9A96E]">{b.account_name || b.name}</h3>
                <p className="text-sm text-gray-600">{b.bank_name || b.bank}</p>
                <p className="text-sm font-mono mt-1">{b.account_no}</p>
                <p className="text-2xl font-bold mt-3">{formatCurrency(b.balance)}</p>
              </div>
            ))}
          </div>
        );
      case 'asset':
        return (
          <table className="w-full">
            <thead className="bg-[#C9A96E] text-white">
              <tr>
                <th className="px-4 py-3 text-left text-sm">Name</th>
                <th className="px-4 py-3 text-left text-sm">Category</th>
                <th className="px-4 py-3 text-left text-sm">Purchase Date</th>
                <th className="px-4 py-3 text-right text-sm">Value</th>
                <th className="px-4 py-3 text-right text-sm">Depreciation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((a: Asset) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{a.name}</td>
                  <td className="px-4 py-3">{a.category}</td>
                  <td className="px-4 py-3">{new Date(a.purchase_date).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-right">{formatCurrency(a.current_value || a.value || a.purchase_cost || 0)}</td>
                  <td className="px-4 py-3 text-right text-red-600">{formatCurrency((a.purchase_cost || 0) - (a.current_value || a.purchase_cost || 0))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        );
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Finance</h1>
      
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