import { useNavigate } from "react-router-dom";

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
      <p className="text-6xl font-bold text-gray-200 mb-2">404</p>
      <h1 className="text-lg font-bold text-gray-700 mb-1">Página não encontrada</h1>
      <p className="text-sm text-gray-500 mb-6">
        O endereço que você tentou acessar não existe ou foi removido.
      </p>
      <button onClick={() => navigate("/")} className="btn btn-primary">
        Voltar ao início
      </button>
    </div>
  );
}
