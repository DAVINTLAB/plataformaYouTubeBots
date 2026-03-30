import type { ReactNode } from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
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
    available: false,
    icon: <IconTag />,
  },
  {
    step: 4,
    title: "Revisar Conflitos",
    description:
      "Resolva classificações divergentes entre anotadores. Toda divergência exige decisão explícita.",
    route: "/review",
    adminOnly: true,
    available: false,
    icon: <IconCheckCircle />,
  },
  {
    step: 5,
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
  onClick: () => void;
}

function Card({ stage, restricted = false, onClick }: CardProps) {
  const clickable = stage.available && !restricted;
  return (
    <div
      onClick={clickable ? onClick : undefined}
      className={[
        "bg-white rounded-xl border p-6 flex flex-col gap-4 transition-all duration-150 w-full",
        clickable
          ? "border-gray-200 cursor-pointer hover:border-davint-400 hover:shadow-md"
          : "border-gray-200 opacity-60 cursor-default",
      ].join(" ")}
    >
      <div className="flex items-start justify-between">
        <span
          className={[
            "inline-flex p-2 rounded-lg",
            clickable ? "bg-davint-400/10 text-davint-400" : "bg-gray-100 text-gray-400",
          ].join(" ")}
        >
          {stage.icon}
        </span>
        <span
          className={[
            "text-[11px] font-semibold px-2.5 py-0.5 rounded-full",
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
        <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1">
          {stage.step > 0 ? `Etapa ${stage.step}` : "Administração"}
        </p>
        <h3 className="text-[15px] font-bold text-gray-800 mb-1.5">{stage.title}</h3>
        <p className="text-sm text-gray-500 leading-relaxed">{stage.description}</p>
      </div>

      {clickable && (
        <div className="flex items-center gap-1 text-sm font-semibold text-davint-400 mt-auto">
          Acessar
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            className="w-4 h-4"
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

  const pipelineStages = PIPELINE_STAGES;

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <PageHeader onChangePassword={() => setShowChangePassword(true)} />

      {/* Main */}
      <main className="flex-1 px-8 py-9 max-w-6xl w-full mx-auto">
        {/* Welcome */}
        <div className="mb-9">
          <h1 className="text-2xl font-bold text-gray-800 tracking-tight mb-1">
            Olá, {user?.name ?? user?.username}
          </h1>
          <p className="text-sm text-gray-500">
            Selecione uma etapa do pipeline de análise para começar.
          </p>
        </div>

        {/* Pipeline */}
        <section className="mb-10">
          <h2 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-4">
            Pipeline de análise
          </h2>
          <div className="flex flex-wrap justify-center gap-4">
            {pipelineStages.map((stage) => (
              <div
                key={stage.route}
                className="w-full sm:w-[calc(50%-0.5rem)] lg:w-[calc(33.333%-0.7rem)] flex"
              >
                <Card
                  stage={stage}
                  restricted={stage.adminOnly && !isAdmin}
                  onClick={() => navigate(stage.route)}
                />
              </div>
            ))}
          </div>
        </section>

        {/* Admin */}
        {isAdmin && (
          <section>
            <h2 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-4">
              Administração
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {ADMIN_CARDS.map((stage) => (
                <Card key={stage.route} stage={stage} onClick={() => navigate(stage.route)} />
              ))}
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
