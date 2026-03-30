import { useCallback, useEffect, useMemo, useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import { StepsCard } from "../../components/StepsCard";
import { useAuthContext } from "../../contexts/AuthContext";
import { useReview } from "../../hooks/useReview";
import type { ConflictDetail, ConflictListItem, BotCommentItem } from "../../api/review";

type Tab = "conflicts" | "bots" | "import";

export function ReviewPage() {
  const { token, isAdmin } = useAuthContext();
  const {
    loading,
    error,
    conflicts,
    conflictDetail,
    bots,
    stats,
    importResult,
    clearError,
    clearImportResult,
    fetchConflicts,
    fetchConflictDetail,
    resolveConflict,
    fetchBots,
    fetchStats,
    importReview,
    downloadExport,
  } = useReview();

  const [tab, setTab] = useState<Tab>("conflicts");
  const [statusFilter, setStatusFilter] = useState<string>("pending");
  const [datasetFilter, setDatasetFilter] = useState<string>("");
  const [selectedConflict, setSelectedConflict] = useState<string | null>(null);
  const [confirmResolve, setConfirmResolve] = useState<{
    conflictId: string;
    label: "bot" | "humano";
  } | null>(null);
  const [conflictsPage, setConflictsPage] = useState(0);
  const [botsPage, setBotsPage] = useState(0);
  const [selectedBot, setSelectedBot] = useState<BotCommentItem | null>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importParseError, setImportParseError] = useState<string | null>(null);

  // Derive dataset list from loaded data
  const datasets = useMemo(() => {
    const map = new Map<string, string>();
    conflicts.forEach((c) => map.set(c.dataset_id, c.dataset_name));
    bots.forEach((b) => map.set(b.dataset_id, b.dataset_name));
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [conflicts, bots]);

  // Load data on mount and when filters change
  useEffect(() => {
    if (!token || !isAdmin) return;
    setConflictsPage(0);
    setBotsPage(0);
    fetchConflicts({
      status: statusFilter || undefined,
      dataset_id: datasetFilter || undefined,
    });
    fetchBots({ dataset_id: datasetFilter || undefined });
    fetchStats();
  }, [token, isAdmin, fetchConflicts, fetchBots, fetchStats, statusFilter, datasetFilter]);

  useEffect(() => {
    if (selectedConflict) {
      fetchConflictDetail(selectedConflict);
    }
  }, [selectedConflict, fetchConflictDetail]);

  const pendingCount = stats?.pending_conflicts ?? 0;

  const handleResolve = useCallback(
    async (conflictId: string, label: "bot" | "humano") => {
      const result = await resolveConflict(conflictId, label);
      if (result) {
        setConfirmResolve(null);
        fetchConflicts({
          status: statusFilter || undefined,
          dataset_id: datasetFilter || undefined,
        });
        fetchStats();
        fetchBots({ dataset_id: datasetFilter || undefined });
      }
    },
    [resolveConflict, fetchConflicts, fetchStats, fetchBots, statusFilter, datasetFilter]
  );

  const handleImport = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!importFile) return;
      setImportParseError(null);
      clearImportResult();
      try {
        const text = await importFile.text();
        const parsed = JSON.parse(text);
        if (!parsed.video_id || !parsed.comments) {
          setImportParseError('JSON deve conter "video_id", "dataset_name" e "comments".');
          return;
        }
        await importReview(parsed);
        setImportFile(null);
        fetchConflicts({ status: statusFilter || undefined });
        fetchStats();
      } catch (err) {
        if (err instanceof SyntaxError) {
          setImportParseError("JSON inválido. Verifique a formatação.");
        } else {
          setImportParseError(err instanceof Error ? err.message : "Erro ao importar.");
        }
      }
    },
    [importFile, importReview, clearImportResult, fetchConflicts, fetchStats, statusFilter]
  );

  if (!isAdmin) {
    return (
      <div className="min-h-screen flex flex-col bg-gray-50">
        <PageHeader breadcrumbs={[{ label: "Início", to: "/" }, { label: "Revisar Conflitos" }]} />
        <main className="flex-1 px-8 py-9 max-w-6xl w-full mx-auto">
          <div className="alert alert-error">Acesso restrito a administradores.</div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <PageHeader breadcrumbs={[{ label: "Início", to: "/" }, { label: "Revisar Conflitos" }]} />

      <main className="flex-1 px-8 py-9 max-w-6xl w-full mx-auto">
        <h1 className="text-2xl font-bold text-gray-800 tracking-tight mb-1">Revisar Conflitos</h1>
        <p className="text-sm text-gray-500 mb-6">
          Resolva divergências entre anotadores comentário a comentário.
        </p>

        <StepsCard
          title="Como funciona"
          steps={[
            {
              label: "Conflitos automáticos",
              description:
                "Quando dois pesquisadores divergem na classificação de um comentário, o conflito aparece na aba Conflitos.",
            },
            {
              label: "Desempate por comentário",
              description:
                'Clique em "Ver" para visualizar as anotações lado a lado e definir o rótulo final (bot ou humano). A decisão é irreversível.',
            },
            {
              label: "Revisão de bots",
              description:
                "Na aba Classificados como Bot, veja todos os comentários sinalizados como bot por pelo menos um anotador, mesmo sem conflito.",
            },
            {
              label: "Exportar resultado",
              description:
                "Selecione um dataset no filtro para exportar o resultado em JSON ou CSV. É possível exportar mesmo com conflitos pendentes — comentários não resolvidos serão marcados como pendentes no arquivo.",
            },
          ]}
        />

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <StatCard label="Total de conflitos" value={stats.total_conflicts} />
            <StatCard label="Pendentes" value={stats.pending_conflicts} color="text-yellow-600" />
            <StatCard label="Resolvidos" value={stats.resolved_conflicts} color="text-green-600" />
            <StatCard
              label="Bots sinalizados"
              value={stats.total_bots_flagged}
              color="text-red-600"
            />
          </div>
        )}

        {error && (
          <div className="alert alert-error mb-4">
            {error}
            <button className="ml-2 text-xs font-semibold underline" onClick={clearError}>
              Fechar
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-gray-200">
          <TabButton
            active={tab === "conflicts"}
            onClick={() => setTab("conflicts")}
            label="Conflitos"
            badge={pendingCount > 0 ? pendingCount : undefined}
          />
          <TabButton
            active={tab === "bots"}
            onClick={() => setTab("bots")}
            label="Classificados como Bot"
          />
          <TabButton
            active={tab === "import"}
            onClick={() => setTab("import")}
            label="Importar JSON"
          />
        </div>

        {/* Filters — shared between conflicts and bots tabs */}
        {tab !== "import" && (
          <div className="flex items-center gap-3 mb-4">
            {tab === "conflicts" && (
              <select
                className="form-input text-sm py-1.5 w-40"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="pending">Pendentes</option>
                <option value="resolved">Resolvidos</option>
                <option value="">Todos</option>
              </select>
            )}
            <select
              className="form-input text-sm py-1.5 w-56"
              value={datasetFilter}
              onChange={(e) => setDatasetFilter(e.target.value)}
            >
              <option value="">Todos os datasets</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>

            <div className="ml-auto flex gap-2">
              <button
                className="text-xs font-medium text-davint-400 hover:underline disabled:text-gray-300 disabled:no-underline"
                disabled={!datasetFilter}
                title={datasetFilter ? "" : "Selecione um dataset para exportar"}
                onClick={() => downloadExport("json", datasetFilter)}
              >
                Exportar JSON
              </button>
              <button
                className="text-xs font-medium text-davint-400 hover:underline disabled:text-gray-300 disabled:no-underline"
                disabled={!datasetFilter}
                title={datasetFilter ? "" : "Selecione um dataset para exportar"}
                onClick={() => downloadExport("csv", datasetFilter)}
              >
                Exportar CSV
              </button>
            </div>
          </div>
        )}

        {/* Tab: Conflicts */}
        {tab === "conflicts" && (
          <ConflictsTab
            conflicts={conflicts}
            loading={loading}
            page={conflictsPage}
            onPageChange={setConflictsPage}
            onSelectConflict={setSelectedConflict}
          />
        )}

        {/* Tab: Bots */}
        {tab === "bots" && (
          <BotsTab
            bots={bots}
            loading={loading}
            page={botsPage}
            onPageChange={setBotsPage}
            onSelectBot={setSelectedBot}
          />
        )}

        {/* Tab: Import */}
        {tab === "import" && (
          <ImportTab
            importFile={importFile}
            onFileChange={(f) => {
              setImportFile(f);
              setImportParseError(null);
            }}
            onImport={handleImport}
            loading={loading}
            importParseError={importParseError}
            importResult={importResult}
            onClearResult={clearImportResult}
          />
        )}
      </main>

      {/* Conflict detail modal */}
      {selectedConflict && conflictDetail && (
        <ConflictModal
          detail={conflictDetail}
          onClose={() => setSelectedConflict(null)}
          onResolve={(label) =>
            setConfirmResolve({ conflictId: conflictDetail.conflict_id, label })
          }
        />
      )}

      {/* Confirm resolve modal */}
      {confirmResolve && (
        <ConfirmModal
          label={confirmResolve.label}
          onConfirm={() => handleResolve(confirmResolve.conflictId, confirmResolve.label)}
          onCancel={() => setConfirmResolve(null)}
        />
      )}

      {/* Bot detail modal */}
      {selectedBot && (
        <BotDetailModal
          bot={selectedBot}
          onClose={() => setSelectedBot(null)}
          onViewConflict={(id) => {
            setSelectedBot(null);
            setSelectedConflict(id);
          }}
        />
      )}
    </div>
  );
}

// ─── Shared sub-components ──────────────────────────────────────────────────

function StatCard({
  label,
  value,
  color = "text-gray-800",
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  label,
  badge,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  badge?: number;
}) {
  return (
    <button
      className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
        active
          ? "border-davint-400 text-davint-500"
          : "border-transparent text-gray-500 hover:text-gray-700"
      }`}
      onClick={onClick}
    >
      {label}
      {badge !== undefined && (
        <span className="ml-1.5 inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold rounded-full bg-yellow-100 text-yellow-700">
          {badge}
        </span>
      )}
    </button>
  );
}

function LabelBadge({ label }: { label: string }) {
  const isBot = label === "bot";
  return (
    <span
      className={`ml-1.5 inline-flex text-[10px] font-bold px-2 py-0.5 rounded-full ${
        isBot ? "bg-red-50 text-red-600" : "bg-green-50 text-green-600"
      }`}
    >
      {isBot ? "Bot" : "Humano"}
    </span>
  );
}

function ConflictStatusBadge({ status }: { status: string }) {
  const styles =
    status === "pending" ? "bg-yellow-50 text-yellow-700" : "bg-green-50 text-green-600";
  return (
    <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${styles}`}>
      {status === "pending" ? "Pendente" : "Resolvido"}
    </span>
  );
}

function Truncate({ text, max = 80 }: { text: string; max?: number }) {
  return <>{text.length > max ? text.slice(0, max) + "…" : text}</>;
}

// ─── Conflicts Tab ──────────────────────────────────────────────────────────

function ConflictsTab({
  conflicts,
  loading,
  page,
  onPageChange,
  onSelectConflict,
}: {
  conflicts: ConflictListItem[];
  loading: boolean;
  page: number;
  onPageChange: (p: number) => void;
  onSelectConflict: (id: string) => void;
}) {
  const PER_PAGE = 20;
  const totalPages = Math.ceil(conflicts.length / PER_PAGE);
  const paginated = useMemo(
    () => conflicts.slice(page * PER_PAGE, (page + 1) * PER_PAGE),
    [conflicts, page]
  );

  if (conflicts.length === 0 && !loading) {
    return (
      <p className="text-sm text-gray-500">
        Nenhum conflito encontrado com os filtros selecionados.
      </p>
    );
  }

  return (
    <div>
      {loading && <p className="text-sm text-gray-500 mb-4">Carregando...</p>}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                Comentário
              </th>
              <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                Autor
              </th>
              <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                Dataset
              </th>
              <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                Status
              </th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {paginated.map((c) => (
              <tr
                key={c.conflict_id}
                className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
                onClick={() => onSelectConflict(c.conflict_id)}
              >
                <td className="px-4 py-3 text-gray-700 max-w-[280px]">
                  <Truncate text={c.text_original} max={80} />
                </td>
                <td className="px-4 py-3 font-medium text-gray-800 whitespace-nowrap">
                  {c.author_display_name}
                </td>
                <td className="px-4 py-3 text-gray-500 whitespace-nowrap text-xs">
                  {c.dataset_name}
                </td>
                <td className="px-4 py-3">
                  <ConflictStatusBadge status={c.status} />
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="text-xs font-medium text-davint-400">Ver &rarr;</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          onPageChange={onPageChange}
          total={conflicts.length}
        />
      )}
    </div>
  );
}

// ─── Bots Tab ───────────────────────────────────────────────────────────────

function BotsTab({
  bots,
  loading,
  page,
  onPageChange,
  onSelectBot,
}: {
  bots: BotCommentItem[];
  loading: boolean;
  page: number;
  onPageChange: (p: number) => void;
  onSelectBot: (bot: BotCommentItem) => void;
}) {
  const PER_PAGE = 20;
  const totalPages = Math.ceil(bots.length / PER_PAGE);
  const paginated = useMemo(() => bots.slice(page * PER_PAGE, (page + 1) * PER_PAGE), [bots, page]);

  if (bots.length === 0 && !loading) {
    return (
      <p className="text-sm text-gray-500">
        Nenhum comentário classificado como bot com os filtros selecionados.
      </p>
    );
  }

  return (
    <div>
      {loading && <p className="text-sm text-gray-500 mb-4">Carregando...</p>}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                Comentário
              </th>
              <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                Autor
              </th>
              <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                Dataset
              </th>
              <th className="text-left px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                Anotações
              </th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {paginated.map((b) => {
              const botCount = b.annotations.filter((a) => a.label === "bot").length;
              const humanCount = b.annotations.filter((a) => a.label === "humano").length;
              return (
                <tr key={b.comment_db_id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-700 max-w-[280px]">
                    <Truncate text={b.text_original} max={80} />
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-800 whitespace-nowrap">
                    {b.author_display_name}
                  </td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap text-xs">
                    {b.dataset_name}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1 text-xs">
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-red-50 text-red-600 text-[10px] font-bold">
                          {botCount}
                        </span>
                        <span className="text-gray-400">bot</span>
                      </span>
                      <span className="inline-flex items-center gap-1 text-xs">
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-green-50 text-green-600 text-[10px] font-bold">
                          {humanCount}
                        </span>
                        <span className="text-gray-400">humano</span>
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="text-xs font-medium text-davint-400 hover:underline"
                      onClick={() => onSelectBot(b)}
                    >
                      Detalhes &rarr;
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          onPageChange={onPageChange}
          total={bots.length}
        />
      )}
    </div>
  );
}

// ─── Import Tab ─────────────────────────────────────────────────────────────

function ImportTab({
  importFile,
  onFileChange,
  onImport,
  loading,
  importParseError,
  importResult,
  onClearResult,
}: {
  importFile: File | null;
  onFileChange: (f: File | null) => void;
  onImport: (e: React.FormEvent) => void;
  loading: boolean;
  importParseError: string | null;
  importResult: { imported: number; skipped: number; errors: string[] } | null;
  onClearResult: () => void;
}) {
  return (
    <>
      <div className="bg-davint-50 rounded-xl p-5 mb-6">
        <h3 className="text-xs font-bold uppercase tracking-wider text-davint-600 mb-3">
          Formato esperado
        </h3>
        <p className="text-xs text-gray-600 mb-3">
          O arquivo deve ser um JSON no formato exportado pela plataforma, com as chaves{" "}
          <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
            video_id
          </code>
          ,{" "}
          <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
            dataset_name
          </code>{" "}
          e{" "}
          <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
            comments
          </code>{" "}
          (array de comentários com{" "}
          <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
            resolution
          </code>
          ).
        </p>
        <p className="text-xs text-gray-400">
          Este é o mesmo formato gerado pelo botão "Exportar JSON". A coleta referenciada pelo{" "}
          <code className="font-mono">video_id</code> deve existir na plataforma.
        </p>
      </div>

      {importResult && (
        <div className="flex items-start gap-2 p-3 bg-green-50 border border-green-200 rounded-lg mb-4">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div className="text-xs text-green-700">
            <p>
              Import concluído: {importResult.imported} resolvido(s), {importResult.skipped}{" "}
              ignorado(s).
            </p>
            {importResult.errors.length > 0 && (
              <ul className="mt-1 list-disc list-inside">
                {importResult.errors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </div>
          <button
            className="ml-auto text-xs font-semibold text-green-600 underline"
            onClick={onClearResult}
          >
            Fechar
          </button>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <form onSubmit={onImport} className="flex flex-col gap-5">
          <div className="form-group">
            <label className="form-label" htmlFor="import_review">
              Arquivo JSON
            </label>
            <input
              id="import_review"
              className="form-input"
              type="file"
              accept=".json"
              onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
              disabled={loading}
            />
          </div>

          {importParseError && <div className="alert alert-error">{importParseError}</div>}

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={loading || !importFile}
          >
            {loading ? "Importando..." : "Importar Revisões"}
          </button>
        </form>
      </div>
    </>
  );
}

// ─── Conflict Detail Modal ──────────────────────────────────────────────────

function ConflictModal({
  detail,
  onClose,
  onResolve,
}: {
  detail: ConflictDetail;
  onClose: () => void;
  onResolve: (label: "bot" | "humano") => void;
}) {
  const isPending = detail.status === "pending";

  // The comment that triggered the conflict (first in the list)
  const conflictComment = detail.comments[0];
  // Other comments from the same author (context)
  const otherComments = detail.comments.slice(1);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-bold text-gray-800">Desempate de comentário</h2>
            <p className="text-xs text-gray-500">
              {detail.dataset_name} &middot; {detail.author_display_name}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ConflictStatusBadge status={detail.status} />
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-5 h-5"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* The comment in conflict */}
        {conflictComment && (
          <div className="p-5 border-b border-gray-100">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">
              Comentário em conflito
            </h3>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-sm text-gray-800 whitespace-pre-wrap">
                {conflictComment.text_original}
              </p>
              <div className="flex gap-3 mt-2 text-[11px] text-gray-400">
                <span>{new Date(conflictComment.published_at).toLocaleDateString("pt-BR")}</span>
                <span>{conflictComment.like_count} curtidas</span>
                <span>{conflictComment.reply_count} respostas</span>
              </div>
            </div>
          </div>
        )}

        {/* Side-by-side annotations */}
        <div className="grid grid-cols-2 gap-4 p-5 border-b border-gray-100">
          <AnnotationCard
            side={detail.annotation_a}
            highlight={detail.resolved_label === detail.annotation_a.label}
          />
          <AnnotationCard
            side={detail.annotation_b}
            highlight={detail.resolved_label === detail.annotation_b.label}
          />
        </div>

        {/* Resolution info */}
        {detail.status === "resolved" && detail.resolved_label && (
          <div className="flex items-start gap-2 p-4 mx-5 mt-4 bg-green-50 border border-green-200 rounded-lg">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div className="text-xs text-green-700">
              Resolvido como <strong>{detail.resolved_label === "bot" ? "Bot" : "Humano"}</strong>{" "}
              por <strong>{detail.resolved_by}</strong> em{" "}
              {detail.resolved_at ? new Date(detail.resolved_at).toLocaleString("pt-BR") : "—"}
            </div>
          </div>
        )}

        {/* Other comments from same author (context) */}
        {otherComments.length > 0 && (
          <div className="p-5">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">
              Outros comentários do mesmo autor ({otherComments.length})
            </h3>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {otherComments.map((c) => (
                <div key={c.comment_db_id} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">{c.text_original}</p>
                  <div className="flex gap-3 mt-1 text-[11px] text-gray-400">
                    <span>{new Date(c.published_at).toLocaleDateString("pt-BR")}</span>
                    <span>{c.like_count} curtidas</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Resolve buttons */}
        {isPending && (
          <div className="flex items-center justify-between p-5 border-t border-gray-100">
            <p className="text-xs text-gray-400">
              A decisão é irreversível e se aplica a este comentário.
            </p>
            <div className="flex gap-3">
              <button className="btn btn-ghost" onClick={() => onResolve("humano")}>
                Definir como Humano
              </button>
              <button className="btn btn-primary" onClick={() => onResolve("bot")}>
                Definir como Bot
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AnnotationCard({
  side,
  highlight,
}: {
  side: {
    annotator: string;
    label: string;
    justificativa: string | null;
    annotated_at: string;
  };
  highlight: boolean;
}) {
  return (
    <div
      className={`rounded-lg border p-4 ${
        highlight ? "border-green-300 bg-green-50" : "border-gray-200 bg-white"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-semibold text-gray-800">{side.annotator}</p>
        <LabelBadge label={side.label} />
      </div>
      {side.justificativa && (
        <p className="text-xs text-gray-600 mb-2 italic">&ldquo;{side.justificativa}&rdquo;</p>
      )}
      <p className="text-[11px] text-gray-400">
        {new Date(side.annotated_at).toLocaleString("pt-BR")}
      </p>
    </div>
  );
}

// ─── Bot Detail Modal ────────────────────────────────────────────────────────

function BotDetailModal({
  bot,
  onClose,
  onViewConflict,
}: {
  bot: BotCommentItem;
  onClose: () => void;
  onViewConflict: (conflictId: string) => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-bold text-gray-800">Detalhes do comentário</h2>
            <p className="text-xs text-gray-500">
              {bot.dataset_name} &middot; {bot.author_display_name}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-5 h-5"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Comment */}
        <div className="p-5 border-b border-gray-100">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">
            Comentário
          </h3>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{bot.text_original}</p>
          </div>
        </div>

        {/* Annotations */}
        <div className="p-5 border-b border-gray-100">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-3">
            Anotações ({bot.annotations.length})
          </h3>
          <div className="space-y-3">
            {bot.annotations.map((a, i) => (
              <div key={i} className="flex items-start gap-3 bg-gray-50 rounded-lg p-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-semibold text-gray-800">{a.annotator_name}</span>
                    <LabelBadge label={a.label} />
                  </div>
                  {a.justificativa && (
                    <p className="text-xs text-gray-600 italic">&ldquo;{a.justificativa}&rdquo;</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Conflict link */}
        <div className="p-5 flex items-center justify-between">
          {bot.has_conflict && bot.conflict_id ? (
            <>
              <span className="text-xs text-yellow-700">
                Este comentário tem um conflito entre anotadores.
              </span>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => onViewConflict(bot.conflict_id!)}
              >
                Ir para conflito
              </button>
            </>
          ) : (
            <span className="text-xs text-gray-400">
              Todos os anotadores concordam na classificação deste comentário.
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Confirm Modal ──────────────────────────────────────────────────────────

function ConfirmModal({
  label,
  onConfirm,
  onCancel,
}: {
  label: "bot" | "humano";
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl max-w-sm w-full mx-4 p-6">
        <h3 className="text-lg font-bold text-gray-800 mb-2">Confirmar decisão</h3>
        <p className="text-sm text-gray-600 mb-4">
          Definir este comentário como{" "}
          <strong className={label === "bot" ? "text-red-600" : "text-green-600"}>
            {label === "bot" ? "Bot" : "Humano"}
          </strong>
          ? Esta ação é <strong>irreversível</strong>.
        </p>
        <div className="flex justify-end gap-2">
          <button className="btn btn-ghost" onClick={onCancel}>
            Cancelar
          </button>
          <button className="btn btn-primary" onClick={onConfirm}>
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Pagination ─────────────────────────────────────────────────────────────

function Pagination({
  page,
  totalPages,
  onPageChange,
  total,
}: {
  page: number;
  totalPages: number;
  onPageChange: (p: number) => void;
  total: number;
}) {
  const from = page * 20 + 1;
  const to = Math.min((page + 1) * 20, total);
  return (
    <div className="flex items-center justify-between mt-4">
      <p className="text-xs text-gray-400">
        {from}–{to} de {total}
      </p>
      <div className="flex gap-1">
        <button
          className="btn btn-ghost btn-sm"
          disabled={page === 0}
          onClick={() => onPageChange(page - 1)}
        >
          Anterior
        </button>
        <button
          className="btn btn-ghost btn-sm"
          disabled={page >= totalPages - 1}
          onClick={() => onPageChange(page + 1)}
        >
          Próxima
        </button>
      </div>
    </div>
  );
}
