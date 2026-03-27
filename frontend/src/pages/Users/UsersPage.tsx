import { useState } from "react";
import { useAuthContext } from "../../contexts/AuthContext";
import { useAuth } from "../Auth/useAuth";
import { CreateUserModal } from "./CreateUserModal";
import { useUsers } from "./useUsers";

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  user: "Anotador",
};

export function UsersPage() {
  const { user } = useAuthContext();
  const { logout } = useAuth();
  const { users, loading, error, createUser, deleteUser } = useUsers();
  const [showModal, setShowModal] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await deleteUser(id);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-8 h-[60px] bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <img src="/davint-logo.png" alt="DaVint Lab" className="h-7 w-auto" />
          <span className="inline-block w-px h-5 bg-gray-200" aria-hidden="true" />
          <span className="text-sm font-semibold text-gray-500">Plataforma YouTube Bots</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-2 text-sm text-gray-500">
            <span className="badge badge-admin">{user ? (ROLE_LABEL[user.role] ?? user.role) : ""}</span>
            {user?.username}
          </span>
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
            <div className="py-12 px-7 text-center text-gray-500 text-sm">
              Carregando usuários…
            </div>
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
                  {users.map((u) => (
                    <tr
                      key={u.id}
                      className="border-b border-gray-200 last:border-0 hover:bg-gray-50 transition-colors"
                    >
                      <td className="px-5 py-3.5 text-gray-800 align-middle">
                        <div className="flex items-center gap-2.5 font-medium">
                          <span className="w-[30px] h-[30px] rounded-full bg-davint-400 text-white text-[13px] font-bold inline-flex items-center justify-center flex-shrink-0">
                            {u.username[0].toUpperCase()}
                          </span>
                          {u.username}
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-gray-800 align-middle">
                        <span className={`badge ${u.role === "admin" ? "badge-admin" : "badge-user"}`}>
                          {ROLE_LABEL[u.role] ?? u.role}
                        </span>
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
                          <button
                            className="btn btn-danger"
                            disabled={deletingId === u.id}
                            onClick={() => void handleDelete(u.id)}
                          >
                            {deletingId === u.id ? "Removendo…" : "Remover"}
                          </button>
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

      {showModal && (
        <CreateUserModal onClose={() => setShowModal(false)} onCreate={createUser} />
      )}
    </div>
  );
}
