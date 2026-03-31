import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import { StatusBadge } from "../../components/StatusBadge";
import { StepsCard } from "../../components/StepsCard";
import { useData } from "../../hooks/useData";
import { ChangePasswordModal } from "../Home/ChangePasswordModal";
import { usersApi } from "../../api/users";
import { useAuthContext } from "../../contexts/AuthContext";
import type { DataCollection } from "../../api/data";
import type { DataDataset, DataAnnotationProgress } from "../../api/data";

// ─── Icons ──────────────────────────────────────────────────────────────────

function IconChevron({ open }: { open: boolean }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={2}
      stroke="currentColor"
      className={`w-4 h-4 transition-transform ${open ? "rotate-180" : ""}`}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

function IconRefresh() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="w-4 h-4"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.992 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
      />
    </svg>
  );
}

function IconX() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="w-4 h-4"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

// ─── Detail Field ───────────────────────────────────────────────────────────

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-0.5">{label}</p>
      <p className="text-xs text-gray-700">{value}</p>
    </div>
  );
}

// ─── Summary Card ───────────────────────────────────────────────────────────

function SummaryCard({
  summary,
}: {
  summary: {
    collections_count: number;
    comments_count: number;
    datasets_count: number;
    annotations_count: number;
    estimated_size_mb: number;
  } | null;
}) {
  if (!summary) return null;

  const NEON_LIMIT_MB = 512;
  const usagePercent = Math.min(100, (summary.estimated_size_mb / NEON_LIMIT_MB) * 100);

  const counters = [
    { label: "Coletas", value: summary.collections_count },
    { label: "Comentários", value: summary.comments_count },
    { label: "Datasets", value: summary.datasets_count },
    { label: "Anotações", value: summary.annotations_count },
  ];

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
      <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">
        Resumo do banco
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
        {counters.map((c) => (
          <div key={c.label} className="text-center">
            <p className="text-2xl font-bold text-gray-800">{c.value.toLocaleString("pt-BR")}</p>
            <p className="text-xs text-gray-500">{c.label}</p>
          </div>
        ))}
      </div>
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <p className="text-xs font-medium text-gray-600">
            Uso estimado do banco (Neon free tier)
          </p>
          <p className="text-xs font-semibold text-gray-700">
            {summary.estimated_size_mb} MB / {NEON_LIMIT_MB} MB
          </p>
        </div>
        <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              usagePercent > 80
                ? "bg-red-400"
                : usagePercent > 50
                  ? "bg-yellow-400"
                  : "bg-davint-400"
            }`}
            style={{ width: `${usagePercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// ─── Collapsible Section ────────────────────────────────────────────────────

function Section({
  title,
  count,
  defaultOpen = true,
  children,
}: {
  title: string;
  count: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-white rounded-xl border border-gray-200 mb-4">
      <button
        className="w-full flex items-center justify-between px-5 py-4 text-left"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-800">{title}</h3>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
            {count}
          </span>
        </div>
        <IconChevron open={open} />
      </button>
      {open && <div className="px-5 pb-5">{children}</div>}
    </div>
  );
}

// ─── Detail Panels ──────────────────────────────────────────────────────────

function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `${m}min ${s}s` : `${m}min`;
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function CollectionDetail({
  col,
  onExport,
  onDelete,
  onClose,
}: {
  col: DataCollection;
  onExport: (format: "json" | "csv") => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  return (
    <div className="mt-3 bg-gray-50 rounded-lg border border-gray-200 p-4 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-bold text-gray-700">Detalhes da coleta</h4>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <IconX />
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <Field label="ID do vídeo" value={col.video_id} />
        <Field label="Título" value={col.video_title || "—"} />
        <Field label="Status" value={<StatusBadge status={col.status} size="sm" />} />
        <Field
          label="Enriquecimento"
          value={col.enrich_status ? <StatusBadge status={col.enrich_status} size="sm" /> : "—"}
        />
        <Field label="Comentários" value={col.total_comments?.toLocaleString("pt-BR") ?? "—"} />
        <Field label="Usuários" value={col.total_users.toLocaleString("pt-BR")} />
        <Field label="Coletado por" value={col.collected_by} />
        <Field label="Início da coleta" value={formatDateTime(col.created_at)} />
        <Field
          label="Conclusão"
          value={col.completed_at ? formatDateTime(col.completed_at) : "—"}
        />
        <Field label="Duração" value={formatDuration(col.duration_seconds)} />
        <Field
          label="Canais sem data"
          value={
            col.channel_dates_failed === true
              ? "Sim"
              : col.channel_dates_failed === false
                ? "Não"
                : "—"
          }
        />
      </div>
      <div className="flex items-center gap-2">
        <button className="btn btn-ghost btn-sm" onClick={() => onExport("json")}>
          Exportar JSON
        </button>
        <button className="btn btn-ghost btn-sm" onClick={() => onExport("csv")}>
          Exportar CSV
        </button>
        <button
          className="btn btn-danger btn-sm ml-auto"
          onClick={onDelete}
          disabled={col.status === "running"}
        >
          Deletar coleta
        </button>
      </div>
    </div>
  );
}

function DatasetDetail({
  ds,
  onDownload,
  onDelete,
  onClose,
}: {
  ds: DataDataset;
  onDownload: (format: "json" | "csv") => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  return (
    <div className="mt-3 bg-gray-50 rounded-lg border border-gray-200 p-4 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-bold text-gray-700">Detalhes do dataset</h4>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <IconX />
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <Field label="Nome" value={ds.name} />
        <Field label="Vídeo" value={ds.video_id} />
        <Field
          label="Critérios"
          value={
            <div className="flex flex-wrap gap-1 mt-0.5">
              {ds.criteria.map((c) => (
                <span
                  key={c}
                  className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-davint-50 text-davint-400"
                >
                  {c}
                </span>
              ))}
            </div>
          }
        />
        <Field
          label="Usuários"
          value={`${ds.total_selected} selecionados de ${ds.total_users_original} total`}
        />
        <Field label="Comentários" value={ds.total_comments.toLocaleString("pt-BR")} />
        <Field label="Criado por" value={ds.created_by} />
        <Field label="Criado em" value={formatDateTime(ds.created_at)} />
      </div>
      <div className="flex items-center gap-2">
        <button className="btn btn-ghost btn-sm" onClick={() => onDownload("json")}>
          Exportar JSON
        </button>
        <button className="btn btn-ghost btn-sm" onClick={() => onDownload("csv")}>
          Exportar CSV
        </button>
        <button className="btn btn-danger btn-sm ml-auto" onClick={onDelete}>
          Deletar dataset
        </button>
      </div>
    </div>
  );
}

function AnnotationDetail({
  ann,
  onExport,
  onDelete,
  onClose,
}: {
  ann: DataAnnotationProgress;
  onExport: (format: "json" | "csv") => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  const isComplete = ann.total > 0 && ann.pending === 0 && ann.conflicts === ann.conflicts_resolved;
  const progressPct = ann.total > 0 ? Math.round((ann.annotated / ann.total) * 100) : 0;

  return (
    <div className="mt-3 bg-gray-50 rounded-lg border border-gray-200 p-4 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-bold text-gray-700">Progresso de anotação</h4>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <IconX />
        </button>
      </div>

      {/* Progress bar */}
      <div className="mb-4">
        <div className="flex justify-between mb-1">
          <p className="text-xs text-gray-500">
            {ann.annotated} de {ann.total} comentários anotados
          </p>
          <p className="text-xs font-semibold text-gray-600">{progressPct}%</p>
        </div>
        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${isComplete ? "bg-green-400" : "bg-davint-400"}`}
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <Field label="Dataset" value={ann.dataset_name} />
        <Field label="Anotadores" value={ann.annotators_count} />
        <Field label="Pendentes" value={ann.pending} />
        <Field
          label="Conflitos"
          value={`${ann.conflicts_resolved} resolvidos / ${ann.conflicts} total`}
        />
        <Field label="Bots (comentários)" value={ann.bots_comments} />
        <Field label="Bots (usuários)" value={ann.bots_users} />
        <Field
          label="Status"
          value={
            <span
              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                isComplete ? "bg-green-50 text-green-600" : "bg-yellow-50 text-yellow-600"
              }`}
            >
              {isComplete ? "Concluído" : "Em andamento"}
            </span>
          }
        />
      </div>
      <div className="flex items-center gap-2">
        <button className="btn btn-ghost btn-sm" onClick={() => onExport("json")}>
          Exportar JSON
        </button>
        <button className="btn btn-ghost btn-sm" onClick={() => onExport("csv")}>
          Exportar CSV
        </button>
        <button className="btn btn-danger btn-sm ml-auto" onClick={onDelete}>
          Deletar dataset
        </button>
      </div>
    </div>
  );
}

function TrainingDetail({
  ds,
  onExport,
  onDelete,
  onClose,
}: {
  ds: DataAnnotationProgress;
  onExport: (format: "json" | "csv") => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  return (
    <div className="mt-3 bg-gray-50 rounded-lg border border-gray-200 p-4 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-bold text-gray-700">Dados para treinamento</h4>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <IconX />
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <Field label="Dataset" value={ds.dataset_name} />
        <Field label="Comentários" value={ds.total} />
        <Field label="Anotadores" value={ds.annotators_count} />
        <Field label="Conflitos resolvidos" value={ds.conflicts_resolved} />
        <Field label="Bots detectados (comentários)" value={ds.bots_comments} />
        <Field label="Bots detectados (usuários)" value={ds.bots_users} />
        <Field label="Humanos (comentários)" value={ds.total - ds.bots_comments} />
      </div>

      <div className="flex items-start gap-2 p-3 bg-davint-50 rounded-lg mb-3">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="w-4 h-4 text-davint-400 flex-shrink-0 mt-0.5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
          />
        </svg>
        <p className="text-xs text-davint-700">
          O export inclui o rótulo final de cada comentário (bot ou humano), as anotações
          individuais e as resoluções de conflito.
        </p>
      </div>

      <div className="flex items-center gap-2">
        <button className="btn btn-ghost btn-sm" onClick={() => onExport("json")}>
          Exportar JSON
        </button>
        <button className="btn btn-ghost btn-sm" onClick={() => onExport("csv")}>
          Exportar CSV
        </button>
        <button className="btn btn-danger btn-sm ml-auto" onClick={onDelete}>
          Deletar dataset
        </button>
      </div>
    </div>
  );
}

// ─── Table header helper ────────────────────────────────────────────────────

const TH_CLS = "text-[11px] font-bold uppercase tracking-wider text-gray-400 pb-2";

// ─── DataPage ───────────────────────────────────────────────────────────────

export function DataPage() {
  const { token } = useAuthContext();
  const {
    loading,
    error,
    summary,
    collections,
    datasets,
    annotations,
    loadAll,
    deleteCollection,
    deleteDataset,
    exportCollection,
    exportAnnotations,
    downloadDataset,
    exportReview,
  } = useData();

  const [showChangePassword, setShowChangePassword] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Selected items for detail panels
  const [selectedCol, setSelectedCol] = useState<string | null>(null);
  const [selectedDs, setSelectedDs] = useState<string | null>(null);
  const [selectedAnn, setSelectedAnn] = useState<string | null>(null);
  const [selectedTraining, setSelectedTraining] = useState<string | null>(null);

  // Fecha todos os painéis de outras seções ao abrir um novo
  const closeAllPanels = () => {
    setSelectedCol(null);
    setSelectedDs(null);
    setSelectedAnn(null);
    setSelectedTraining(null);
  };

  const togglePanel = (current: string | null, id: string, setter: (v: string | null) => void) => {
    if (current === id) {
      setter(null);
    } else {
      closeAllPanels();
      setter(id);
    }
  };

  const handleDelete = async (col: DataCollection) => {
    if (col.status === "running") {
      setActionError("Não é possível deletar uma coleta em andamento.");
      return;
    }
    if (!window.confirm("Tem certeza que deseja deletar esta coleta e todos os dados associados?"))
      return;
    setActionError(null);
    try {
      await deleteCollection(col.collection_id);
      setSelectedCol(null);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Erro ao deletar coleta.");
    }
  };

  const handleDeleteDataset = async (datasetId: string) => {
    if (!window.confirm("Tem certeza que deseja deletar este dataset e todos os dados associados?"))
      return;
    setActionError(null);
    try {
      await deleteDataset(datasetId);
      setSelectedDs(null);
      setSelectedAnn(null);
      setSelectedTraining(null);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Erro ao deletar dataset.");
    }
  };

  const withErrorHandling = async (fn: () => Promise<void>, fallback: string) => {
    setActionError(null);
    try {
      await fn();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : fallback);
    }
  };

  const completedDatasets = annotations.filter(
    (a) => a.total > 0 && a.pending === 0 && a.conflicts === a.conflicts_resolved
  );

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <PageHeader
        breadcrumbs={[{ label: "Início", to: "/" }, { label: "Catálogo de Dados" }]}
        onChangePassword={() => setShowChangePassword(true)}
      />

      <main className="flex-1 px-8 py-9 max-w-6xl w-full mx-auto">
        <StepsCard
          title="Catálogo de Dados"
          steps={[
            {
              label: "Resumo do banco",
              description:
                "Veja quantas coletas, comentários, datasets e anotações existem, e o uso estimado do banco.",
            },
            {
              label: "Gerencie coletas e datasets",
              description: "Clique em qualquer item para ver detalhes, exportar ou deletar.",
            },
            {
              label: "Exporte dados para treinamento",
              description:
                "Datasets com anotação concluída e conflitos resolvidos ficam prontos para exportar.",
            },
          ]}
        />

        {(error || actionError) && (
          <div className="alert alert-error mb-4">{error || actionError}</div>
        )}

        {loading && (
          <div className="flex items-center gap-2 p-3 bg-davint-50 rounded-lg mb-4">
            <svg
              className="w-4 h-4 text-davint-400 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            <p className="text-xs text-davint-700">Carregando dados do catálogo...</p>
          </div>
        )}

        {!loading && (
          <>
            <div className="flex justify-end mb-4">
              <button className="btn btn-ghost btn-sm flex items-center gap-1.5" onClick={loadAll}>
                <IconRefresh />
                Atualizar
              </button>
            </div>

            <SummaryCard summary={summary} />

            {/* ── Coletas ── */}
            <Section title="Coletas" count={collections.length}>
              {collections.length === 0 ? (
                <p className="text-xs text-gray-400 py-2">Nenhuma coleta encontrada.</p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left">
                      <thead>
                        <tr>
                          <th className={TH_CLS}>Vídeo</th>
                          <th className={TH_CLS}>Comentários</th>
                          <th className={TH_CLS}>Status</th>
                          <th className={TH_CLS}>Data</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {collections.map((col) => (
                          <tr
                            key={col.collection_id}
                            className={`cursor-pointer transition-colors ${selectedCol === col.collection_id ? "bg-davint-50" : "hover:bg-gray-50"}`}
                            onClick={() =>
                              togglePanel(selectedCol, col.collection_id, setSelectedCol)
                            }
                          >
                            <td className="py-2.5 pr-3">
                              <p className="text-xs font-medium text-gray-800 truncate max-w-[280px]">
                                {col.video_title || col.video_id}
                              </p>
                              <p className="text-[10px] text-gray-400">{col.video_id}</p>
                            </td>
                            <td className="py-2.5 pr-3 text-xs text-gray-600">
                              {col.total_comments?.toLocaleString("pt-BR") ?? "—"}
                            </td>
                            <td className="py-2.5 pr-3">
                              <StatusBadge status={col.status} size="sm" />
                            </td>
                            <td className="py-2.5 pr-3 text-xs text-gray-500">
                              {new Date(col.created_at).toLocaleDateString("pt-BR")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {selectedCol &&
                    (() => {
                      const col = collections.find((c) => c.collection_id === selectedCol);
                      if (!col) return null;
                      return (
                        <CollectionDetail
                          col={col}
                          onExport={(fmt) =>
                            withErrorHandling(
                              () => exportCollection(col.collection_id, fmt, col.video_id),
                              "Erro ao exportar."
                            )
                          }
                          onDelete={() => handleDelete(col)}
                          onClose={() => setSelectedCol(null)}
                        />
                      );
                    })()}
                </>
              )}
            </Section>

            {/* ── Datasets ── */}
            <Section title="Datasets" count={datasets.length} defaultOpen={datasets.length > 0}>
              {datasets.length === 0 ? (
                <p className="text-xs text-gray-400 py-2">
                  Nenhum dataset encontrado. Crie um dataset na etapa de Limpeza.
                </p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left">
                      <thead>
                        <tr>
                          <th className={TH_CLS}>Nome</th>
                          <th className={TH_CLS}>Critérios</th>
                          <th className={TH_CLS}>Usuários selecionados</th>
                          <th className={TH_CLS}>Criado em</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {datasets.map((ds) => (
                          <tr
                            key={ds.dataset_id}
                            className={`cursor-pointer transition-colors ${selectedDs === ds.dataset_id ? "bg-davint-50" : "hover:bg-gray-50"}`}
                            onClick={() => togglePanel(selectedDs, ds.dataset_id, setSelectedDs)}
                          >
                            <td className="py-2.5 pr-3 text-xs font-medium text-gray-800">
                              {ds.name}
                            </td>
                            <td className="py-2.5 pr-3">
                              <div className="flex flex-wrap gap-1">
                                {ds.criteria.map((c) => (
                                  <span
                                    key={c}
                                    className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-davint-50 text-davint-400"
                                  >
                                    {c}
                                  </span>
                                ))}
                              </div>
                            </td>
                            <td className="py-2.5 pr-3 text-xs text-gray-600">
                              {ds.total_selected}
                            </td>
                            <td className="py-2.5 pr-3 text-xs text-gray-500">
                              {new Date(ds.created_at).toLocaleDateString("pt-BR")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {selectedDs &&
                    (() => {
                      const ds = datasets.find((d) => d.dataset_id === selectedDs);
                      if (!ds) return null;
                      return (
                        <DatasetDetail
                          ds={ds}
                          onDownload={(fmt) =>
                            withErrorHandling(
                              () => downloadDataset(ds.dataset_id, fmt, ds.name),
                              "Erro ao baixar dataset."
                            )
                          }
                          onDelete={() => handleDeleteDataset(ds.dataset_id)}
                          onClose={() => setSelectedDs(null)}
                        />
                      );
                    })()}
                </>
              )}
            </Section>

            {/* ── Progresso de Anotação ── */}
            <Section
              title="Progresso de Anotação"
              count={annotations.length}
              defaultOpen={annotations.length > 0}
            >
              {annotations.length === 0 ? (
                <p className="text-xs text-gray-400 py-2">
                  Nenhuma anotação encontrada. Comece a anotar na etapa de Anotação.
                </p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left">
                      <thead>
                        <tr>
                          <th className={TH_CLS}>Dataset</th>
                          <th className={TH_CLS}>Progresso</th>
                          <th className={TH_CLS}>Conflitos</th>
                          <th className={TH_CLS}>Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {annotations.map((ann) => {
                          const isComplete =
                            ann.total > 0 &&
                            ann.pending === 0 &&
                            ann.conflicts === ann.conflicts_resolved;
                          return (
                            <tr
                              key={ann.dataset_id}
                              className={`cursor-pointer transition-colors ${selectedAnn === ann.dataset_id ? "bg-davint-50" : "hover:bg-gray-50"}`}
                              onClick={() =>
                                togglePanel(selectedAnn, ann.dataset_id, setSelectedAnn)
                              }
                            >
                              <td className="py-2.5 pr-3 text-xs font-medium text-gray-800">
                                {ann.dataset_name}
                              </td>
                              <td className="py-2.5 pr-3 text-xs text-gray-600">
                                {ann.annotated}/{ann.total}
                              </td>
                              <td className="py-2.5 pr-3 text-xs text-gray-600">
                                {ann.conflicts_resolved}/{ann.conflicts}
                              </td>
                              <td className="py-2.5 pr-3">
                                <span
                                  className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                                    isComplete
                                      ? "bg-green-50 text-green-600"
                                      : "bg-yellow-50 text-yellow-600"
                                  }`}
                                >
                                  {isComplete ? "Concluído" : "Em andamento"}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  {selectedAnn &&
                    (() => {
                      const ann = annotations.find((a) => a.dataset_id === selectedAnn);
                      if (!ann) return null;
                      return (
                        <AnnotationDetail
                          ann={ann}
                          onExport={(fmt) =>
                            withErrorHandling(
                              () => exportAnnotations(ann.dataset_id, fmt),
                              "Erro ao exportar anotações."
                            )
                          }
                          onDelete={() => handleDeleteDataset(ann.dataset_id)}
                          onClose={() => setSelectedAnn(null)}
                        />
                      );
                    })()}
                </>
              )}
            </Section>

            {/* ── Dados para Treinamento ── */}
            <Section
              title="Dados para Treinamento"
              count={completedDatasets.length}
              defaultOpen={completedDatasets.length > 0}
            >
              {completedDatasets.length === 0 ? (
                <p className="text-xs text-gray-400 py-2">
                  Nenhum dataset pronto para exportar. Um dataset fica disponível aqui quando todos
                  os comentários forem anotados e todos os conflitos forem resolvidos.
                </p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left">
                      <thead>
                        <tr>
                          <th className={TH_CLS}>Dataset</th>
                          <th className={TH_CLS}>Comentários</th>
                          <th className={TH_CLS}>Bots detectados</th>
                          <th className={TH_CLS}>Anotadores</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {completedDatasets.map((ds) => (
                          <tr
                            key={ds.dataset_id}
                            className={`cursor-pointer transition-colors ${selectedTraining === ds.dataset_id ? "bg-davint-50" : "hover:bg-gray-50"}`}
                            onClick={() =>
                              togglePanel(selectedTraining, ds.dataset_id, setSelectedTraining)
                            }
                          >
                            <td className="py-2.5 pr-3 text-xs font-medium text-gray-800">
                              {ds.dataset_name}
                            </td>
                            <td className="py-2.5 pr-3 text-xs text-gray-600">{ds.total}</td>
                            <td className="py-2.5 pr-3 text-xs text-gray-600">
                              {ds.bots_users} usuários / {ds.bots_comments} comentários
                            </td>
                            <td className="py-2.5 pr-3 text-xs text-gray-600">
                              {ds.annotators_count}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {selectedTraining &&
                    (() => {
                      const ds = completedDatasets.find((d) => d.dataset_id === selectedTraining);
                      if (!ds) return null;
                      return (
                        <TrainingDetail
                          ds={ds}
                          onExport={(fmt) =>
                            withErrorHandling(
                              () => exportReview(ds.dataset_id, fmt),
                              "Erro ao exportar dataset final."
                            )
                          }
                          onDelete={() => handleDeleteDataset(ds.dataset_id)}
                          onClose={() => setSelectedTraining(null)}
                        />
                      );
                    })()}
                </>
              )}
            </Section>
          </>
        )}
      </main>

      {showChangePassword && (
        <ChangePasswordModal
          onClose={() => setShowChangePassword(false)}
          onSubmit={(currentPassword, newPassword) =>
            usersApi.changePassword(
              { current_password: currentPassword, new_password: newPassword },
              token!
            )
          }
        />
      )}
    </div>
  );
}
