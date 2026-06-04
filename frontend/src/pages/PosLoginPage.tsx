import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function PosLoginPage() {
  const navigate = useNavigate();
  const [staffId, setStaffId] = useState('');
  const [pin, setPin] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch('/api/pos/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ staff_id: staffId, pin }),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        setError(data.message || 'Login gagal');
        setLoading(false);
        return;
      }

      // Store token and staff info
      localStorage.setItem('pos_token', data.access_token);
      localStorage.setItem('pos_staff', JSON.stringify(data.staff));
      if (data.staff?.branch_id) {
        localStorage.setItem('pos_branch_id', data.staff.branch_id);
      }

      // Always redirect to open-shift page — it handles existing shifts too
      navigate('/open-shift');
    } catch {
      setError('Gagal terhubung ke server');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--ivory)] flex flex-col items-center justify-center px-4">
      {/* Logo / Brand */}
      <div className="mb-8 text-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--gold)] to-[var(--rose)] flex items-center justify-center text-white font-bold text-2xl shadow-lg mx-auto mb-3">
          B
        </div>
        <h1 className="text-xl font-bold text-[var(--charcoal)]">Beauty & Shine</h1>
        <p className="text-sm text-gray-400 mt-1">Point of Sale</p>
      </div>

      {/* Login Form */}
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
        {error && (
          <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-xl text-center">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Staff ID</label>
          <input
            type="text"
            value={staffId}
            onChange={(e) => setStaffId(e.target.value.toUpperCase())}
            placeholder="KSR001"
            autoComplete="off"
            required
            className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent text-center text-lg font-mono"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">PIN</label>
          <input
            type="password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            placeholder="••••"
            autoComplete="off"
            required
            inputMode="numeric"
            maxLength={6}
            className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-[var(--charcoal)] placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[var(--gold)] focus:border-transparent text-center text-2xl font-mono tracking-widest"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !staffId || !pin}
          className="w-full py-3.5 rounded-xl bg-[var(--gold)] text-white font-semibold text-base active:bg-[var(--gold)]/90 disabled:opacity-50 disabled:active:bg-[var(--gold)] transition-colors shadow-sm"
        >
          {loading ? (
            <span className="inline-flex items-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Masuk...
            </span>
          ) : 'Masuk'}
        </button>
      </form>

      {/* Footer hint */}
      <p className="text-xs text-gray-300 mt-8">Masukkan Staff ID dan PIN untuk memulai shift</p>
    </div>
  );
}
