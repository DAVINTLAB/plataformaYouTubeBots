import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import { useDashboard } from "../../hooks/useDashboard";
import { GlobalTab } from "./GlobalTab";
import { UserTab } from "./UserTab";
import { VideoTab } from "./VideoTab";

type Tab = "global" | "video" | "user";

const TABS: { key: Tab; label: string; description: string }[] = [
  { key: "global", label: "Visão Geral", description: "Métricas globais de todos os vídeos" },
  { key: "video", label: "Por Vídeo", description: "Análise detalhada por vídeo" },
  { key: "user", label: "Meu Progresso", description: "Seu progresso como anotador" },
];

export function DashboardPage() {
  const [tab, setTab] = useState<Tab>("global");
  const {
    error,
    globalData,
    videoData,
    userData,
    botsData,
    collections,
    activeCriteria,
    setActiveCriteria,
    fetchGlobal,
    fetchVideo,
    fetchUser,
    fetchBots,
    fetchCollections,
  } = useDashboard();

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <PageHeader breadcrumbs={[{ label: "Início", to: "/" }, { label: "Dashboard" }]} />

      <main className="flex-1 px-8 py-9 max-w-6xl w-full mx-auto">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-gray-800 mb-0.5">Dashboard de Análise</h1>
          <p className="text-sm text-gray-500">{TABS.find((t) => t.key === tab)?.description}</p>
        </div>

        {error && <div className="alert alert-error mb-4">{error}</div>}

        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-gray-200">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                tab === t.key
                  ? "border-davint-400 text-davint-500"
                  : "border-transparent text-gray-400 hover:text-gray-600"
              }`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "global" && (
          <GlobalTab
            data={globalData}
            botsData={botsData}
            activeCriteria={activeCriteria}
            onCriteriaChange={setActiveCriteria}
            onFetchGlobal={fetchGlobal}
            onFetchBots={fetchBots}
          />
        )}
        {tab === "video" && (
          <VideoTab
            data={videoData}
            botsData={botsData}
            collections={collections}
            activeCriteria={activeCriteria}
            onCriteriaChange={setActiveCriteria}
            onFetchVideo={fetchVideo}
            onFetchCollections={fetchCollections}
            onFetchBots={fetchBots}
          />
        )}
        {tab === "user" && <UserTab data={userData} onFetchUser={fetchUser} />}
      </main>
    </div>
  );
}
