import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type { UserDashboardResponse } from "../../api/dashboard";
import { ProgressBar } from "../../components/ProgressBar";
import { AbbreviatedChart } from "./AbbreviatedChart";
import { KpiCards } from "./KpiCards";
import { ChartCard, PlotlyChart } from "./PlotlyChart";

interface UserTabProps {
  data: UserDashboardResponse | null;
  onFetchUser: () => void;
}

export function UserTab({ data, onFetchUser }: UserTabProps) {
  const navigate = useNavigate();

  useEffect(() => {
    onFetchUser();
  }, [onFetchUser]);

  if (!data) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-sm text-gray-400 animate-pulse">Carregando progresso...</div>
      </div>
    );
  }

  const s = data.summary;

  const statusBadge = (status: string) => {
    const map: Record<string, { label: string; cls: string }> = {
      completed: { label: "Concluído", cls: "bg-emerald-50 text-emerald-700" },
      in_progress: { label: "Em andamento", cls: "bg-blue-50 text-blue-700" },
      not_started: { label: "Não iniciado", cls: "bg-gray-100 text-gray-500" },
    };
    const { label, cls } = map[status] ?? map.not_started;
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${cls}`}
      >
        {label}
      </span>
    );
  };

  return (
    <div>
      <KpiCards
        cards={[
          { label: "Datasets", value: s.total_datasets_assigned },
          { label: "Concluídos", value: s.datasets_completed, color: "green" },
          { label: "Pendentes", value: s.datasets_pending, color: "orange" },
          { label: "Anotados", value: s.total_annotated },
          { label: "A fazer", value: s.total_pending, color: "yellow" },
          { label: "Humanos", value: s.humans, color: "green" },
          { label: "Bots", value: s.bots, color: "red" },
          { label: "Conflitos", value: s.conflicts_generated, color: "yellow" },
        ]}
      />

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <ChartCard title="Minha Distribuição" subtitle="Bot vs Humano nas minhas anotações">
          <PlotlyChart figureJson={data.my_label_distribution_chart} height={300} />
        </ChartCard>
        <ChartCard title="Progresso por Dataset" subtitle="Percentual concluído em cada dataset">
          <AbbreviatedChart figureJson={data.my_progress_by_dataset_chart} />
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <ChartCard
          title="Minhas Anotações ao Longo do Tempo"
          subtitle="Ritmo diário de anotações"
          full
        >
          <PlotlyChart figureJson={data.my_annotations_over_time_chart} height={280} />
        </ChartCard>
      </div>

      {/* Tabela de progresso por dataset */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h3 className="text-[13px] font-semibold text-gray-700">Detalhamento por Dataset</h3>
          <p className="text-[11px] text-gray-400 mt-0.5">
            Progresso individual em cada dataset atribuído
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="text-left px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  Dataset
                </th>
                <th className="text-left px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  Vídeo
                </th>
                <th className="text-center px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400 w-44">
                  Progresso
                </th>
                <th className="text-center px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  Bots
                </th>
                <th className="text-center px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  Conflitos
                </th>
                <th className="text-center px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  Status
                </th>
                <th className="text-center px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  Ação
                </th>
              </tr>
            </thead>
            <tbody>
              {data.datasets.map((ds) => (
                <tr key={ds.dataset_id} className="border-b border-gray-50 hover:bg-gray-50/50">
                  <td className="px-4 py-2.5 text-gray-700 font-medium max-w-[140px] truncate">
                    {ds.dataset_name}
                  </td>
                  <td className="px-4 py-2.5 text-gray-400 max-w-[100px] truncate font-mono text-[10px]">
                    {ds.video_id}
                  </td>
                  <td className="px-4 py-3 w-44">
                    <div className="flex items-center gap-2">
                      <div className="flex-1">
                        <ProgressBar percent={ds.percent_complete} size="sm" />
                      </div>
                      <span className="text-[10px] text-gray-400 whitespace-nowrap tabular-nums">
                        {ds.annotated_by_me}/{ds.total_comments}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-center text-gray-600 tabular-nums">
                    {ds.my_bots}
                  </td>
                  <td className="px-4 py-2.5 text-center text-gray-600 tabular-nums">
                    {ds.my_conflicts}
                  </td>
                  <td className="px-4 py-2.5 text-center">{statusBadge(ds.status)}</td>
                  <td className="px-4 py-2.5 text-center">
                    {ds.status !== "completed" && (
                      <button
                        onClick={() => navigate("/annotate")}
                        className="text-[10px] font-semibold text-davint-400 hover:underline"
                      >
                        Continuar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {data.datasets.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-gray-400">
                    Nenhum dataset disponível para anotação.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
