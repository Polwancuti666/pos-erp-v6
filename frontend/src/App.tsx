import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import MasterDataPage from './pages/MasterDataPage';
import MasterModulePage from './pages/MasterModulePage';
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
          <Route path="master/treatment" element={<MasterModulePage module="treatment" />} />
          <Route path="master/product" element={<MasterModulePage module="product" />} />
          <Route path="master/branch" element={<MasterModulePage module="branch" />} />
          <Route path="master/user" element={<MasterModulePage module="user" />} />
          <Route path="master/customer" element={<MasterModulePage module="customer" />} />
          <Route path="master/coa" element={<MasterModulePage module="coa" />} />
          <Route path="master/voucher" element={<MasterModulePage module="voucher" />} />
          <Route path="master/promo" element={<MasterModulePage module="promo" />} />
          <Route path="master/treatment-category" element={<MasterModulePage module="treatment-category" />} />
          <Route path="master/treatment-subcategory" element={<MasterModulePage module="treatment-subcategory" />} />
          <Route path="master/product-category" element={<MasterModulePage module="product-category" />} />
          <Route path="master/product-subcategory" element={<MasterModulePage module="product-subcategory" />} />
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
