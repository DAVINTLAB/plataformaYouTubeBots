import { PreviewResponse } from "../../api/clean";

interface PreviewPanelProps {
  preview: PreviewResponse;
  datasetName: string;
  selectedCriteria: string[];
}

const CRITERIA_LABELS: Record<string, string> = {
  percentil: "Percentil (top 30%)",
  media: "Acima da média",
  moda: "Acima da moda",
  mediana: "Acima da mediana",
  curtos: "Curtos/repetitivos",
  intervalo: "Intervalo temporal",
  identicos: "Idênticos",
  perfil: "Perfil suspeito",
};

export function PreviewPanel({ preview, datasetName, selectedCriteria }: PreviewPanelProps) {
  const { central_measures: cm, by_criteria, total_users, union_if_combined } = preview;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">
        Preview dos critérios
      </h3>

      {/* Medidas centrais */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-[11px] font-semibold text-gray-400 uppercase">Média</p>
          <p className="text-lg font-bold text-gray-800">{cm.mean}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-[11px] font-semibold text-gray-400 uppercase">Moda</p>
          <p className="text-lg font-bold text-gray-800">{cm.mode}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 text-center">
          <p className="text-[11px] font-semibold text-gray-400 uppercase">Mediana</p>
          <p className="text-lg font-bold text-gray-800">{cm.median}</p>
        </div>
      </div>

      <div className="text-xs text-gray-500 mb-4">
        IQR: [{cm.iqr_lower}, {cm.iqr_upper}] — Total de usuários: {total_users}
      </div>

      {/* Contagem por critério */}
      <table className="w-full text-sm mb-4">
        <thead>
          <tr>
            <th className="text-[11px] font-bold uppercase tracking-wider text-gray-400 text-left pb-2">
              Critério
            </th>
            <th className="text-[11px] font-bold uppercase tracking-wider text-gray-400 text-right pb-2">
              Selecionados
            </th>
          </tr>
        </thead>
        <tbody>
          {selectedCriteria.map((name) => {
            const info = by_criteria[name];
            if (!info) return null;
            return (
              <tr key={name} className="border-t border-gray-100">
                <td className="py-2 text-gray-700">{CRITERIA_LABELS[name] ?? name}</td>
                <td className="py-2 text-right font-semibold text-gray-800">
                  {info.selected_users}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* União */}
      {selectedCriteria.length > 1 && (
        <div className="bg-davint-50 rounded-lg p-3 mb-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-davint-600">
              Total combinado (qualquer critério)
            </span>
            <span className="text-lg font-bold text-davint-600">{union_if_combined}</span>
          </div>
        </div>
      )}

      {/* Nome do dataset */}
      <div className="border-t border-gray-100 pt-3">
        <p className="text-[11px] font-semibold text-gray-400 uppercase mb-1">Nome do dataset</p>
        <p className="text-sm font-mono font-semibold text-gray-800 bg-gray-50 rounded px-3 py-2">
          {datasetName || "—"}
        </p>
      </div>
    </div>
  );
}
