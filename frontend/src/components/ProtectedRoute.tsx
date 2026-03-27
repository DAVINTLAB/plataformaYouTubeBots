import { Navigate, Outlet } from "react-router-dom";
import { useAuthContext } from "../contexts/AuthContext";

interface Props {
  requireAdmin?: boolean;
}

export function ProtectedRoute({ requireAdmin = false }: Props) {
  const { token, isAdmin } = useAuthContext();

  if (!token) return <Navigate to="/login" replace />;
  if (requireAdmin && !isAdmin) return <Navigate to="/" replace />;

  return <Outlet />;
}
