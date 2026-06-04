import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import PosLayout from './components/PosLayout';
import CheckoutPage from './pages/CheckoutPage';
import PosLoginPage from './pages/PosLoginPage';
import PosOpenShiftPage from './pages/PosOpenShiftPage';
import PosCloseShiftPage from './pages/PosCloseShiftPage';
import PosHomePage from './pages/PosHomePage';
import PosBookingPage from './pages/PosBookingPage';
import PosDailyClosingPage from './pages/PosDailyClosingPage';
import PosVoucherPage from './pages/PosVoucherPage';
import PosTreatmentRecordPage from './pages/PosTreatmentRecordPage';
import PosTreatmentSelectorPage from './pages/PosTreatmentSelectorPage';
import PosReceiptPage from './pages/PosReceiptPage';

function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = localStorage.getItem('pos_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function ShiftGuard({ children }: { children: ReactNode }) {
  const token = localStorage.getItem('pos_token');
  const shiftId = localStorage.getItem('pos_shift_id');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  if (!shiftId) {
    return <Navigate to="/open-shift" replace />;
  }
  return <>{children}</>;
}

export default function PosApp() {
  return (
    <BrowserRouter basename="/pos">
      <Routes>
        <Route path="/login" element={<PosLoginPage />} />
        <Route path="/open-shift" element={
          <ProtectedRoute>
            <PosOpenShiftPage />
          </ProtectedRoute>
        } />
        <Route path="/close-shift" element={
          <ShiftGuard>
            <PosCloseShiftPage />
          </ShiftGuard>
        } />
        <Route
          path="/"
          element={
            <ShiftGuard>
              <PosLayout />
            </ShiftGuard>
          }
        >
          <Route index element={<PosHomePage />} />
          <Route path="kasir" element={<CheckoutPage />} />
          <Route path="kasir/:transactionId" element={<CheckoutPage />} />
          <Route path="kasir/:transactionId/select-treatment" element={<PosTreatmentSelectorPage />} />
          <Route path=":transactionId" element={<CheckoutPage />} />
          <Route path="booking" element={<PosBookingPage />} />
          <Route path="closing" element={<PosDailyClosingPage />} />
          <Route path="voucher" element={<PosVoucherPage />} />
          <Route path="treatment-record" element={<PosTreatmentRecordPage />} />
          <Route path="receipt" element={<PosReceiptPage />} />
          <Route path="receipt/:transactionId" element={<PosReceiptPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
