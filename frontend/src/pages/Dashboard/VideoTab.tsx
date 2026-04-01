import { useEffect, useState } from "react";
import type { DataCollection } from "../../api/data";
import type { BotCommentsResponse, VideoDashboardResponse } from "../../api/dashboard";
import { AbbreviatedChart } from "./AbbreviatedChart";
import { BotCommentsTable } from "./BotCommentsTable";
import { CriteriaFilterBar } from "./CriteriaFilterBar";
import { KpiCards } from "./KpiCards";
import { ChartCard, PlotlyChart } from "./PlotlyChart";

interface VideoTabProps {
  data: VideoDashboardResponse | null;
  botsData: BotCommentsResponse | null;
  collections: DataCollection[];
  activeCriteria: string[];
  onCriteriaChange: (criteria: string[]) => void;
  onFetchVideo: (videoId: string, criteria?: string[]) => void;
  onFetchCollections: () => void;
  onFetchBots: (params: {
    search?: string;
    video_id?: string;
    criteria?: string[];
    page?: number;
    page_size?: number;
  }) => void;
}

export function VideoTab({
  data,
  botsData,
  collections,
  activeCriteria,
  onCriteriaChange,
  onFetchVideo,
  onFetchCollections,
  onFetchBots,
}: VideoTabProps) {
  const [selectedVideoId, setSelectedVideoId] = useState("");

  useEffect(() => {
    onFetchCollections();
  }, [onFetchCollections]);

  const uniqueVideos = collections.reduce(
    (acc, col) => {
      if (!acc.find((v) => v.video_id === col.video_id)) {
        acc.push({ video_id: col.video_id, video_title: col.video_title });
      }
      return acc;
    },
    [] as { video_id: string; video_title: string | null }[]
  );

  const handleSelectVideo = (videoId: string) => {
    setSelectedVideoId(videoId);
    if (videoId) {
      onFetchVideo(videoId, activeCriteria.length > 0 ? activeCriteria : undefined);
    }
  };

  const handleCriteriaChange = (criteria: string[]) => {
    onCriteriaChange(criteria);
    if (selectedVideoId) {
      onFetchVideo(selectedVideoId, criteria.length > 0 ? criteria : undefined);
    }
  };

  return (
    <div>
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <label className="block text-xs font-semibold text-gray-600 mb-1.5">
          Selecione um vídeo
        </label>
        <select
          value={selectedVideoId}
          onChange={(e) => handleSelectVideo(e.target.value)}
          className="form-input text-sm w-full max-w-md"
        >
          <option value="">Escolha um vídeo...</option>
          {uniqueVideos.map((v) => (
            <option key={v.video_id} value={v.video_id}>
              {v.video_title || v.video_id}
            </option>
          ))}
        </select>
      </div>

      {!selectedVideoId && (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1}
            stroke="currentColor"
            className="w-12 h-12 mb-3 text-gray-300"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z"
            />
          </svg>
          <p className="text-sm">Selecione um vídeo acima para visualizar as métricas.</p>
        </div>
      )}

      {selectedVideoId && data && (
        <>
          <KpiCards
            cards={[
              { label: "Coletados", value: data.summary.total_comments_collected },
              { label: "No Dataset", value: data.summary.total_comments_in_datasets },
              { label: "Anotados", value: data.summary.total_annotated },
              { label: "Humanos", value: data.summary.total_humans, color: "green" },
              { label: "Bots", value: data.summary.total_bots, color: "red" },
              {
                label: "Concordância",
                value: `${(data.summary.agreement_rate * 100).toFixed(1)}%`,
                color: "blue",
              },
              { label: "Pendentes", value: data.summary.pending_conflicts, color: "orange" },
            ]}
          />

          {/* Destaques do vídeo */}
          {data.highlights.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
              {data.highlights.map((h) => (
                <div
                  key={h.label}
                  className="bg-white rounded-xl border border-gray-200 px-3 py-3 text-center"
                >
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">
                    {h.label}
                  </p>
                  <p className="text-sm font-bold text-gray-700 truncate" title={h.value}>
                    {h.value}
                  </p>
                  {h.detail && (
                    <p className="text-[10px] text-gray-400 mt-0.5 truncate" title={h.detail}>
                      {h.detail}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          <CriteriaFilterBar active={activeCriteria} onChange={handleCriteriaChange} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
            <ChartCard title="Distribuição deste Vídeo" subtitle="Humano / Bot / Conflito">
              <PlotlyChart figureJson={data.label_distribution_chart} height={300} />
            </ChartCard>
            <ChartCard title="Comparativo por Dataset" subtitle="Datasets gerados para este vídeo">
              <AbbreviatedChart figureJson={data.comparativo_por_dataset_chart} />
            </ChartCard>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            <ChartCard title="Taxa de Bots por Critério" subtitle="Critérios usados neste vídeo">
              <AbbreviatedChart figureJson={data.bot_rate_by_criteria_chart} prefix="C" />
            </ChartCard>
            <ChartCard title="Timeline de Comentários" subtitle="Comentários postados por dia">
              <PlotlyChart figureJson={data.comment_timeline_chart} />
            </ChartCard>
          </div>

          <BotCommentsTable data={botsData} videoId={selectedVideoId} onFetch={onFetchBots} />
        </>
      )}
    </div>
  );
}
