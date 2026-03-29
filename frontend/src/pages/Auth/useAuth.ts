import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../../api/auth";
import { useAuthContext } from "../../contexts/AuthContext";

export function useAuth() {
  const { token, user, isAdmin, login: setLogin, logout: setLogout } = useAuthContext();
  const navigate = useNavigate();

  const login = useCallback(
    async (username: string, password: string) => {
      const { access_token, refresh_token } = await authApi.login(username, password);
      setLogin(access_token, refresh_token);
      navigate("/");
    },
    [setLogin, navigate]
  );

  const logout = useCallback(async () => {
    if (token) {
      try {
        await authApi.logout(token);
      } catch {
        // ignora erros de logout no servidor — limpa o estado local de qualquer forma
      }
    }
    setLogout();
    navigate("/login");
  }, [token, setLogout, navigate]);

  return { token, user, isAdmin, login, logout };
}
