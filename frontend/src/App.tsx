import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import MasterDataPage from './pages/MasterDataPage';
import InventoryPage from './pages/InventoryPage';
import FinancePage from './pages/FinancePage';
import ReportingPage from './pages/ReportingPage';
import PeriodPage from './pages/PeriodPage';
import ExceptionPage from './pages/ExceptionPage';
import CoaMappingPage from './pages/CoaMappingPage';
import DailyClosingPage from './pages/DailyClosingPage';
import OperationsPage from './pages/OperationsPage';
import CoaUploadPage from './pages/CoaUploadPage';
import CoaManagementPage from './pages/CoaManagementPage';


function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('erp_token');
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter basename="/app">
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="master" element={<MasterDataPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="finance" element={<FinancePage />} />
          <Route path="reporting" element={<ReportingPage />} />
          <Route path="period" element={<PeriodPage />} />
          <Route path="exceptions" element={<ExceptionPage />} />
          <Route path="coa" element={<CoaMappingPage />} />
          <Route path="closing" element={<DailyClosingPage />} />
          <Route path="operations" element={<OperationsPage />} />

          <Route path="coa-upload" element={<CoaUploadPage />} />
          <Route path="coa-management" element={<CoaManagementPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
