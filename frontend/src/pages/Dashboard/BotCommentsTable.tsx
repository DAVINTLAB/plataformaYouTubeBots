import { useCallback, useEffect, useState } from "react";
import type { BotCommentItem, BotCommentsResponse } from "../../api/dashboard";

interface BotCommentsTableProps {
  data: BotCommentsResponse | null;
  videoId?: string;
  onFetch: (params: {
    search?: string;
    video_id?: string;
    criteria?: string[];
    page?: number;
    page_size?: number;
  }) => void;
}

const CRITERIA_OPTIONS = [
  "percentil",
  "media",
  "moda",
  "mediana",
  "curtos",
  "intervalo",
  "identicos",
  "perfil",
];

export function BotCommentsTable({ data, videoId, onFetch }: BotCommentsTableProps) {
  const [search, setSearch] = useState("");
  const [criteriaFilter, setCriteriaFilter] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const doFetch = useCallback(
    (p: number, s: string, crit: string[]) => {
      onFetch({
        search: s || undefined,
        video_id: videoId,
        criteria: crit.length > 0 ? crit : undefined,
        page: p,
        page_size: pageSize,
      });
    },
    [onFetch, videoId]
  );

  useEffect(() => {
    doFetch(1, "", []);
  }, [doFetch]);

  const handleSearch = () => {
    setPage(1);
    doFetch(1, search, criteriaFilter);
  };

  const handleCriteriaToggle = (crit: string) => {
    const next = criteriaFilter.includes(crit)
      ? criteriaFilter.filter((c) => c !== crit)
      : [...criteriaFilter, crit];
    setCriteriaFilter(next);
    setPage(1);
    doFetch(1, search, next);
  };

  const handlePage = (newPage: number) => {
    setPage(newPage);
    doFetch(newPage, search, criteriaFilter);
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h3 className="text-[13px] font-semibold text-gray-700">Comentários Bot</h3>
            {data && (
              <p className="text-[10px] text-gray-400 mt-0.5">
                {data.total} comentários encontrados
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Buscar no texto..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="form-input text-xs px-2 py-1 w-48"
            />
            <button onClick={handleSearch} className="btn btn-ghost text-xs px-2 py-1">
              Buscar
            </button>
          </div>
        </div>
        {/* Filtro por critério */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
            Critério:
          </span>
          {CRITERIA_OPTIONS.map((crit) => (
            <button
              key={crit}
              onClick={() => handleCriteriaToggle(crit)}
              className={`text-[10px] px-2 py-0.5 rounded-full border transition-colors ${
                criteriaFilter.includes(crit)
                  ? "bg-davint-400 text-white border-davint-400"
                  : "bg-white text-gray-500 border-gray-200 hover:border-gray-300"
              }`}
            >
              {crit.charAt(0).toUpperCase() + crit.slice(1)}
            </button>
          ))}
          {criteriaFilter.length > 0 && (
            <button
              onClick={() => {
                setCriteriaFilter([]);
                setPage(1);
                doFetch(1, search, []);
              }}
              className="text-[10px] text-davint-400 hover:underline"
            >
              Limpar
            </button>
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              <th className="text-left px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                Dataset
              </th>
              <th className="text-left px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                Autor
              </th>
              <th className="text-left px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                Comentário
              </th>
              <th className="text-center px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                Anot.
              </th>
              <th className="text-center px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                Concord.
              </th>
              <th className="text-center px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                Status
              </th>
              <th className="text-left px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                Critérios
              </th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((item: BotCommentItem, i: number) => (
              <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                <td className="px-4 py-2.5 text-gray-700 font-medium max-w-[110px] truncate">
                  {item.dataset_name}
                </td>
                <td className="px-4 py-2.5 text-gray-600 max-w-[100px] truncate">
                  {item.author_display_name}
                </td>
                <td className="px-4 py-2.5 text-gray-500 max-w-[220px] truncate">
                  {item.text_original}
                </td>
                <td className="px-4 py-2.5 text-center text-gray-600 tabular-nums">
                  {item.annotators_count}
                </td>
                <td className="px-4 py-2.5 text-center">
                  <span
                    className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${
                      item.concordance_pct === 100
                        ? "bg-emerald-50 text-emerald-700"
                        : item.concordance_pct >= 50
                          ? "bg-amber-50 text-amber-700"
                          : "bg-red-50 text-red-700"
                    }`}
                  >
                    {item.concordance_pct}%
                  </span>
                </td>
                <td className="px-4 py-2.5 text-center">
                  {item.conflict_status && (
                    <span
                      className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${
                        item.conflict_status === "resolved"
                          ? "bg-gray-100 text-gray-600"
                          : "bg-orange-50 text-orange-600"
                      }`}
                    >
                      {item.conflict_status === "resolved" ? "Resolvido" : "Pendente"}
                    </span>
                  )}
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex flex-wrap gap-1">
                    {item.criteria.map((c) => (
                      <span
                        key={c}
                        className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium bg-gray-100 text-gray-600"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-gray-400">
                  Nenhum comentário bot encontrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
          <button
            disabled={page <= 1}
            onClick={() => handlePage(page - 1)}
            className="text-xs text-davint-400 hover:underline disabled:text-gray-300 disabled:no-underline"
          >
            Anterior
          </button>
          <span className="text-[10px] text-gray-400">
            Página {page} de {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => handlePage(page + 1)}
            className="text-xs text-davint-400 hover:underline disabled:text-gray-300 disabled:no-underline"
          >
            Próxima
          </button>
        </div>
      )}
    </div>
  );
}
