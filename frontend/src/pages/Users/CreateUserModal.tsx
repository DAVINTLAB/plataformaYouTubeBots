import { FormEvent, useState } from "react";
import { UserCreate } from "../../api/users";

interface Props {
  onClose: () => void;
  onCreate: (data: UserCreate) => Promise<void>;
}

export function CreateUserModal({ onClose, onCreate }: Props) {
  const [username, setUsername] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await onCreate({ username, name, password });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar usuário");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-[rgba(15,12,40,0.45)] backdrop-blur-sm flex items-center justify-center p-6 z-[100] animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-[440px] animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 pt-5">
          <h2 className="text-[17px] font-bold text-gray-800 tracking-tight">Criar Anotador</h2>
          <button
            className="bg-transparent border-0 cursor-pointer text-gray-500 text-base px-2 py-1 rounded-md hover:bg-gray-100 transition-colors"
            onClick={onClose}
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="px-6 pt-6">
            <div className="form-group">
              <label className="form-label" htmlFor="new-name">
                Nome
              </label>
              <input
                id="new-name"
                className="form-input"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={128}
                autoFocus
                placeholder="Nome completo do pesquisador"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="new-username">
                Usuário
              </label>
              <input
                id="new-username"
                className="form-input"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={3}
                maxLength={64}
                placeholder="apenas minúsculas, dígitos, ponto ou _"
              />
            </div>

            <div className="form-group mb-0">
              <label className="form-label" htmlFor="new-password">
                Senha
              </label>
              <input
                id="new-password"
                className="form-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                placeholder="mínimo 8 caracteres"
              />
            </div>

            {error && <div className="alert alert-error mt-4">{error}</div>}

            <div className="flex items-start gap-2.5 p-3 bg-yellow-50 border border-yellow-200 rounded-lg mt-4">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 16 16"
                fill="currentColor"
                className="w-4 h-4 text-yellow-500 shrink-0 mt-0.5"
              >
                <path
                  fillRule="evenodd"
                  d="M6.701 2.25c.577-1 2.02-1 2.598 0l5.196 9a1.5 1.5 0 0 1-1.299 2.25H2.804a1.5 1.5 0 0 1-1.3-2.25l5.197-9ZM8 4a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
                  clipRule="evenodd"
                />
              </svg>
              <div className="text-xs text-yellow-700">
                <p className="font-semibold mb-1">
                  Cada anotador precisa de sua própria API key do YouTube
                </p>
                <p>
                  Instrua o pesquisador a criar uma chave em{" "}
                  <a
                    href="https://console.cloud.google.com/apis/credentials"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline font-medium"
                  >
                    Google Cloud Console
                  </a>{" "}
                  com a YouTube Data API v3 habilitada. A chave é pessoal e intransferível — não
                  deve ser compartilhada entre pesquisadores.
                </p>
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2.5 px-6 py-5 border-t border-gray-200 mt-6">
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Criando…" : "Criar Anotador"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
