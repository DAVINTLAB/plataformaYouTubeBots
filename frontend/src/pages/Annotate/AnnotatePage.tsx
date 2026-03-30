import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { cleanApi, DatasetSummary } from "../../api/clean";
import { PageHeader } from "../../components/PageHeader";
import { ProgressBar } from "../../components/ProgressBar";
import { StepsCard } from "../../components/StepsCard";
import { useAuthContext } from "../../contexts/AuthContext";
import { useAnnotate } from "../../hooks/useAnnotate";
import { UserCommentsList } from "./UserCommentsList";

type Tab = "annotate" | "import";

export function AnnotatePage() {
  const { token, isAdmin } = useAuthContext();

  // ─── State ──────────────────────────────────────────────────────────
  const [tab, setTab] = useState<Tab>("annotate");
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [usersPage, setUsersPage] = useState(0);
  const USERS_PER_PAGE = 20;

  const {
    loading,
    error,
    datasetUsers,
    userComments,
    progress,
    allProgress,
    importResult,
    clearError,
    clearImportResult,
    fetchDatasetUsers,
    fetchUserComments,
    submitAnnotation,
    fetchProgress,
    fetchAllProgress,
    importAnnotations,
    downloadExport,
  } = useAnnotate();

  // ─── Import state ───────────────────────────────────────────────────
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importParseError, setImportParseError] = useState<string | null>(null);

  // ─── Load datasets on mount ─────────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    cleanApi.list(token).then(setDatasets);
  }, [token]);

  // ─── Load progress on mount ─────────────────────────────────────────
  useEffect(() => {
    if (isAdmin) {
      fetchAllProgress();
    } else {
      fetchProgress();
    }
  }, [isAdmin, fetchProgress, fetchAllProgress]);

  // ─── Handlers ───────────────────────────────────────────────────────
  const handleSelectDataset = useCallback(
    (id: string) => {
      setSelectedDatasetId(id);
      setUsersPage(0);
      if (id) {
        fetchDatasetUsers(id);
      }
    },
    [fetchDatasetUsers]
  );

  const handleSelectUser = useCallback(
    (entryId: string) => {
      fetchUserComments(entryId);
    },
    [fetchUserComments]
  );

  const handleAnnotate = useCallback(
    async (commentDbId: string, label: "bot" | "humano", justificativa?: string | null) => {
      const result = await submitAnnotation(commentDbId, label, justificativa);
      if (result?.conflict_created) {
        setToast(
          "Conflito detectado: outro pesquisador classificou este comentário de forma diferente."
        );
        setTimeout(() => setToast(null), 5000);
      }
    },
    [submitAnnotation]
  );

  const handleBackToUsers = useCallback(() => {
    if (selectedDatasetId) {
      fetchDatasetUsers(selectedDatasetId);
    }
  }, [selectedDatasetId, fetchDatasetUsers]);

  const handleImport = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      if (!importFile) return;
      setImportParseError(null);

      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const parsed = JSON.parse(ev.target?.result as string) as {
            dataset_id?: string;
            dataset_name?: string;
            video_id?: string;
            annotations?: Array<{
              comment_db_id: string;
              label: "bot" | "humano";
              justificativa?: string | null;
            }>;
          };
          if (!Array.isArray(parsed.annotations) || parsed.annotations.length === 0) {
            setImportParseError('O arquivo deve conter "annotations" (array não vazio).');
            return;
          }
          void (async () => {
            await importAnnotations({
              dataset_id: parsed.dataset_id,
              dataset_name: parsed.dataset_name,
              video_id: parsed.video_id,
              annotations: parsed.annotations!,
            });
            setImportFile(null);
            fetchProgress();
          })();
        } catch {
          setImportParseError("Arquivo JSON inválido.");
        }
      };
      reader.readAsText(importFile);
    },
    [importFile, importAnnotations, fetchProgress]
  );

  // ─── Derived ────────────────────────────────────────────────────────
  const datasetProgress = progress.find((p) => p.dataset_id === selectedDatasetId);
  const globalPercent = datasetProgress ? datasetProgress.percent_complete : 0;

  const totalUsersPages = datasetUsers ? Math.ceil(datasetUsers.items.length / USERS_PER_PAGE) : 0;
  const paginatedUsers = useMemo(() => {
    if (!datasetUsers) return [];
    const start = usersPage * USERS_PER_PAGE;
    return datasetUsers.items.slice(start, start + USERS_PER_PAGE);
  }, [datasetUsers, usersPage]);

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <PageHeader breadcrumbs={[{ label: "Início", to: "/" }, { label: "Anotação" }]} />

      <main className="flex-1 px-8 py-9 max-w-6xl w-full mx-auto">
        <h1 className="text-2xl font-bold text-gray-800 tracking-tight mb-1">
          Anotação de Comentários
        </h1>
        <p className="text-sm text-gray-500 mb-6">
          Classifique cada comentário como bot ou humano. Veja todos os comentários do usuário para
          tomar uma decisão informada.
        </p>

        {/* Toast (conflito) */}
        {toast && (
          <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg mb-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
              />
            </svg>
            <p className="text-xs text-yellow-700">{toast}</p>
          </div>
        )}

        {/* Erro */}
        {error && (
          <div className="alert alert-error mb-4">
            {error}
            <button className="ml-2 text-xs font-semibold underline" onClick={clearError}>
              Fechar
            </button>
          </div>
        )}

        {/* Import result */}
        {importResult && (
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
              <p className="text-sm font-semibold text-green-800">Importação concluída!</p>
              <p className="text-xs text-green-700 mt-0.5">
                {importResult.imported} criadas, {importResult.updated} atualizadas,{" "}
                {importResult.skipped} ignoradas.
              </p>
              {importResult.errors.length > 0 && (
                <ul className="text-xs text-yellow-700 mt-1 list-disc list-inside">
                  {importResult.errors.slice(0, 5).map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                  {importResult.errors.length > 5 && (
                    <li>...e mais {importResult.errors.length - 5} erros.</li>
                  )}
                </ul>
              )}
              <button className="text-xs text-green-600 underline mt-1" onClick={clearImportResult}>
                Fechar
              </button>
            </div>
          </div>
        )}

        {/* Aviso admin */}
        {isAdmin && (
          <div className="flex items-start gap-2 p-3 bg-orange-50 border border-orange-200 rounded-lg mb-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
              />
            </svg>
            <p className="text-xs text-orange-700">
              <span className="font-semibold">Modo visualização.</span> Administradores podem
              consultar os comentários e o progresso dos datasets, mas não podem anotar. Use a etapa
              de Revisão para desempatar conflitos.
            </p>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-gray-200">
          <button
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === "annotate"
                ? "border-davint-400 text-davint-500"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
            onClick={() => setTab("annotate")}
          >
            {isAdmin ? "Visualizar" : "Anotar"}
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

        {/* Tab — Anotar */}
        {tab === "annotate" && (
          <>
            {/* Se está vendo comentários de um usuário */}
            {userComments ? (
              <UserCommentsList
                data={userComments}
                onAnnotate={handleAnnotate}
                onBack={handleBackToUsers}
                readOnly={isAdmin}
              />
            ) : (
              <>
                <StepsCard
                  title="Passo a passo"
                  steps={[
                    {
                      label: "Selecione um dataset",
                      description: "Escolha o dataset com os usuários suspeitos a serem anotados.",
                    },
                    {
                      label: "Escolha um usuário",
                      description: "Veja todos os comentários do usuário agrupados para contexto.",
                    },
                    {
                      label: "Classifique cada comentário",
                      description: 'Marque como "Bot" ou "Humano". Bot exige justificativa.',
                    },
                  ]}
                />

                {/* Seleção de dataset */}
                <div className="form-group mb-6">
                  <label className="form-label" htmlFor="select_dataset">
                    Dataset
                  </label>
                  <select
                    id="select_dataset"
                    className="form-input"
                    value={selectedDatasetId}
                    onChange={(e) => handleSelectDataset(e.target.value)}
                  >
                    <option value="">Selecione um dataset...</option>
                    {datasets.map((d) => (
                      <option key={d.dataset_id} value={d.dataset_id}>
                        {d.name} ({d.total_users_selected} usuários)
                      </option>
                    ))}
                  </select>
                </div>

                {/* Progresso global */}
                {datasetProgress && (
                  <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-semibold text-gray-700">Meu progresso</h3>
                      <span className="text-xs text-gray-500">
                        {datasetProgress.annotated}/{datasetProgress.total_comments} comentários
                      </span>
                    </div>
                    <ProgressBar
                      percent={globalPercent}
                      label={`${globalPercent}% — ${datasetProgress.bots} bots, ${datasetProgress.humans} humanos`}
                      size="sm"
                    />
                  </div>
                )}

                {/* Tabela de usuários */}
                {datasetUsers && (
                  <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                      <h2 className="text-sm font-semibold text-gray-700">Usuários do dataset</h2>
                      <div className="flex gap-2">
                        <button
                          className="text-xs font-medium text-davint-400 hover:underline"
                          onClick={() => downloadExport("json", selectedDatasetId)}
                        >
                          Exportar JSON
                        </button>
                        <button
                          className="text-xs font-medium text-davint-400 hover:underline"
                          onClick={() => downloadExport("csv", selectedDatasetId)}
                        >
                          Exportar CSV
                        </button>
                      </div>
                    </div>
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-100">
                          <th className="px-6 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-400">
                            Usuário
                          </th>
                          <th className="px-6 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-400">
                            Comentários
                          </th>
                          <th className="px-6 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-400">
                            Progresso
                          </th>
                          <th className="px-6 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-400">
                            Status
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedUsers.map((item) => {
                          const pct =
                            item.comment_count > 0
                              ? Math.round((item.my_annotated_count / item.comment_count) * 100)
                              : 0;
                          const done = item.my_pending_count === 0;
                          return (
                            <tr
                              key={item.entry_id}
                              className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
                              onClick={() => handleSelectUser(item.entry_id)}
                            >
                              <td className="px-6 py-3">
                                <p className="text-sm font-medium text-gray-800">
                                  {item.author_display_name}
                                </p>
                                <p className="text-[11px] text-gray-400 font-mono">
                                  {item.author_channel_id.slice(0, 20)}...
                                </p>
                              </td>
                              <td className="px-6 py-3 text-sm text-gray-600">
                                {item.comment_count}
                              </td>
                              <td className="px-6 py-3 w-36">
                                <ProgressBar percent={pct} size="sm" />
                                <span className="text-[10px] text-gray-400">
                                  {item.my_annotated_count}/{item.comment_count}
                                </span>
                              </td>
                              <td className="px-6 py-3">
                                <span
                                  className={[
                                    "text-[11px] font-semibold px-2.5 py-0.5 rounded-full",
                                    done
                                      ? "bg-green-50 text-green-600"
                                      : "bg-yellow-50 text-yellow-600",
                                  ].join(" ")}
                                >
                                  {done ? "Concluído" : `${item.my_pending_count} pendentes`}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>

                    {/* Paginação */}
                    {totalUsersPages > 1 && (
                      <div className="px-6 py-3 border-t border-gray-100 flex items-center justify-between">
                        <span className="text-xs text-gray-500">
                          {usersPage * USERS_PER_PAGE + 1}–
                          {Math.min((usersPage + 1) * USERS_PER_PAGE, datasetUsers.items.length)} de{" "}
                          {datasetUsers.items.length} usuários
                        </span>
                        <div className="flex gap-1.5">
                          <button
                            className="btn btn-ghost btn-sm"
                            disabled={usersPage === 0}
                            onClick={() => setUsersPage((p) => p - 1)}
                          >
                            Anterior
                          </button>
                          <button
                            className="btn btn-ghost btn-sm"
                            disabled={usersPage >= totalUsersPages - 1}
                            onClick={() => setUsersPage((p) => p + 1)}
                          >
                            Próxima
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {loading && !datasetUsers && selectedDatasetId && (
                  <div className="text-center py-8">
                    <ProgressBar indeterminate label="Carregando usuários..." />
                  </div>
                )}
              </>
            )}
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
                O arquivo deve ser um JSON no formato exportado pela plataforma, com a chave{" "}
                <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
                  annotations
                </code>{" "}
                contendo um array de objetos com{" "}
                <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
                  comment_db_id
                </code>
                ,{" "}
                <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
                  label
                </code>{" "}
                e opcionalmente{" "}
                <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
                  justificativa
                </code>
                .
              </p>
              <p className="text-xs text-gray-400">
                Este é o mesmo formato gerado pelo botão "Exportar JSON". Faz upsert: anotações
                existentes são atualizadas, novas são criadas.
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
              <form onSubmit={handleImport} className="flex flex-col gap-5">
                <div className="form-group">
                  <label className="form-label" htmlFor="import_annotations">
                    Arquivo JSON
                  </label>
                  <input
                    id="import_annotations"
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
                  {loading ? "Importando..." : "Importar Anotações"}
                </button>
              </form>
            </div>
          </>
        )}

        {/* Progresso — admin vê todos os anotadores, pesquisador vê o próprio */}
        {!userComments && (isAdmin ? allProgress.length > 0 : progress.length > 0) && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mt-6">
            <div className="px-6 py-4 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-700">
                {isAdmin ? "Progresso dos anotadores" : "Progresso geral"}
              </h2>
            </div>
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  {isAdmin && (
                    <th className="px-6 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-400">
                      Anotador
                    </th>
                  )}
                  <th className="px-6 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-400">
                    Dataset
                  </th>
                  <th className="px-6 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-400">
                    Anotados
                  </th>
                  <th className="px-6 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-400">
                    Bots
                  </th>
                  <th className="px-6 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-400">
                    Humanos
                  </th>
                  <th className="px-6 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-gray-400">
                    Progresso
                  </th>
                </tr>
              </thead>
              <tbody>
                {isAdmin
                  ? allProgress.map((p) => (
                      <tr
                        key={`${p.annotator_id}-${p.dataset_id}`}
                        className="border-b border-gray-50"
                      >
                        <td className="px-6 py-3 text-sm font-medium text-gray-800">
                          {p.annotator_name}
                        </td>
                        <td className="px-6 py-3 text-sm text-gray-600 font-mono">
                          {p.dataset_name}
                        </td>
                        <td className="px-6 py-3 text-sm text-gray-600">
                          {p.annotated}/{p.total_comments}
                        </td>
                        <td className="px-6 py-3">
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-red-50 text-red-600">
                            {p.bots}
                          </span>
                        </td>
                        <td className="px-6 py-3">
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-green-50 text-green-600">
                            {p.humans}
                          </span>
                        </td>
                        <td className="px-6 py-3 w-36">
                          <ProgressBar percent={p.percent_complete} size="sm" />
                          <span className="text-[10px] text-gray-400">{p.percent_complete}%</span>
                        </td>
                      </tr>
                    ))
                  : progress.map((p) => (
                      <tr key={p.dataset_id} className="border-b border-gray-50">
                        <td className="px-6 py-3 text-sm font-medium text-gray-800 font-mono">
                          {p.dataset_name}
                        </td>
                        <td className="px-6 py-3 text-sm text-gray-600">
                          {p.annotated}/{p.total_comments}
                        </td>
                        <td className="px-6 py-3">
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-red-50 text-red-600">
                            {p.bots}
                          </span>
                        </td>
                        <td className="px-6 py-3">
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-green-50 text-green-600">
                            {p.humans}
                          </span>
                        </td>
                        <td className="px-6 py-3 w-36">
                          <ProgressBar percent={p.percent_complete} size="sm" />
                          <span className="text-[10px] text-gray-400">{p.percent_complete}%</span>
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
