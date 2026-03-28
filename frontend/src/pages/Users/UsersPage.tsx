import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usersApi } from "../../api/users";
import { useAuthContext } from "../../contexts/AuthContext";
import { useAuth } from "../Auth/useAuth";
import { ChangePasswordModal } from "../Home/ChangePasswordModal";
import { CreateUserModal } from "./CreateUserModal";
import { ResetPasswordModal } from "./ResetPasswordModal";
import { useUsers } from "./useUsers";

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  user: "Anotador",
};

export function UsersPage() {
  const { user, token } = useAuthContext();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const { users, loading, error, createUser, deactivateUser, reactivateUser } = useUsers();
  const [showModal, setShowModal] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [deactivatingId, setDeactivatingId] = useState<string | null>(null);
  const [reactivatingId, setReactivatingId] = useState<string | null>(null);
  const [resetTarget, setResetTarget] = useState<{ id: string; username: string } | null>(null);

  async function handleDeactivate(id: string) {
    setDeactivatingId(id);
    try {
      await deactivateUser(id);
    } finally {
      setDeactivatingId(null);
    }
  }

  async function handleReactivate(id: string) {
    setReactivatingId(id);
    try {
      await reactivateUser(id);
    } finally {
      setReactivatingId(null);
    }
  }

  const sortedUsers = [...users].sort((a, b) => Number(b.is_active) - Number(a.is_active));

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-8 h-[60px] bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/")}
            className="bg-transparent border-0 p-0 cursor-pointer flex-shrink-0"
            aria-label="Voltar ao início"
          >
            <img src="/davint-logo.png" alt="DaVint Lab" className="h-7 w-auto" />
          </button>
          <span className="inline-block w-px h-5 bg-gray-200" aria-hidden="true" />
          <nav className="flex items-center gap-1.5 text-sm">
            <button
              onClick={() => navigate("/")}
              className="font-semibold text-gray-500 hover:text-davint-400 transition-colors bg-transparent border-0 cursor-pointer p-0"
            >
              Início
            </button>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2.5}
              stroke="currentColor"
              className="w-3 h-3 text-gray-300 flex-shrink-0"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
            <span className="font-semibold text-gray-800">Usuários</span>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-2 text-sm text-gray-500">
            <span className="badge badge-admin">
              {user ? (ROLE_LABEL[user.role] ?? user.role) : ""}
            </span>
            {user?.username}
          </span>
          <button className="btn btn-ghost" onClick={() => setShowChangePassword(true)}>
            Alterar senha
          </button>
          <button className="btn btn-ghost" onClick={() => void logout()}>
            Sair
          </button>
        </div>
      </header>

      {/* Conteúdo */}
      <main className="flex-1 px-8 py-9 max-w-4xl w-full mx-auto">
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          <div className="flex items-center justify-between px-7 py-6 border-b border-gray-200">
            <div>
              <h1 className="text-lg font-bold text-gray-800 tracking-tight mb-1">Usuários</h1>
              <p className="text-sm text-gray-500">Gerencie as contas de acesso à plataforma.</p>
            </div>
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>
              + Criar Anotador
            </button>
          </div>

          {error && <div className="alert alert-error mx-7 mt-4">{error}</div>}

          {loading ? (
            <div className="py-12 px-7 text-center text-gray-500 text-sm">Carregando usuários…</div>
          ) : users.length === 0 ? (
            <div className="py-12 px-7 text-center text-gray-500 text-sm">
              Nenhum usuário encontrado.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-500 border-b border-gray-200">
                      Usuário
                    </th>
                    <th className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-500 border-b border-gray-200">
                      Papel
                    </th>
                    <th className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-500 border-b border-gray-200">
                      Criado em
                    </th>
                    <th className="px-5 py-3 border-b border-gray-200" />
                  </tr>
                </thead>
                <tbody>
                  {sortedUsers.map((u) => (
                    <tr
                      key={u.id}
                      className={[
                        "border-b border-gray-200 last:border-0 transition-colors",
                        u.is_active ? "hover:bg-gray-50" : "bg-gray-50/60",
                      ].join(" ")}
                    >
                      <td className="px-5 py-3.5 align-middle">
                        <div className="flex items-center gap-2.5">
                          <span
                            className={`w-[30px] h-[30px] rounded-full text-white text-[13px] font-bold inline-flex items-center justify-center flex-shrink-0 ${u.is_active ? "bg-davint-400" : "bg-gray-300"}`}
                          >
                            {u.name[0].toUpperCase()}
                          </span>
                          <div>
                            <div
                              className={`font-medium ${u.is_active ? "text-gray-800" : "text-gray-400"}`}
                            >
                              {u.name}
                            </div>
                            <div className="text-xs text-gray-400">@{u.username}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 align-middle">
                        {u.is_active ? (
                          <span
                            className={`badge ${u.role === "admin" ? "badge-admin" : "badge-user"}`}
                          >
                            {ROLE_LABEL[u.role] ?? u.role}
                          </span>
                        ) : (
                          <span className="badge bg-gray-100 text-gray-400">Inativo</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-gray-500 text-sm align-middle">
                        {new Date(u.created_at).toLocaleDateString("pt-BR", {
                          day: "2-digit",
                          month: "short",
                          year: "numeric",
                        })}
                      </td>
                      <td className="px-5 py-3.5 text-right align-middle">
                        {u.username !== user?.username && (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              className="btn btn-ghost"
                              onClick={() => setResetTarget({ id: u.id, username: u.username })}
                            >
                              Redefinir senha
                            </button>
                            {u.is_active ? (
                              <button
                                className="btn btn-danger"
                                disabled={deactivatingId === u.id}
                                onClick={() => void handleDeactivate(u.id)}
                              >
                                {deactivatingId === u.id ? "Desativando…" : "Desativar"}
                              </button>
                            ) : (
                              <button
                                className="btn btn-primary"
                                disabled={reactivatingId === u.id}
                                onClick={() => void handleReactivate(u.id)}
                              >
                                {reactivatingId === u.id ? "Reativando…" : "Reativar"}
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {showModal && <CreateUserModal onClose={() => setShowModal(false)} onCreate={createUser} />}

      {showChangePassword && (
        <ChangePasswordModal
          onClose={() => setShowChangePassword(false)}
          onSubmit={(currentPassword, newPassword) =>
            usersApi.changePassword(
              { current_password: currentPassword, new_password: newPassword },
              token!
            )
          }
        />
      )}

      {resetTarget && (
        <ResetPasswordModal
          username={resetTarget.username}
          onClose={() => setResetTarget(null)}
          onSubmit={(newPassword) =>
            usersApi.resetPassword(resetTarget.id, { new_password: newPassword }, token!)
          }
        />
      )}
    </div>
  );
}
