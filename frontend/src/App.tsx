import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./contexts/AuthContext";
import { LoginPage } from "./pages/Auth/LoginPage";
import { AnnotatePage } from "./pages/Annotate/AnnotatePage";
import { CleanPage } from "./pages/Clean/CleanPage";
import { CollectPage } from "./pages/Collect/CollectPage";
import { HomePage } from "./pages/Home/HomePage";
import { UsersPage } from "./pages/Users/UsersPage";

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<ProtectedRoute requireAdmin />}>
            <Route path="/users" element={<UsersPage />} />
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/collect" element={<CollectPage />} />
            <Route path="/clean" element={<CleanPage />} />
            <Route path="/annotate" element={<AnnotatePage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
