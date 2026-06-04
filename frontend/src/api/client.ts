const BASE = '/api';

function getSelectedBranchId(): string {
  const p = window.location.pathname;
  const isPOS = p.startsWith('/app') || p.startsWith('/pos');
  return localStorage.getItem(isPOS ? 'pos_branch_id' : 'erp_branch_id') || '';
}

function withBranchParam(url: string, method?: string): string {
  const branchId = getSelectedBranchId();
  const httpMethod = (method || 'GET').toUpperCase();
  if (!branchId || branchId === 'all' || httpMethod !== 'GET' || url.includes('branch_id=')) return url;
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}branch_id=${encodeURIComponent(branchId)}`;
}

function withBranchBody(url: string, options?: RequestInit): RequestInit | undefined {
  const branchId = getSelectedBranchId();
  if (!branchId || branchId === 'all' || !options?.body || typeof options.body !== 'string') return options;
  const method = (options.method || 'GET').toUpperCase();
  // POS booking/create endpoints accept branch_id; avoid mutating unrelated ERP writes.
  if (method !== 'POST' || !url.startsWith('/pos/booking')) return options;
  try {
    const body = JSON.parse(options.body);
    if (!body.branch_id) body.branch_id = branchId;
    return { ...options, body: JSON.stringify(body) };
  } catch {
    return options;
  }
}

export async function fetchJSON<T = any>(url: string, options?: RequestInit): Promise<T> {
  // POS token takes priority if present (POS app context)
  const token = localStorage.getItem('pos_token') || localStorage.getItem('erp_token');
  const adjustedOptions = withBranchBody(url, options);
  const adjustedUrl = withBranchParam(url, adjustedOptions?.method);
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...adjustedOptions?.headers as Record<string, string>,
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}${adjustedUrl}`, {
    ...adjustedOptions,
    headers,
  });
  if (res.status === 401) {
    // Determine which login to redirect to based on context
    const isPOS = !!localStorage.getItem('pos_token') || window.location.pathname.startsWith('/app');
    if (isPOS) {
      localStorage.removeItem('pos_token');
      localStorage.removeItem('pos_staff');
      localStorage.removeItem('pos_shift_id');
      window.location.href = '/app/login';
    } else {
      localStorage.removeItem('erp_token');
      window.location.href = '/app/login';
    }
    throw new Error('Unauthorized – please log in');
  }
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(body ? `HTTP ${res.status}: ${body}` : `HTTP ${res.status}`);
  }
  return res.json();
}

// Main API object
export const api = {
  // Master
  getTreatments: () => fetchJSON('/master/treatment'),
  getTreatmentCategories: () => fetchJSON('/master/treatment-category'),
  getProducts: () => fetchJSON('/master/product'),
  exportProducts: () => fetchJSON('/master/product/export'),
  exportProductsCSV: () => '/master/product/export/csv',
  exportProductsXLSX: () => '/master/product/export/xlsx',
  exportProductsPDF: () => '/master/product/export/pdf',
  getProductCategories: () => fetchJSON('/master/product-category'),
  getCOA: () => fetchJSON('/master/coa'),
  getUsers: () => fetchJSON('/master/user'),
  getBeds: () => fetchJSON('/pos/beds'),
  getPaymentMethods: () => fetchJSON('/master/payment-method'),
  getBranches: () => fetchJSON('/master/branch'),
  updateBranch: (id: string, data: any) => fetchJSON(`/master/branch/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  // Customer
  getCustomers: (q?: string) => fetchJSON(`/master/customer${q ? '?q=' + encodeURIComponent(q) : ''}`),
  createCustomer: (data: any) => fetchJSON('/master/customer', { method: 'POST', body: JSON.stringify(data) }),
  updateCustomer: (id: string, data: any) => fetchJSON(`/master/customer/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  // POS
  getHomeSummary: (branchId?: string) => fetchJSON(`/pos/home-summary${branchId ? '?branch_id=' + encodeURIComponent(branchId) : ''}`),
  getTransactions: (params?: string) => fetchJSON(`/pos/transactions${params ? '?' + params : ''}`),
  getDailyClosings: () => fetchJSON('/pos/daily-closings'),
  // Inventory
  getStockCards: () => fetchJSON('/inventory/stock-card'),
  getBatches: () => fetchJSON('/inventory/batches'),
  getBOMs: () => fetchJSON('/inventory/bom'),
  getLowStock: () => fetchJSON('/inventory/low-stock'),
  getInventoryAlerts: () => fetchJSON('/inventory/alerts'),
  updateProductThreshold: (productId: string, threshold: number) => fetchJSON(`/inventory/product/${productId}/threshold`, { method: 'PUT', body: JSON.stringify({ min_stock_threshold: threshold }) }),
  // Finance
  getJournalEntries: () => fetchJSON('/finance/journal-entries'),
  getTrialBalance: () => fetchJSON('/finance/trial-balance'),
  getProfitLoss: () => fetchJSON('/finance/profit-loss'),
  getAP: () => fetchJSON('/finance/accounts-payable'),
  getBankAccounts: () => fetchJSON('/finance/bank-accounts'),
  getAssets: () => fetchJSON('/finance/assets'),
  // Reporting
  getDashboard: () => fetchJSON('/reporting/dashboard'),
  getDailySales: (params?: string) => fetchJSON(`/reporting/sales/daily${params ? '?' + params : ''}`),
  getSalesByTreatment: (params?: string) => fetchJSON(`/reporting/sales/by-treatment${params ? '?' + params : ''}`),
  getSalesByPayment: (params?: string) => fetchJSON(`/reporting/sales/by-payment${params ? '?' + params : ''}`),
  getFinanceSummary: () => fetchJSON('/reporting/finance/summary'),
  getStockSummary: () => fetchJSON('/reporting/inventory/stock-summary'),
  getTherapistPerformance: (params?: string) => fetchJSON(`/reporting/staff/therapist-performance${params ? '?' + params : ''}`),
  getCommissionSummary: (params?: string) => fetchJSON(`/reporting/commission/summary${params ? '?' + params : ''}`),
  getCommissionDetail: (params?: string) => fetchJSON(`/reporting/commission/detail${params ? '?' + params : ''}`),
  generateCommissions: (params?: string) => {
    const branchId = getSelectedBranchId();
    const branchParam = branchId && branchId !== 'all' && !(params || '').includes('branch_id=') ? `${params ? '&' : ''}branch_id=${encodeURIComponent(branchId)}` : '';
    return fetchJSON(`/reporting/commission/generate${params || branchParam ? '?' + (params || '') + branchParam : ''}`, { method: 'POST' });
  },
  markCommissionsPaid: (commissionIds: string[]) => fetchJSON('/reporting/commission/mark-paid', { method: 'POST', body: JSON.stringify({ commission_ids: commissionIds }) }),
  exportCSV: (reportType: string, params?: string) => {
    const token = localStorage.getItem('pos_token') || localStorage.getItem('erp_token');
    const branchId = getSelectedBranchId();
    const branchParam = branchId && branchId !== 'all' && !(params || '').includes('branch_id=') ? `${params ? '&' : ''}branch_id=${encodeURIComponent(branchId)}` : '';
    return fetch(`/api/reporting/export/csv?report_type=${reportType}${params ? '&' + params : ''}${branchParam ? '&' + branchParam.replace(/^&/, '') : ''}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }).then(res => {
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);
      return res.blob();
    });
  },
  exportExcel: (reportType: string, params?: string) => {
    const token = localStorage.getItem('pos_token') || localStorage.getItem('erp_token');
    const branchId = getSelectedBranchId();
    const branchParam = branchId && branchId !== 'all' && !(params || '').includes('branch_id=') ? `${params ? '&' : ''}branch_id=${encodeURIComponent(branchId)}` : '';
    return fetch(`/api/reporting/export/excel?report_type=${reportType}${params ? '&' + params : ''}${branchParam ? '&' + branchParam.replace(/^&/, '') : ''}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }).then(res => {
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);
      return res.blob();
    });
  },
  // Shift Reports
  getShiftSummary: (params?: string) => fetchJSON(`/reporting/shift/summary${params ? '?' + params : ''}`),
  getShiftStaffPerformance: (params?: string) => fetchJSON(`/reporting/shift/staff-performance${params ? '?' + params : ''}`),
  // Loyalty
  getLoyaltySummary: () => fetchJSON('/master/loyalty/summary'),
  getCustomerLoyalty: (id: string) => fetchJSON(`/master/loyalty/customer/${id}`),
  earnLoyaltyPoints: (customerId: string, data: any) => fetchJSON(`/master/loyalty/customer/${customerId}/earn`, { method: 'POST', body: JSON.stringify(data) }),
  redeemLoyaltyPoints: (customerId: string, data: any) => fetchJSON(`/master/loyalty/customer/${customerId}/redeem`, { method: 'POST', body: JSON.stringify(data) }),
  getLoyaltyLeaderboard: () => fetchJSON('/master/loyalty/leaderboard'),
  autoEarnLoyalty: (data: any) => fetchJSON('/master/loyalty/auto-earn', { method: 'POST', body: JSON.stringify(data) }),
  // Period
  getFinancialPeriods: () => fetchJSON('/period/financial-periods'),
  getPeriodStatus: () => fetchJSON('/period/status'),
  getPeriodClosings: () => fetchJSON('/period/closings'),
  lockPeriod: (id: string, lockedBy: string = '') => fetchJSON(`/period/financial-period/${id}/lock?locked_by=${encodeURIComponent(lockedBy)}`, { method: 'PUT' }),
  unlockPeriod: (id: string, data: { period_id: string; unlocked_by: string; reason: string }) => fetchJSON(`/period/financial-period/${id}/unlock`, { method: 'PUT', body: JSON.stringify(data) }),
  createPeriodClosing: (branchId: string = '', period: string = '') => fetchJSON(`/period/closing?branch_id=${branchId}&period=${period}`, { method: 'POST' }),
  updateChecklistItem: (closingId: string, data: { closing_id: string; check_name: string; status: string; checked_by?: string }) => fetchJSON(`/period/closing/${closingId}/checklist`, { method: 'PUT', body: JSON.stringify(data) }),
  reviewPeriodClosing: (id: string, reviewedBy: string = '') => fetchJSON(`/period/closing/${id}/review?reviewed_by=${encodeURIComponent(reviewedBy)}`, { method: 'PUT' }),
  closePeriod: (id: string, closedBy: string = '') => fetchJSON(`/period/closing/${id}/close?closed_by=${encodeURIComponent(closedBy)}`, { method: 'PUT' }),
  // Sync
  getSyncQueue: () => fetchJSON('/sync/queue'),
  getSyncStats: () => fetchJSON('/sync/queue/stats'),
  // Audit
  getAuditLog: () => fetchJSON('/reporting/audit'),
  // WIP
  getProductionOrders: () => fetchJSON('/wip/production-order'),
  createProductionOrder: (data: any) => fetchJSON('/wip/production-order', { method: 'POST', body: JSON.stringify(data) }),
  startProductionOrder: (id: string) => fetchJSON(`/wip/production-order/${id}/start`, { method: 'POST' }),
  completeProductionOrder: (id: string) => fetchJSON(`/wip/production-order/${id}/complete`, { method: 'POST' }),
  qcProductionOrder: (id: string, data: any) => fetchJSON(`/wip/production-order/${id}/qc`, { method: 'POST', body: JSON.stringify(data) }),
  getProductionVariance: () => fetchJSON('/wip/production-order/variance'),
  // Asset
  getAssetList: () => fetchJSON('/asset'),
  getAssetSummary: () => fetchJSON('/asset/summary'),
  createAsset: (data: any) => fetchJSON('/asset', { method: 'POST', body: JSON.stringify(data) }),
  depreciateAsset: (id: string, data: any) => fetchJSON(`/asset/${id}/depreciate`, { method: 'POST', body: JSON.stringify(data) }),
  maintainAsset: (id: string, data: any) => fetchJSON(`/asset/${id}/maintenance`, { method: 'POST', body: JSON.stringify(data) }),
  disposeAsset: (id: string, data: any) => fetchJSON(`/asset/${id}/dispose`, { method: 'POST', body: JSON.stringify(data) }),
  // Bank Recon
  getReconciliations: () => fetchJSON('/bank-recon/reconciliation/summary'),
  createReconciliation: (data: any) => fetchJSON('/bank-recon/reconciliation/create', { method: 'POST', body: JSON.stringify(data) }),
  importBankMutations: (data: any) => fetchJSON('/bank-recon/bank-mutation/import', { method: 'POST', body: JSON.stringify(data) }),
  autoMatchMutations: (data: any) => fetchJSON('/bank-recon/bank-mutation/auto-match', { method: 'POST', body: JSON.stringify(data) }),
  // Cost Center
  getCostCenters: () => fetchJSON('/cost-center/cost_center'),
  getCostCenterSummary: () => fetchJSON('/cost-center/cost-center/summary'),
  createCostCenter: (data: any) => fetchJSON('/cost-center/cost_center', { method: 'POST', body: JSON.stringify(data) }),
  // Schedule
  getSchedules: (params?: string) => fetchJSON(`/schedule${params ? '?' + params : ''}`),
  createSchedule: (data: any) => fetchJSON('/schedule', { method: 'POST', body: JSON.stringify(data) }),
  bulkCreateSchedule: (data: any) => fetchJSON('/schedule/bulk', { method: 'POST', body: JSON.stringify(data) }),
  getAvailability: (params: string) => fetchJSON(`/schedule/availability?${params}`),
  // Certification
  getCertifications: () => fetchJSON('/certification'),
  getExpiringCertifications: (days?: number) => fetchJSON(`/certification/expiring${days ? '?days=' + days : ''}`),
  createCertification: (data: any) => fetchJSON('/certification', { method: 'POST', body: JSON.stringify(data) }),
  // Pricelist
  getProductPricelist: () => fetchJSON('/pricelist/product-pricelist'),
  getTreatmentPricelist: () => fetchJSON('/pricelist/treatment-pricelist'),
  createProductPricelist: (data: any) => fetchJSON('/pricelist/product-pricelist', { method: 'POST', body: JSON.stringify(data) }),
  createTreatmentPricelist: (data: any) => fetchJSON('/pricelist/treatment-pricelist', { method: 'POST', body: JSON.stringify(data) }),
  // Cancel Reason
  getCancelReasons: () => fetchJSON('/cancel-reason/cancel-reason'),
  createCancelReason: (data: any) => fetchJSON('/cancel-reason/cancel-reason', { method: 'POST', body: JSON.stringify(data) }),
};

// Legacy API exports for backward compatibility
export const transactionApi = {
  get: (id: string) => fetchJSON(`/transaction/${id}`),
  list: (params?: string) => fetchJSON(`/pos/transactions${params ? '?' + params : ''}`),
  create: (data: any) => fetchJSON('/transaction', { method: 'POST', body: JSON.stringify(data) }),
  addItem: (id: string, data: any) => fetchJSON(`/transaction/${id}/add-item`, { method: 'POST', body: JSON.stringify(data) }),
  removeItem: (id: string, data: any) => fetchJSON(`/transaction/${id}/remove-item`, { method: 'POST', body: JSON.stringify(data) }),
  pay: (id: string, data: any) => fetchJSON(`/pos/transaction/${id}/payment`, { method: 'POST', body: JSON.stringify(data) }),
  updateCustomer: (id: string, data: { customer_name: string; customer_phone?: string }) => fetchJSON(`/pos/transaction/${id}/customer`, { method: 'PUT', body: JSON.stringify(data) }),
  applyVoucher: (id: string, code: string) => fetchJSON(`/pos/transaction/${id}/apply-voucher`, { method: 'POST', body: JSON.stringify({ code }) }),
  applyDiscount: (id: string, data: { discount_type: string; value: number; reason?: string }) => fetchJSON(`/pos/transaction/${id}/apply-discount`, { method: 'POST', body: JSON.stringify(data) }),
  submitCheckout: (id: string) => fetchJSON(`/transaction/${id}/submit-checkout`, { method: 'POST', body: JSON.stringify({}) }),
  selectPaymentMethod: (id: string, data: any) => fetchJSON(`/transaction/${id}/select-payment-method`, { method: 'POST', body: JSON.stringify({ payment_method: data.method?.toLowerCase() || data.payment_method }) }),
  confirmCash: (id: string, data: any) => fetchJSON(`/transaction/${id}/confirm-cash`, { method: 'POST', body: JSON.stringify({ amount_received: String(data.amountReceived || data.amount_received) }) }),
  requestStaffReplacement: (id: string) => fetchJSON(`/transaction/${id}/staff-replacement`, { method: 'POST' }),
};

export const receiptApi = {
  get: (id: string) => fetchJSON(`/receipt/${id}`),
  getHtml: (id: string) => `/api/receipt/${id}/html`,
};

export const paymentApi = {
  getMethods: () => fetchJSON('/master/payment-method'),
  getQrisStatus: (paymentIntentId: string) => fetchJSON(`/payments/qris/${paymentIntentId}/status`),
};

export const coaApi = {
  list: () => fetchJSON('/master/coa'),
  create: (data: any) => fetchJSON('/master/coa', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: any) => fetchJSON(`/master/coa/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string) => fetchJSON(`/master/coa/${id}`, { method: 'DELETE' }),
  getMappings: () => fetchJSON('/master/account-mapping'),
  createMapping: (data: any) => fetchJSON('/master/account-mapping', { method: 'POST', body: JSON.stringify(data) }),
  statusSummary: () => fetchJSON('/master/account-mapping/summary'),
  searchAccounts: (q?: string) => fetchJSON(`/master/coa${q ? '?q=' + q : ''}`),
  listMappings: (type?: string) => fetchJSON(`/master/account-mapping${type ? '?type=' + type : ''}`),
  deleteMapping: (id: string) => fetchJSON(`/master/account-mapping/${id}`, { method: 'DELETE' }),
  bulkValidate: (data: any) => fetchJSON('/master/account-mapping/bulk-validate', { method: 'POST', body: JSON.stringify(data) }),
  bulkApply: (data: any, options?: any) => fetchJSON('/master/account-mapping/bulk-apply', { method: 'POST', body: JSON.stringify({ rows: data, options }) }),
};

export const closingApi = {
  summary: (params: string) => fetchJSON(`/daily-closing/summary?${params}`),
  submit: (data: any) => fetchJSON('/daily-closing/submit', { method: 'POST', body: JSON.stringify(data) }),
  getReport: (id: string) => fetchJSON(`/daily-closing/report/${id}`),
  history: (params?: string) => fetchJSON(`/daily-closing/history${params ? '?' + params : ''}`),
  list: () => fetchJSON('/pos/daily-closings'),
  create: (data: any) => fetchJSON('/pos/daily-closing', { method: 'POST', body: JSON.stringify(data) }),
};

export const exceptionApi = {
  list: (params?: string) => fetchJSON(`/exceptions${params ? '?' + params : ''}`),
  get: (id: string) => fetchJSON(`/exceptions/${id}`),
  resolve: (id: string, data: any) => fetchJSON(`/exceptions/${id}/resolve`, { method: 'POST', body: JSON.stringify(data) }),
  escalate: (id: string, data: any) => fetchJSON(`/exceptions/${id}/escalate`, { method: 'POST', body: JSON.stringify(data) }),
};

export const docRegistryApi = {
  getModules: () => fetchJSON('/doc-registry/modules'),
  getStats: () => fetchJSON('/doc-registry/stats'),
  getSequences: (params?: string) => fetchJSON(`/doc-registry/sequences${params ? '?' + params : ''}`),
  getLinks: (docKey: string) => fetchJSON(`/doc-registry/links/${encodeURIComponent(docKey)}`),
  search: (q?: string, module?: string) => {
    const p = new URLSearchParams();
    if (q) p.set('q', q);
    if (module) p.set('module', module);
    return fetchJSON(`/doc-registry/search${p.toString() ? '?' + p.toString() : ''}`);
  },
  getIntegrationLog: (params?: string) => fetchJSON(`/doc-registry/integration-log${params ? '?' + params : ''}`),
  generateDocKey: (moduleCode: string, branchCode: string) =>
    fetchJSON('/doc-registry/generate', { method: 'POST', body: JSON.stringify({ module_code: moduleCode, branch_code: branchCode }) }),
  linkDocuments: (sourceDocKey: string, sourceModule: string, targetDocKey: string, targetModule: string, relationship?: string) =>
    fetchJSON('/doc-registry/link', { method: 'POST', body: JSON.stringify({ source_doc_key: sourceDocKey, source_module: sourceModule, target_doc_key: targetDocKey, target_module: targetModule, relationship: relationship || 'related' }) }),
};
