import { request } from "./http";

export interface UserOut {
  id: string;
  username: string;
  name: string;
  role: string;
  created_at: string;
  is_active: boolean;
}

export interface UserCreate {
  username: string;
  name: string;
  password: string;
}

export const usersApi = {
  list: (token: string) => request<UserOut[]>("/users/", {}, token),

  create: (data: UserCreate, token: string) =>
    request<UserOut>("/users/", { method: "POST", body: JSON.stringify(data) }, token),

  delete: (userId: string, token: string) =>
    request<void>(`/users/${userId}`, { method: "DELETE" }, token),

  reactivate: (userId: string, token: string) =>
    request<UserOut>(`/users/${userId}/reactivate`, { method: "POST" }, token),

  changePassword: (data: { current_password: string; new_password: string }, token: string) =>
    request<void>("/users/me/password", { method: "PATCH", body: JSON.stringify(data) }, token),

  resetPassword: (userId: string, data: { new_password: string }, token: string) =>
    request<void>(
      `/users/${userId}/password`,
      { method: "PATCH", body: JSON.stringify(data) },
      token
    ),
};
