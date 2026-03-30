import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { collectApi, CollectionSummary } from "../../api/collect";
import { PageHeader } from "../../components/PageHeader";
import { StepsCard } from "../../components/StepsCard";
import { useAuthContext } from "../../contexts/AuthContext";
import { useClean } from "../../hooks/useClean";
import { CriteriaGroup1 } from "./CriteriaGroup1";
import { CriteriaGroup2 } from "./CriteriaGroup2";
import { DatasetList } from "./DatasetList";
import { PreviewPanel } from "./PreviewPanel";

const CRITERIA_ORDER = [
  "percentil",
  "media",
  "moda",
  "mediana",
  "curtos",
  "intervalo",
  "identicos",
  "perfil",
];

function buildDatasetName(videoId: string, criteria: string[]): string {
  const active = CRITERIA_ORDER.filter((c) => criteria.includes(c));
  return active.length > 0 ? `${videoId}_${active.join("_")}` : "";
}

type Tab = "create" | "import";

export function CleanPage() {
  const { token } = useAuthContext();

  // ─── State ──────────────────────────────────────────────────────────
  const [tab, setTab] = useState<Tab>("create");
  const [collections, setCollections] = useState<CollectionSummary[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState("");
  const [selectedCriteria, setSelectedCriteria] = useState<Set<string>>(new Set());
  const [thresholdChars, setThresholdChars] = useState(20);
  const [thresholdSeconds, setThresholdSeconds] = useState(30);

  const {
    loading,
    error,
    preview,
    datasets,
    createdDataset,
    clearError,
    clearPreview,
    fetchPreview,
    createDataset,
    fetchDatasets,
    downloadDataset,
    importDataset,
    deleteDataset,
  } = useClean();

  // ─── Import state ───────────────────────────────────────────────────
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importParseError, setImportParseError] = useState<string | null>(null);

  // ─── Load collections on mount ──────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    collectApi.list(token).then((cols) => {
      const completed = cols.filter(
        (c) => c.status === "completed" && (c.enrich_status === "done" || c.enrich_status === null)
      );
      setCollections(completed);
    });
  }, [token]);

  // ─── Load datasets on mount ─────────────────────────────────────────
  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  // ─── Derived ────────────────────────────────────────────────────────
  const selectedCollection = collections.find((c) => c.collection_id === selectedCollectionId);
  const criteriaArray = useMemo(
    () => CRITERIA_ORDER.filter((c) => selectedCriteria.has(c)),
    [selectedCriteria]
  );
  const datasetName = useMemo(
    () => (selectedCollection ? buildDatasetName(selectedCollection.video_id, criteriaArray) : ""),
    [selectedCollection, criteriaArray]
  );

  // ─── Handlers ───────────────────────────────────────────────────────
  const toggleCriteria = useCallback(
    (id: string) => {
      clearPreview();
      setSelectedCriteria((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
    },
    [clearPreview]
  );

  const handlePreview = useCallback(() => {
    if (!selectedCollectionId || criteriaArray.length === 0) return;
    clearError();
    fetchPreview(selectedCollectionId, criteriaArray, {
      threshold_chars: thresholdChars,
      threshold_seconds: thresholdSeconds,
    });
  }, [
    selectedCollectionId,
    criteriaArray,
    thresholdChars,
    thresholdSeconds,
    clearError,
    fetchPreview,
  ]);

  const handleCreate = useCallback(async () => {
    if (!selectedCollectionId || criteriaArray.length === 0) return;
    clearError();
    await createDataset({
      collection_id: selectedCollectionId,
      criteria: criteriaArray,
      thresholds: {
        threshold_chars: thresholdChars,
        threshold_seconds: thresholdSeconds,
      },
    });
    fetchDatasets();
  }, [
    selectedCollectionId,
    criteriaArray,
    thresholdChars,
    thresholdSeconds,
    clearError,
    createDataset,
    fetchDatasets,
  ]);

  const handleCollectionChange = useCallback(
    (id: string) => {
      setSelectedCollectionId(id);
      setSelectedCriteria(new Set());
      clearPreview();
    },
    [clearPreview]
  );

  // ─── Validação ──────────────────────────────────────────────────────
  const handleImportDataset = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      if (!importFile) return;
      setImportParseError(null);

      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const parsed = JSON.parse(ev.target?.result as string) as {
            dataset?: { name?: string; video_id?: string; criteria_applied?: string[] };
            users?: Array<{
              author_channel_id: string;
              author_display_name?: string;
              comment_count?: number;
              matched_criteria?: string[];
            }>;
          };
          if (!parsed.dataset?.name || !parsed.dataset?.video_id) {
            setImportParseError('O arquivo deve conter "dataset" com "name" e "video_id".');
            return;
          }
          if (!Array.isArray(parsed.users) || parsed.users.length === 0) {
            setImportParseError('O arquivo deve conter "users" (array não vazio).');
            return;
          }
          void (async () => {
            await importDataset({
              dataset: {
                name: parsed.dataset!.name!,
                video_id: parsed.dataset!.video_id!,
                criteria_applied: parsed.dataset!.criteria_applied ?? [],
              },
              users: parsed.users!.map((u) => ({
                author_channel_id: u.author_channel_id,
                author_display_name: u.author_display_name ?? "",
                comment_count: u.comment_count ?? 0,
                matched_criteria: u.matched_criteria ?? [],
              })),
            });
            fetchDatasets();
            setImportFile(null);
          })();
        } catch {
          setImportParseError("Arquivo JSON inválido.");
        }
      };
      reader.readAsText(importFile);
    },
    [importFile, importDataset, fetchDatasets]
  );

  const canPreview = selectedCollectionId !== "" && criteriaArray.length > 0;
  const canCreate =
    preview !== null &&
    (criteriaArray.length === 1
      ? (preview.by_criteria[criteriaArray[0]]?.selected_users ?? 0) > 0
      : preview.union_if_combined > 0);

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <PageHeader breadcrumbs={[{ label: "Início", to: "/" }, { label: "Limpeza e Seleção" }]} />

      <main className="flex-1 px-8 py-9 max-w-6xl w-full mx-auto">
        <h1 className="text-2xl font-bold text-gray-800 tracking-tight mb-1">
          Limpeza e Seleção de Dataset
        </h1>
        <p className="text-sm text-gray-500 mb-6">
          Aplique critérios estatísticos e comportamentais para identificar usuários suspeitos.
        </p>

        {/* Erro */}
        {error && (
          <div className="alert alert-error mb-4">
            {error}
            <button className="ml-2 text-xs font-semibold underline" onClick={clearError}>
              Fechar
            </button>
          </div>
        )}

        {/* Sucesso ao criar/importar */}
        {createdDataset && (
          <div className="flex items-start gap-2 p-3 bg-green-50 border border-green-200 rounded-lg mb-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <p className="text-sm font-semibold text-green-800">Dataset criado com sucesso!</p>
              <p className="text-xs text-green-700 mt-0.5">
                <span className="font-mono">{createdDataset.name}</span>
                {" — "}
                {createdDataset.total_users_selected} usuários selecionados de{" "}
                {createdDataset.total_users_original}.
              </p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-gray-200">
          <button
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === "create"
                ? "border-davint-400 text-davint-500"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
            onClick={() => setTab("create")}
          >
            Criar via critérios
          </button>
          <button
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === "import"
                ? "border-davint-400 text-davint-500"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
            onClick={() => setTab("import")}
          >
            Importar JSON
          </button>
        </div>

        {/* Tab — Criar via critérios */}
        {tab === "create" && (
          <>
            <StepsCard
              title="Passo a passo"
              steps={[
                {
                  label: "Selecione uma coleta concluída",
                  description: "Apenas coletas finalizadas e enriquecidas podem ser filtradas.",
                },
                {
                  label: "Escolha critérios de seleção",
                  description:
                    "Combine critérios estatísticos (volume) e comportamentais (padrões de postagem).",
                },
                {
                  label: "Visualize o preview",
                  description:
                    "Confira quantos usuários cada critério seleciona antes de confirmar.",
                },
                {
                  label: "Crie o dataset",
                  description:
                    "Persista os usuários selecionados para análise nas próximas etapas.",
                },
              ]}
            />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              <div className="lg:col-span-2 flex flex-col gap-6">
                <div>
                  <label className="form-group">
                    <span className="form-label">Coleta</span>
                    <select
                      className="form-input"
                      value={selectedCollectionId}
                      onChange={(e) => handleCollectionChange(e.target.value)}
                    >
                      <option value="">Selecione uma coleta concluída...</option>
                      {collections.map((c) => (
                        <option key={c.collection_id} value={c.collection_id}>
                          {c.video_id}
                          {c.video_title ? ` — ${c.video_title}` : ""}
                          {` (${c.total_comments ?? 0} comentários)`}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                {selectedCollectionId && (
                  <>
                    <CriteriaGroup1 selected={selectedCriteria} onToggle={toggleCriteria} />
                    <CriteriaGroup2
                      selected={selectedCriteria}
                      onToggle={toggleCriteria}
                      thresholdChars={thresholdChars}
                      thresholdSeconds={thresholdSeconds}
                      onThresholdCharsChange={setThresholdChars}
                      onThresholdSecondsChange={setThresholdSeconds}
                    />

                    <div className="flex flex-col gap-3">
                      <div className="flex gap-3">
                        <button
                          className="btn btn-primary"
                          disabled={!canPreview || loading}
                          onClick={handlePreview}
                        >
                          {loading && !preview ? "Calculando..." : "Visualizar preview"}
                        </button>
                        {preview && (
                          <button
                            className="btn btn-primary"
                            disabled={!canCreate || loading}
                            onClick={handleCreate}
                          >
                            {loading ? "Criando..." : "Criar Dataset"}
                          </button>
                        )}
                      </div>
                      {!preview && canPreview && (
                        <p className="text-xs text-gray-400">
                          Visualize o preview antes de criar o dataset.
                        </p>
                      )}
                    </div>
                  </>
                )}
              </div>

              <div>
                {preview && selectedCollection && (
                  <PreviewPanel
                    preview={preview}
                    datasetName={datasetName}
                    selectedCriteria={criteriaArray}
                  />
                )}
              </div>
            </div>
          </>
        )}

        {/* Tab — Importar JSON */}
        {tab === "import" && (
          <>
            <div className="bg-davint-50 rounded-xl p-5 mb-6">
              <h3 className="text-xs font-bold uppercase tracking-wider text-davint-600 mb-3">
                Formato esperado
              </h3>
              <p className="text-xs text-gray-600 mb-3">
                O arquivo deve ser um JSON no formato exportado pela plataforma, com as chaves{" "}
                <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
                  dataset
                </code>{" "}
                (com{" "}
                <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
                  name
                </code>{" "}
                e{" "}
                <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
                  video_id
                </code>
                ) e{" "}
                <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
                  users
                </code>{" "}
                (array de usuários selecionados).
              </p>
              <p className="text-xs text-gray-400">
                Este é o mesmo formato gerado pelo botão de exportação JSON. A coleta referenciada
                pelo <code className="font-mono">video_id</code> deve existir na plataforma.
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
              <form onSubmit={handleImportDataset} className="flex flex-col gap-5">
                <div className="form-group">
                  <label className="form-label" htmlFor="import_dataset">
                    Arquivo JSON
                  </label>
                  <input
                    id="import_dataset"
                    className="form-input"
                    type="file"
                    accept=".json"
                    onChange={(e) => {
                      setImportFile(e.target.files?.[0] ?? null);
                      setImportParseError(null);
                    }}
                    disabled={loading}
                  />
                </div>

                {importParseError && <div className="alert alert-error">{importParseError}</div>}

                <button
                  type="submit"
                  className="btn btn-primary btn-full"
                  disabled={loading || !importFile}
                >
                  {loading ? "Importando…" : "Importar Dataset"}
                </button>
              </form>
            </div>
          </>
        )}

        {/* Datasets existentes */}
        {datasets.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-700">Datasets criados</h2>
            </div>
            <DatasetList
              datasets={datasets}
              onDownload={downloadDataset}
              onDelete={deleteDataset}
            />
          </div>
        )}
      </main>
    </div>
  );
}
