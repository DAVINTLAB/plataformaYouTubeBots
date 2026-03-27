import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../../api/http";
import { UserCreate, UserOut, usersApi } from "../../api/users";
import { useAuthContext } from "../../contexts/AuthContext";

export function useUsers() {
  const { token, logout } = useAuthContext();
  const navigate = useNavigate();
  const [users, setUsers] = useState<UserOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUnauthorized = useCallback(() => {
    logout();
    navigate("/login");
  }, [logout, navigate]);

  const fetchUsers = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      setUsers(await usersApi.list(token));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Erro ao carregar usuários");
    } finally {
      setLoading(false);
    }
  }, [token, handleUnauthorized]);

  useEffect(() => {
    void fetchUsers();
  }, [fetchUsers]);

  const createUser = useCallback(
    async (data: UserCreate) => {
      if (!token) return;
      await usersApi.create(data, token);
      await fetchUsers();
    },
    [token, fetchUsers]
  );

  const deactivateUser = useCallback(
    async (userId: string) => {
      if (!token) return;
      await usersApi.delete(userId, token);
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, is_active: false } : u)));
    },
    [token]
  );

  const reactivateUser = useCallback(
    async (userId: string) => {
      if (!token) return;
      const updated = await usersApi.reactivate(userId, token);
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)));
    },
    [token]
  );

  return { users, loading, error, createUser, deactivateUser, reactivateUser, refetch: fetchUsers };
}
