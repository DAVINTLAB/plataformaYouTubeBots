import { Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { LoginPage } from "../pages/Auth/LoginPage";
import { AnnotatePage } from "../pages/Annotate/AnnotatePage";
import { CleanPage } from "../pages/Clean/CleanPage";
import { CollectPage } from "../pages/Collect/CollectPage";
import { DashboardPage } from "../pages/Dashboard/DashboardPage";
import { DataPage } from "../pages/Data/DataPage";
import { HomePage } from "../pages/Home/HomePage";
import { NotFoundPage } from "../pages/NotFound/NotFoundPage";
import { ReviewPage } from "../pages/Review/ReviewPage";
import { UsersPage } from "../pages/Users/UsersPage";

export function AppRoutes() {
  return (
    <Routes>
      {/* Pública */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protegidas — admin */}
      <Route element={<ProtectedRoute requireAdmin />}>
        <Route path="/users" element={<UsersPage />} />
        <Route path="/review" element={<ReviewPage />} />
      </Route>

      {/* Protegidas — qualquer usuário autenticado */}
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/collect" element={<CollectPage />} />
        <Route path="/clean" element={<CleanPage />} />
        <Route path="/annotate" element={<AnnotatePage />} />
        <Route path="/data" element={<DataPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Route>

      {/* 404 */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
