import { useEffect } from "react";
import type { BotCommentsResponse, GlobalDashboardResponse } from "../../api/dashboard";
import { AbbreviatedChart } from "./AbbreviatedChart";
import { BotCommentsTable } from "./BotCommentsTable";
import { CriteriaFilterBar } from "./CriteriaFilterBar";
import { KpiCards } from "./KpiCards";
import { ChartCard, PlotlyChart } from "./PlotlyChart";

interface GlobalTabProps {
  data: GlobalDashboardResponse | null;
  botsData: BotCommentsResponse | null;
  activeCriteria: string[];
  onCriteriaChange: (criteria: string[]) => void;
  onFetchGlobal: (criteria?: string[]) => void;
  onFetchBots: (params: { search?: string; page?: number; page_size?: number }) => void;
}

export function GlobalTab({
  data,
  botsData,
  activeCriteria,
  onCriteriaChange,
  onFetchGlobal,
  onFetchBots,
}: GlobalTabProps) {
  useEffect(() => {
    onFetchGlobal();
  }, [onFetchGlobal]);

  const handleCriteriaChange = (criteria: string[]) => {
    onCriteriaChange(criteria);
    onFetchGlobal(criteria.length > 0 ? criteria : undefined);
  };

  if (!data) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-sm text-gray-400 animate-pulse">Carregando dashboard...</div>
      </div>
    );
  }

  const s = data.summary;

  return (
    <div>
      <KpiCards
        cards={[
          { label: "Datasets", value: s.total_datasets },
          {
            label: "Progresso",
            value: `${s.annotation_progress.toFixed(0)}%`,
            color: "blue",
          },
          { label: "Humanos", value: s.total_humans, color: "green" },
          { label: "Bots", value: s.total_bots, color: "red" },
          { label: "Conflitos", value: s.total_conflicts, color: "yellow" },
          {
            label: "Concordância",
            value: `${(s.agreement_rate * 100).toFixed(1)}%`,
            color: "blue",
          },
          { label: "Pendentes", value: s.pending_conflicts, color: "orange" },
        ]}
      />

      <CriteriaFilterBar active={activeCriteria} onChange={handleCriteriaChange} />

      {/* Linha 1: Distribuição + Comparativo */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <ChartCard title="Distribuição Global" subtitle="Humano / Bot / Conflito">
          <PlotlyChart figureJson={data.label_distribution_chart} height={300} />
        </ChartCard>
        <ChartCard title="Comparativo por Dataset" subtitle="Classificações por dataset">
          <AbbreviatedChart figureJson={data.comparativo_por_dataset_chart} />
        </ChartCard>
      </div>

      {/* Linha 2: Taxa de Bots + Concordância por Dataset */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <ChartCard title="Taxa de Bots por Dataset" subtitle="Percentual de bots detectados">
          <AbbreviatedChart figureJson={data.bot_rate_by_dataset_chart} />
        </ChartCard>
        <ChartCard title="Concordância por Dataset" subtitle="Taxa de acordo entre anotadores">
          <AbbreviatedChart figureJson={data.agreement_by_dataset_chart} />
        </ChartCard>
      </div>

      {/* Linha 3: Timeline + Eficácia por Critério */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <ChartCard title="Evolução das Anotações" subtitle="Anotações realizadas por dia">
          <PlotlyChart figureJson={data.annotations_over_time_chart} />
        </ChartCard>
        <ChartCard title="Eficácia por Critério" subtitle="Taxa de bots por critério de limpeza">
          <PlotlyChart figureJson={data.criteria_effectiveness_chart} />
        </ChartCard>
      </div>

      <BotCommentsTable data={botsData} onFetch={onFetchBots} />
    </div>
  );
}
