import { DatasetSummary } from "../../api/clean";

interface DatasetListProps {
  datasets: DatasetSummary[];
  onDownload: (datasetId: string, format: "json" | "csv", name: string) => void;
  onDelete: (datasetId: string) => void;
}

export function DatasetList({ datasets, onDownload, onDelete }: DatasetListProps) {
  if (datasets.length === 0) {
    return <p className="text-sm text-gray-400 italic px-6 py-4">Nenhum dataset criado ainda.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-100">
            <th className="text-left py-2.5 px-6 text-[11px] font-bold uppercase tracking-wider text-gray-400">
              Nome
            </th>
            <th className="text-left py-2.5 pr-4 text-[11px] font-bold uppercase tracking-wider text-gray-400">
              Critérios
            </th>
            <th className="text-left py-2.5 pr-4 text-[11px] font-bold uppercase tracking-wider text-gray-400">
              Selecionados
            </th>
            <th className="text-left py-2.5 pr-4 text-[11px] font-bold uppercase tracking-wider text-gray-400">
              Criado em
            </th>
            <th className="text-left py-2.5 pr-4 text-[11px] font-bold uppercase tracking-wider text-gray-400">
              Exportar
            </th>
            <th className="text-right py-2.5 pr-6 text-[11px] font-bold uppercase tracking-wider text-gray-400" />
          </tr>
        </thead>
        <tbody>
          {datasets.map((ds) => (
            <tr key={ds.dataset_id} className="border-b border-gray-100 last:border-0">
              <td className="py-3 pl-6 pr-4 font-mono text-sm text-gray-800 font-medium">
                {ds.name}
              </td>
              <td className="py-3 pr-4 text-sm text-gray-600">{ds.criteria_applied.join(", ")}</td>
              <td className="py-3 pr-4 text-sm text-gray-600">{ds.total_users_selected}</td>
              <td className="py-3 pr-4 text-sm text-gray-500">
                {new Date(ds.created_at).toLocaleDateString("pt-BR")}
              </td>
              <td className="py-3 pr-4">
                <div className="flex items-center gap-3">
                  <button
                    className="text-xs font-medium text-davint-400 hover:text-davint-500 hover:underline transition-colors"
                    onClick={() => onDownload(ds.dataset_id, "json", ds.name)}
                  >
                    JSON
                  </button>
                  <button
                    className="text-xs font-medium text-davint-400 hover:text-davint-500 hover:underline transition-colors"
                    onClick={() => onDownload(ds.dataset_id, "csv", ds.name)}
                  >
                    CSV
                  </button>
                </div>
              </td>
              <td className="py-3 pr-6 text-right">
                <button
                  className="text-xs font-medium text-red-400 hover:text-red-600 transition-colors"
                  title="Deletar dataset"
                  onClick={() => {
                    if (window.confirm(`Deseja deletar o dataset "${ds.name}"?`)) {
                      onDelete(ds.dataset_id);
                    }
                  }}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    className="w-4 h-4"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
