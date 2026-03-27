import { FormEvent, useState } from "react";

interface Props {
  onClose: () => void;
  onSubmit: (currentPassword: string, newPassword: string) => Promise<void>;
}

export function ChangePasswordModal({ onClose, onSubmit }: Props) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("As senhas não coincidem.");
      return;
    }

    setLoading(true);
    try {
      await onSubmit(currentPassword, newPassword);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao alterar senha");
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
          <h2 className="text-[17px] font-bold text-gray-800 tracking-tight">Alterar Senha</h2>
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
              <label className="form-label" htmlFor="current-password">
                Senha atual
              </label>
              <input
                id="current-password"
                className="form-input"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                autoFocus
                placeholder="sua senha atual"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="new-password">
                Nova senha
              </label>
              <input
                id="new-password"
                className="form-input"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                placeholder="mínimo 8 caracteres"
              />
            </div>

            <div className="form-group mb-0">
              <label className="form-label" htmlFor="confirm-password">
                Confirmar nova senha
              </label>
              <input
                id="confirm-password"
                className="form-input"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
                placeholder="repita a nova senha"
              />
            </div>

            {error && <div className="alert alert-error mt-4">{error}</div>}
          </div>

          <div className="flex justify-end gap-2.5 px-6 py-5 border-t border-gray-200 mt-6">
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Salvando…" : "Alterar Senha"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
