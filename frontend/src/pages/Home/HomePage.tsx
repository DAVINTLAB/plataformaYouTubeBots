import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { request } from "../../api/http";
import { usersApi } from "../../api/users";
import { PageHeader } from "../../components/PageHeader";
import { useAuthContext } from "../../contexts/AuthContext";
import { ChangePasswordModal } from "./ChangePasswordModal";

interface StageCard {
  step: number;
  title: string;
  description: string;
  route: string;
  adminOnly: boolean;
  available: boolean;
  icon: ReactNode;
}

function IconCloudArrowDown() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="w-6 h-6"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z"
      />
    </svg>
  );
}

function IconFunnel() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="w-6 h-6"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z"
      />
    </svg>
  );
}

function IconTag() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="w-6 h-6"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.568 3H5.25A2.25 2.25 0 003 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 005.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 009.568 3z"
      />
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 6h.008v.008H6V6z" />
    </svg>
  );
}

function IconCheckCircle() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="w-6 h-6"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function IconChartBar() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="w-6 h-6"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
      />
    </svg>
  );
}

function IconDatabase() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="w-6 h-6"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75"
      />
    </svg>
  );
}

function IconUsers() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="w-6 h-6"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
      />
    </svg>
  );
}

const PIPELINE_STAGES: StageCard[] = [
  {
    step: 1,
    title: "Coletar Comentários",
    description:
      "Informe o ID ou URL de um vídeo do YouTube para extrair todos os comentários via YouTube Data API.",
    route: "/collect",
    adminOnly: false,
    available: true,
    icon: <IconCloudArrowDown />,
  },
  {
    step: 2,
    title: "Limpar Dataset",
    description:
      "Aplique critérios estatísticos e comportamentais para filtrar usuários suspeitos de bot.",
    route: "/clean",
    adminOnly: false,
    available: true,
    icon: <IconFunnel />,
  },
  {
    step: 3,
    title: "Anotar Comentários",
    description:
      "Classifique comentários individualmente como bot ou humano. Progresso salvo automaticamente.",
    route: "/annotate",
    adminOnly: false,
    available: true,
    icon: <IconTag />,
  },
  {
    step: 4,
    title: "Revisar Conflitos",
    description:
      "Resolva classificações divergentes entre anotadores. Toda divergência exige decisão explícita.",
    route: "/review",
    adminOnly: true,
    available: true,
    icon: <IconCheckCircle />,
  },
];

const TOOLS_CARDS: StageCard[] = [
  {
    step: 0,
    title: "Catálogo de Dados",
    description: "Visualize e gerencie todas as coletas, datasets e anotações da plataforma.",
    route: "/data",
    adminOnly: false,
    available: true,
    icon: <IconDatabase />,
  },
  {
    step: 0,
    title: "Dashboard",
    description:
      "Visualize métricas globais e individuais sobre as anotações com gráficos interativos.",
    route: "/dashboard",
    adminOnly: false,
    available: false,
    icon: <IconChartBar />,
  },
];

const ADMIN_CARDS: StageCard[] = [
  {
    step: 0,
    title: "Gerenciar Usuários",
    description: "Crie e remova contas de anotadores da plataforma.",
    route: "/users",
    adminOnly: true,
    available: true,
    icon: <IconUsers />,
  },
];

interface CardProps {
  stage: StageCard;
  restricted?: boolean;
  badge?: number;
  sectionLabel?: string;
  onClick: () => void;
}

function Card({
  stage,
  restricted = false,
  badge,
  sectionLabel,
  compact = false,
  onClick,
}: CardProps & { compact?: boolean }) {
  const clickable = stage.available && !restricted;
  return (
    <div
      onClick={clickable ? onClick : undefined}
      className={[
        "bg-white rounded-xl border flex flex-col transition-all duration-150 w-full",
        compact ? "p-4 gap-2.5" : "p-5 gap-3",
        clickable
          ? "border-gray-200 cursor-pointer hover:border-davint-400 hover:shadow-md"
          : "border-gray-200 opacity-60 cursor-default",
      ].join(" ")}
    >
      <div className="flex items-start justify-between">
        <span
          className={[
            "inline-flex rounded-lg",
            compact ? "p-1.5" : "p-2",
            clickable ? "bg-davint-400/10 text-davint-400" : "bg-gray-100 text-gray-400",
          ].join(" ")}
        >
          {stage.icon}
        </span>
        <span
          className={[
            "text-[10px] font-semibold px-2 py-0.5 rounded-full",
            restricted
              ? "bg-orange-50 text-orange-600"
              : stage.available
                ? "bg-green-50 text-green-600"
                : "bg-gray-100 text-gray-400",
          ].join(" ")}
        >
          {restricted ? "Restrito a admins" : stage.available ? "Disponível" : "Em breve"}
        </span>
      </div>

      <div className="flex-1">
        {sectionLabel && (
          <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-0.5">
            {sectionLabel}
          </p>
        )}
        <h3
          className={`font-bold text-gray-800 ${compact ? "text-[13px] mb-1" : "text-[14px] mb-1"}`}
        >
          {stage.title}
          {badge !== undefined && badge > 0 && (
            <span className="ml-2 inline-flex items-center justify-center px-2 py-0.5 text-[10px] font-bold rounded-full bg-yellow-100 text-yellow-700">
              Pendentes
            </span>
          )}
        </h3>
        <p className={`text-gray-500 leading-snug ${compact ? "text-xs" : "text-[13px]"}`}>
          {stage.description}
        </p>
      </div>

      {clickable && (
        <div className="flex items-center gap-1 text-xs font-semibold text-davint-400 mt-auto">
          Acessar
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            className="w-3.5 h-3.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
            />
          </svg>
        </div>
      )}
    </div>
  );
}

export function HomePage() {
  const { user, isAdmin, token } = useAuthContext();
  const navigate = useNavigate();
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showInfo, setShowInfo] = useState(
    () => localStorage.getItem("davint_home_info") !== "closed"
  );
  const [seedLoading, setSeedLoading] = useState(false);
  const [seedResult, setSeedResult] = useState<string | null>(null);
  const [seedError, setSeedError] = useState<string | null>(null);
  const [pendingConflicts, setPendingConflicts] = useState(0);

  useEffect(() => {
    if (!isAdmin || !token) return;
    import("../../api/review").then(({ reviewApi }) =>
      reviewApi
        .stats(token)
        .then((s) => setPendingConflicts(s.pending_conflicts))
        .catch(() => {})
    );
  }, [isAdmin, token]);

  const handleSeed = async () => {
    if (!token) return;
    setSeedLoading(true);
    setSeedResult(null);
    setSeedError(null);
    try {
      const data = await request<{ message: string; total_comments: number; total_bots: number }>(
        "/seed",
        { method: "POST" },
        token
      );
      setSeedResult(
        `${data.message} (${data.total_comments} comentários, ${data.total_bots} bots)`
      );
    } catch (err) {
      setSeedError(err instanceof Error ? err.message : "Erro ao executar seed.");
    } finally {
      setSeedLoading(false);
    }
  };

  const handleDeleteSeed = async () => {
    if (!token || !window.confirm("Tem certeza que deseja deletar todos os dados mockados?"))
      return;
    setSeedLoading(true);
    setSeedResult(null);
    setSeedError(null);
    try {
      const data = await request<{ message: string }>("/seed", { method: "DELETE" }, token);
      setSeedResult(data.message);
    } catch (err) {
      setSeedError(err instanceof Error ? err.message : "Erro ao deletar seed.");
    } finally {
      setSeedLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <PageHeader onChangePassword={() => setShowChangePassword(true)} />

      {/* Main */}
      <main className="flex-1 px-8 py-9 max-w-6xl w-full mx-auto">
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <img src="/davint.png" alt="DaVint Lab" className="h-36 w-auto invert" />
        </div>

        {/* Welcome */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-800 tracking-tight mb-1">
            Olá, {user?.name ?? user?.username}
          </h1>
          <div className="flex items-center gap-2">
            <p className="text-sm text-gray-500">
              {showInfo
                ? "Consulte o guia abaixo para entender o fluxo da plataforma e escolha por onde começar."
                : "Escolha uma etapa do pipeline ou uma ferramenta para começar."}
            </p>
            {!showInfo && (
              <button
                className="flex-shrink-0 w-5 h-5 rounded-full bg-davint-400/10 text-davint-400 text-xs font-bold inline-flex items-center justify-center hover:bg-davint-400/20 transition-colors"
                onClick={() => {
                  setShowInfo(true);
                  localStorage.removeItem("davint_home_info");
                }}
                title="Mostrar guia da plataforma"
              >
                ?
              </button>
            )}
          </div>
        </div>

        {/* Info card */}
        {showInfo && (
          <div className="bg-davint-50 rounded-xl border border-davint-400/20 p-5 mb-8 relative">
            <button
              className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 transition-colors"
              onClick={() => {
                setShowInfo(false);
                localStorage.setItem("davint_home_info", "closed");
              }}
              aria-label="Fechar"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-4 h-4"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            <h2 className="text-sm font-bold text-gray-800 mb-3">
              Plataforma de Detecção de Bots no YouTube
            </h2>
            <p className="text-xs text-gray-500 mb-4 leading-relaxed">
              Sistema para coleta, limpeza, anotação e revisão de comentários do YouTube, voltado à
              pesquisa científica em detecção de bots.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div>
                <h3 className="font-semibold text-davint-400 mb-1.5">Pipeline de Análise</h3>
                <ol className="text-gray-500 space-y-0.5 list-decimal list-inside">
                  <li>Coletar comentários via YouTube API</li>
                  <li>Filtrar usuários suspeitos por critérios</li>
                  <li>Anotar cada comentário como bot ou humano</li>
                  <li>Revisar e resolver divergências entre anotadores</li>
                </ol>
              </div>
              <div>
                <h3 className="font-semibold text-davint-400 mb-1.5">Ferramentas</h3>
                <ul className="text-gray-500 space-y-0.5">
                  <li>
                    <span className="font-medium text-gray-600">Catálogo de Dados</span> — gerencie
                    coletas, datasets e anotações
                  </li>
                  <li>
                    <span className="font-medium text-gray-600">Dashboard</span> — métricas e
                    gráficos interativos da pesquisa
                  </li>
                </ul>
              </div>
              {isAdmin && (
                <div>
                  <h3 className="font-semibold text-davint-400 mb-1.5">Administração</h3>
                  <ul className="text-gray-500 space-y-0.5">
                    <li>
                      <span className="font-medium text-gray-600">Gerenciar Usuários</span> — criar
                      e desativar contas de pesquisadores
                    </li>
                    <li>
                      <span className="font-medium text-gray-600">Dados de teste</span> — popular
                      banco com dados mockados
                    </li>
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Pipeline de análise — 4 etapas em linha */}
        <section className="mb-8">
          <h2 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">
            Pipeline de análise
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {PIPELINE_STAGES.map((stage) => (
              <Card
                key={stage.route}
                stage={stage}
                sectionLabel={`Etapa ${stage.step}`}
                restricted={stage.adminOnly && !isAdmin}
                badge={stage.route === "/review" && isAdmin ? pendingConflicts : undefined}
                onClick={() => navigate(stage.route)}
              />
            ))}
          </div>
        </section>

        {/* Ferramentas + Administração — linha compacta */}
        <section className="mb-8">
          <h2 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">
            Ferramentas
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {TOOLS_CARDS.map((stage) => (
              <Card key={stage.route} stage={stage} compact onClick={() => navigate(stage.route)} />
            ))}
          </div>
        </section>

        {/* Administração — admin only */}
        {isAdmin && (
          <section className="mb-8">
            <h2 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">
              Administração
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {ADMIN_CARDS.map((stage) => (
                <Card
                  key={stage.route}
                  stage={stage}
                  compact
                  sectionLabel="Administração"
                  onClick={() => navigate(stage.route)}
                />
              ))}
            </div>
          </section>
        )}

        {/* Seed — admin only */}
        {isAdmin && (
          <section>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Dados de teste</h3>
              <p className="text-xs text-gray-500 mb-3">
                Popula o banco com uma coleta mockada (30 usuários, 18 bots) e um dataset pronto
                para anotação.
              </p>
              {seedResult && (
                <div className="flex items-start gap-2 p-3 bg-green-50 border border-green-200 rounded-lg mb-3">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <p className="text-xs text-green-700">{seedResult}</p>
                </div>
              )}
              {seedError && <div className="alert alert-error mb-3">{seedError}</div>}
              <div className="flex gap-2">
                <button
                  className="btn btn-ghost btn-sm"
                  disabled={seedLoading}
                  onClick={handleSeed}
                >
                  {seedLoading ? "Gerando..." : "Gerar dados mockados"}
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  disabled={seedLoading}
                  onClick={handleDeleteSeed}
                >
                  {seedLoading ? "Deletando..." : "Deletar dados mockados"}
                </button>
              </div>
            </div>
          </section>
        )}
      </main>

      <footer className="py-4 text-center">
        <p className="text-[11px] text-gray-400">
          Desenvolvido pelo{" "}
          <span className="font-semibold">
            DaVint Lab (Data Visualization and Interaction) — PUCRS
          </span>{" "}
          com financiamento do <span className="font-semibold">CNPq</span>. Desenvolvido com auxílio
          da ferramenta de IA <span className="font-semibold">Claude</span> (Anthropic).
        </p>
      </footer>

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
    </div>
  );
}
