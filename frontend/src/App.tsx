import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import CheckoutPage from './pages/CheckoutPage';
import ExceptionPage from './pages/ExceptionPage';
import DashboardPage from './pages/DashboardPage';
import CoaMappingPage from './pages/CoaMappingPage';
import DailyClosingPage from './pages/DailyClosingPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/checkout" replace />} />
          <Route path="checkout" element={<CheckoutPage />} />
          <Route path="checkout/:transactionId" element={<CheckoutPage />} />
          <Route path="exceptions" element={<ExceptionPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="coa" element={<CoaMappingPage />} />
          <Route path="closing" element={<DailyClosingPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
