import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "./auth";
import { OnboardingPage } from "./pages/OnboardingPage";
import { AuthPage } from "./pages/AuthPage";
import { ScannerPage } from "./pages/ScannerPage";
import { TableConfirmPage } from "./pages/TableConfirmPage";
import { MenuPage } from "./pages/MenuPage";
import { CartPage } from "./pages/CartPage";
import { BillPage } from "./pages/BillPage";
import { DashboardListPage } from "./pages/DashboardListPage";
import { RestaurantDashboardPage } from "./pages/RestaurantDashboardPage";

function RequireAuth({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="min-h-[100dvh] flex items-center justify-center text-on-surface-variant">
        <span className="material-symbols-outlined animate-spin">
          progress_activity
        </span>
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/auth" replace state={{ from: location }} />;
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<OnboardingPage />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route
        path="/scan"
        element={
          <RequireAuth>
            <ScannerPage />
          </RequireAuth>
        }
      />
      <Route
        path="/scan/:qrToken"
        element={
          <RequireAuth>
            <TableConfirmPage />
          </RequireAuth>
        }
      />
      <Route
        path="/sessions/:sessionId/menu"
        element={
          <RequireAuth>
            <MenuPage />
          </RequireAuth>
        }
      />
      <Route
        path="/sessions/:sessionId/cart"
        element={
          <RequireAuth>
            <CartPage />
          </RequireAuth>
        }
      />
      <Route
        path="/sessions/:sessionId/bill"
        element={
          <RequireAuth>
            <BillPage />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <DashboardListPage />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard/:restaurantId"
        element={
          <RequireAuth>
            <RestaurantDashboardPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
