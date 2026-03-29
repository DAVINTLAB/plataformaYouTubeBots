export const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

const REFRESH_KEY = "refresh_token";
const TOKEN_KEY = "access_token";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function tryRefresh(): Promise<string | null> {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return null;

  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      localStorage.removeItem(REFRESH_KEY);
      sessionStorage.removeItem(TOKEN_KEY);
      return null;
    }
    const data = (await res.json()) as {
      access_token: string;
      refresh_token: string;
    };
    sessionStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(REFRESH_KEY, data.refresh_token);
    return data.access_token;
  } catch {
    return null;
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  // Se 401 e temos refresh token, tentar renovar
  if (res.status === 401 && token) {
    if (!refreshPromise) {
      refreshPromise = tryRefresh();
    }
    const newToken = await refreshPromise;
    refreshPromise = null;

    if (newToken) {
      // Retry com novo token
      const retryHeaders: Record<string, string> = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${newToken}`,
      };
      const retryRes = await fetch(`${API_URL}${path}`, {
        ...options,
        headers: retryHeaders,
      });
      if (!retryRes.ok) {
        const body = (await retryRes.json().catch(() => ({}))) as {
          detail?: string | Array<{ msg: string; loc: (string | number)[] }>;
        };
        const detail = Array.isArray(body.detail)
          ? body.detail.map((e) => e.msg).join("; ")
          : (body.detail ?? "Erro na requisição");
        throw new ApiError(detail, retryRes.status);
      }
      if (retryRes.status === 204) return undefined as T;
      // Notificar AuthContext do novo token
      window.dispatchEvent(new CustomEvent("token-refreshed", { detail: newToken }));
      return retryRes.json() as Promise<T>;
    }
  }

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as {
      detail?: string | Array<{ msg: string; loc: (string | number)[] }>;
    };
    const detail = Array.isArray(body.detail)
      ? body.detail.map((e) => e.msg).join("; ")
      : (body.detail ?? "Erro na requisição");
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
