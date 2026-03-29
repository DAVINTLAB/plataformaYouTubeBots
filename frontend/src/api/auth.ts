import { request } from "./http";

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export const authApi = {
  login: (username: string, password: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  logout: (token: string) => request<{ detail: string }>("/auth/logout", { method: "POST" }, token),
};
