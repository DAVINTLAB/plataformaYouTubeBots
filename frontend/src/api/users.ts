import { request } from "./http";

export interface UserOut {
  id: string;
  username: string;
  role: string;
  created_at: string;
}

export interface UserCreate {
  username: string;
  password: string;
}

export const usersApi = {
  list: (token: string) => request<UserOut[]>("/users/", {}, token),

  create: (data: UserCreate, token: string) =>
    request<UserOut>("/users/", { method: "POST", body: JSON.stringify(data) }, token),

  delete: (userId: string, token: string) =>
    request<void>(`/users/${userId}`, { method: "DELETE" }, token),
};
