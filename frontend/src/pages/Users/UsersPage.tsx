import { useState } from "react";
import { usersApi } from "../../api/users";
import { PageHeader } from "../../components/PageHeader";
import { StepsCard } from "../../components/StepsCard";
import { useAuthContext } from "../../contexts/AuthContext";
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
      <PageHeader
        breadcrumbs={[{ label: "Início", to: "/" }, { label: "Usuários" }]}
        onChangePassword={() => setShowChangePassword(true)}
      />

      {/* Conteúdo */}
      <main className="flex-1 px-8 py-9 max-w-6xl w-full mx-auto">
        <StepsCard
          title="Gestão de usuários"
          steps={[
            {
              label: "Crie contas para os anotadores",
              description:
                "Cada pesquisador recebe um usuário com nome, username e senha. O papel padrão é 'user' (anotador).",
            },
            {
              label: "Anotadores acessam a plataforma com suas credenciais",
              description:
                "Eles podem coletar comentários, anotar e visualizar dados compartilhados.",
            },
            {
              label: "Desative contas de quem saiu do laboratório",
              description:
                "Soft-delete preserva as anotações feitas. Contas podem ser reativadas a qualquer momento.",
            },
          ]}
        />
        <div className="flex items-start gap-2.5 p-4 bg-yellow-50 border border-yellow-200 rounded-xl mb-6">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 16 16"
            fill="currentColor"
            className="w-5 h-5 text-yellow-500 shrink-0 mt-0.5"
          >
            <path
              fillRule="evenodd"
              d="M6.701 2.25c.577-1 2.02-1 2.598 0l5.196 9a1.5 1.5 0 0 1-1.299 2.25H2.804a1.5 1.5 0 0 1-1.3-2.25l5.197-9ZM8 4a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
              clipRule="evenodd"
            />
          </svg>
          <div className="text-sm text-yellow-700">
            <p className="font-semibold">Cada anotador precisa de sua própria API key do YouTube</p>
            <p className="mt-1 text-xs">
              Antes de criar a conta, instrua o pesquisador a gerar uma chave em{" "}
              <a
                href="https://console.cloud.google.com/apis/credentials"
                target="_blank"
                rel="noopener noreferrer"
                className="underline font-medium"
              >
                Google Cloud Console
              </a>{" "}
              com a <strong>YouTube Data API v3</strong> habilitada. A chave é pessoal e
              intransferível — não deve ser compartilhada entre pesquisadores.
            </p>
          </div>
        </div>
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
                                onClick={() => {
                                  if (
                                    window.confirm(
                                      `Desativar "${u.name}" (@${u.username})?\n\nO usuário não poderá mais acessar a plataforma. As anotações feitas serão preservadas. Você pode reativar a conta a qualquer momento.`
                                    )
                                  ) {
                                    void handleDeactivate(u.id);
                                  }
                                }}
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
