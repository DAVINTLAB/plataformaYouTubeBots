import { useMemo } from "react";
import { PlotlyChart } from "./PlotlyChart";

interface AbbreviatedChartProps {
  figureJson: string;
  height?: number;
  prefix?: string;
}

/**
 * Renderiza um gráfico Plotly substituindo nomes longos no eixo X/Y
 * por siglas curtas (D1, D2, ...) e mostra uma legenda compacta abaixo.
 */
export function AbbreviatedChart({ figureJson, height, prefix = "D" }: AbbreviatedChartProps) {
  const { modifiedJson, legend } = useMemo(() => {
    try {
      const fig = JSON.parse(figureJson) as {
        data: Array<Record<string, unknown>>;
        layout: Record<string, unknown>;
      };

      // Encontrar nomes originais do primeiro trace (x ou y dependendo da orientação)
      const firstTrace = fig.data[0];
      if (!firstTrace) return { modifiedJson: figureJson, legend: [] };

      const isHorizontal = firstTrace.orientation === "h";
      const axis = isHorizontal ? "y" : "x";
      const origNames = (firstTrace[axis] as string[]) ?? [];

      if (origNames.length === 0) {
        return { modifiedJson: figureJson, legend: [] };
      }

      // Criar mapeamento abreviado
      const mapping = origNames.map((name, i) => ({
        short: `${prefix}${i + 1}`,
        full: name,
      }));
      const shortNames = mapping.map((m) => m.short);

      // Substituir em todos os traces
      for (const trace of fig.data) {
        if (Array.isArray(trace[axis]) && (trace[axis] as string[]).length === origNames.length) {
          (trace as Record<string, unknown>)[axis] = shortNames;
        }
        // Adicionar nome completo no hover via customdata
        if (!trace.customdata) {
          (trace as Record<string, unknown>).customdata = origNames.map((n) => [n]);
        }
        // Atualizar hovertemplate para mostrar nome completo
        if (typeof trace.hovertemplate === "string") {
          const ht = trace.hovertemplate as string;
          if (isHorizontal) {
            (trace as Record<string, unknown>).hovertemplate = ht.replace(
              "%{y}",
              "%{customdata[0]}"
            );
          } else {
            (trace as Record<string, unknown>).hovertemplate = ht.replace(
              "%{x}",
              "%{customdata[0]}"
            );
          }
        }
      }

      return {
        modifiedJson: JSON.stringify(fig),
        legend: mapping,
      };
    } catch {
      return { modifiedJson: figureJson, legend: [] };
    }
  }, [figureJson, prefix]);

  return (
    <div>
      <PlotlyChart figureJson={modifiedJson} height={height} />
      {legend.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <div className="flex flex-wrap gap-x-4 gap-y-0.5">
            {legend.map((item) => (
              <span key={item.short} className="text-[10px] text-gray-500">
                <span className="font-semibold text-gray-600">{item.short}</span> {item.full}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
