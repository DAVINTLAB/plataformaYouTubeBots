import Plotly from "plotly.js-dist-min";
import { useEffect, useRef } from "react";

interface PlotlyChartProps {
  figureJson: string;
  height?: number;
}

export function PlotlyChart({ figureJson, height = 320 }: PlotlyChartProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !figureJson) return;

    let fig: { data: Plotly.Data[]; layout: Partial<Plotly.Layout> };
    try {
      fig = JSON.parse(figureJson) as {
        data: Plotly.Data[];
        layout: Partial<Plotly.Layout>;
      };
    } catch {
      return;
    }

    const layout: Partial<Plotly.Layout> = {
      ...fig.layout,
      autosize: true,
      height,
    };

    Plotly.newPlot(ref.current, fig.data, layout, {
      responsive: true,
      displayModeBar: false,
    });

    const el = ref.current;
    const ro = new ResizeObserver(() => {
      if (el) Plotly.Plots.resize(el);
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      if (el) Plotly.purge(el);
    };
  }, [figureJson, height]);

  return <div ref={ref} style={{ width: "100%" }} />;
}

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  full?: boolean;
}

export function ChartCard({ title, subtitle, children, full }: ChartCardProps) {
  return (
    <div
      className={`bg-white rounded-xl border border-gray-200 p-5 ${full ? "col-span-1 lg:col-span-2" : ""}`}
    >
      <div className="mb-3">
        <h3 className="text-[13px] font-semibold text-gray-700">{title}</h3>
        {subtitle && <p className="text-[11px] text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
