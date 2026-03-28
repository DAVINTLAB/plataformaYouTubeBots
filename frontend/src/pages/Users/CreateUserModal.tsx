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
