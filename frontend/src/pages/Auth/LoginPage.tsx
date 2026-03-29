import { FormEvent, useState } from "react";
import { useAuth } from "./useAuth";

export function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
    } catch {
      setError("Credenciais inválidas. Verifique seus dados e tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-davint-50 via-white to-davint-50 p-6">
      <div className="bg-white rounded-xl shadow-xl px-9 py-10 w-full max-w-[420px]">
        <div className="flex flex-col items-center text-center mb-8 gap-2.5">
          <img src="/davint-logo.png" alt="DaVint Lab" className="h-12 w-auto mb-1" />
          <h1 className="text-xl font-bold text-gray-800 tracking-tight">
            Plataforma YouTube Bots
          </h1>
          <p className="text-sm text-gray-500">DaVint Lab · PUCRS</p>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label className="form-label" htmlFor="username">
              Usuário
            </label>
            <input
              id="username"
              className="form-input"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              autoFocus
              placeholder="Digite seu usuário"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">
              Senha
            </label>
            <input
              id="password"
              className="form-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              placeholder="Digite sua senha"
            />
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          <button type="submit" disabled={loading} className="btn btn-primary btn-full">
            {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>

        <p className="mt-5 text-xs text-gray-500 text-center">
          Acesso restrito — conta criada pelo administrador.
        </p>
      </div>

      <p className="mt-6 text-[11px] text-gray-400 text-center max-w-sm">
        Desenvolvido pelo{" "}
        <span className="font-semibold">
          DaVint Lab (Data Visualization and Interaction) — PUCRS
        </span>{" "}
        com financiamento do <span className="font-semibold">CNPq</span>. Desenvolvido com auxílio
        da ferramenta de IA <span className="font-semibold">Claude</span> (Anthropic).
      </p>
    </div>
  );
}
