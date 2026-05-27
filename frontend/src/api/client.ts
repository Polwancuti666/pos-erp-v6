// ═══════════════════════════════════════════════════════════
// POS-ERP V6 — API Client
// ═══════════════════════════════════════════════════════════

const BASE_URL = '/api';

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: 'Network error' }));
    throw new Error(error.message || `HTTP ${res.status}`);
  }

  return res.json();
}

// ── Transaction API ──────────────────────────────────────────
export const transactionApi = {
  get: (id: string) => request<any>(`/transaction/${id}`),
  create: (data: any) => request<any>('/transaction', { method: 'POST', body: JSON.stringify(data) }),
  addItem: (id: string, data: any) => request<any>(`/transaction/${id}/add-item`, { method: 'POST', body: JSON.stringify(data) }),
  removeItem: (id: string, data: any) => request<any>(`/transaction/${id}/remove-item`, { method: 'POST', body: JSON.stringify(data) }),
  selectStaff: (id: string, data: any) => request<any>(`/transaction/${id}/select-staff`, { method: 'POST', body: JSON.stringify(data) }),
  selectPaymentMethod: (id: string, data: any) => request<any>(`/transaction/${id}/select-payment-method`, { method: 'POST', body: JSON.stringify(data) }),
  submitCheckout: (id: string) => request<any>(`/transaction/${id}/submit-checkout`, { method: 'POST' }),
  confirmCash: (id: string, data: any) => request<any>(`/transaction/${id}/confirm-cash`, { method: 'POST', body: JSON.stringify(data) }),
  requestStaffReplacement: (id: string) => request<any>(`/transaction/${id}/request-staff-replacement`, { method: 'POST' }),
};

// ── Payment API ──────────────────────────────────────────────
export const paymentApi = {
  getQrisStatus: (paymentIntentId: string) => request<any>(`/payment/qris-status/${paymentIntentId}`),
};

// ── Exception API ────────────────────────────────────────────
export const exceptionApi = {
  list: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return request<any[]>(`/exceptions${qs}`);
  },
  get: (id: string) => request<any>(`/exceptions/${id}`),
  resolve: (id: string, data: any) => request<any>(`/exceptions/${id}/resolve`, { method: 'POST', body: JSON.stringify(data) }),
  escalate: (id: string, data: any) => request<any>(`/exceptions/${id}/escalate`, { method: 'POST', body: JSON.stringify(data) }),
};

// ── Dashboard API ────────────────────────────────────────────
export const dashboardApi = {
  summary: (date?: string, branchCode?: string) => {
    const params = new URLSearchParams();
    if (date) params.set('date', date);
    if (branchCode) params.set('branchCode', branchCode);
    return request<any>(`/dashboard/summary?${params.toString()}`);
  },
  alerts: () => request<any[]>('/dashboard/alerts'),
};

// ── COA Mapping API ──────────────────────────────────────────
export const coaApi = {
  listMappings: (type?: string) => {
    const qs = type ? `?type=${type}` : '';
    return request<any[]>(`/coa/mappings${qs}`);
  },
  createMapping: (data: any) => request<any>('/coa/mappings', { method: 'POST', body: JSON.stringify(data) }),
  updateMapping: (id: string, data: any) => request<any>(`/coa/mappings/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteMapping: (id: string) => request<any>(`/coa/mappings/${id}`, { method: 'DELETE' }),
  bulkValidate: (rows: any[]) => request<any>('/coa/mappings/bulk-validate', { method: 'POST', body: JSON.stringify({ rows }) }),
  bulkApply: (rows: any[], overrideConflicts: string[]) => request<any>('/coa/mappings/bulk-apply', { method: 'POST', body: JSON.stringify({ rows, overrideConflicts }) }),
  searchAccounts: (search?: string) => {
    const qs = search ? `?search=${search}` : '';
    return request<any[]>(`/coa/accounts${qs}`);
  },
  statusSummary: () => request<any>('/coa/mappings/status-summary'),
};

// ── Daily Closing API ────────────────────────────────────────
export const closingApi = {
  summary: (date: string, branchCode: string) => request<any>(`/daily-closing/summary?date=${date}&branchCode=${branchCode}`),
  submit: (data: any) => request<any>('/daily-closing/submit', { method: 'POST', body: JSON.stringify(data) }),
  report: (id: string) => request<any>(`/daily-closing/report/${id}`),
};

// ── Auth API ─────────────────────────────────────────────────
export const authApi = {
  login: (username: string, password: string) => fetch('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) }).then(r => r.json()),
  posAuth: (staffId: string, pin: string) => fetch('/pos/auth', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ staff_id: staffId, pin }) }).then(r => r.json()),
  endShift: (shiftId: string) => fetch('/pos/end-shift', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ shift_id: shiftId }) }).then(r => r.json()),
};
