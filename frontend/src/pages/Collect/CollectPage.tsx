import { FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { collectApi, ImportRequest } from "../../api/collect";
import { PageHeader } from "../../components/PageHeader";
import { ProgressBar } from "../../components/ProgressBar";
import { StepsCard } from "../../components/StepsCard";
import { StatusBadge } from "../../components/StatusBadge";
import { useAuthContext } from "../../contexts/AuthContext";
import { useCollect } from "./useCollect";

type Tab = "collect" | "import";

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return [h, m, s].map((v) => String(v).padStart(2, "0")).join(":");
}

function useElapsed(running: boolean): number {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!running) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
      startRef.current = null;
      setElapsed(0);
      return;
    }
    startRef.current = Date.now();
    const tick = () => {
      if (startRef.current) {
        setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
      }
    };
    intervalRef.current = setInterval(tick, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [running]);

  return elapsed;
}

function getDisplayStatus(
  status: string,
  enrichStatus: string | null,
  enrichPhase: "video" | "replies" | "channels" | null,
  enrichDone: boolean
): string {
  if (status === "completed") {
    if (enrichDone || enrichStatus === "done" || enrichStatus === null) {
      return "completed";
    }
    if (enrichPhase === "video") return "enriching_video";
    if (enrichPhase === "replies") return "enriching_replies";
    if (enrichPhase === "channels") return "enriching_channels";
    return "enriching";
  }
  return status;
}

export function CollectPage() {
  const { token } = useAuthContext();
  const navigate = useNavigate();
  const {
    loading,
    error,
    active,
    collections,
    isActivelyPolling,
    enrichPhase,
    enrichRemaining,
    enrichDone,
    importProgress,
    startCollection,
    resumeCollection,
    importCollection,
    deleteCollection,
    clearActive,
    restoreFromList,
  } = useCollect();

  // ─── Coletar via API ───────────────────────────────────────────────
  const [tab, setTab] = useState<Tab>("collect");
  const [videoId, setVideoId] = useState("");
  const [apiKey, setApiKey] = useState("");

  // ─── Retomar coleta interrompida ────────────────────────────────────
  const [resumeApiKey, setResumeApiKey] = useState("");

  // ─── Importar JSON ─────────────────────────────────────────────────
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importParseError, setImportParseError] = useState<string | null>(null);

  // ─── Download ──────────────────────────────────────────────────────
  const [downloadState, setDownloadState] = useState<{
    id: string;
    format: "json" | "csv";
    percent: number;
  } | null>(null);

  const isRunning = active !== null && (active.status === "running" || active.status === "pending");
  const isInterrupted = isRunning && !isActivelyPolling;

  const isEnriching = active?.status === "completed" && !enrichDone && isActivelyPolling;
  const isEnrichInterrupted =
    active?.status === "completed" &&
    !enrichDone &&
    !isActivelyPolling &&
    (active?.enrich_status === "pending" || active?.enrich_status === "enriching");
  const isFullyDone =
    active?.status === "completed" &&
    (enrichDone || active?.enrich_status === "done" || active?.enrich_status === null);

  const elapsed = useElapsed(isActivelyPolling);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!videoId.trim() || !apiKey.trim()) return;
    void startCollection(videoId.trim(), apiKey);
    setApiKey("");
  }

  function handleImport(e: FormEvent) {
    e.preventDefault();
    if (!importFile) return;
    setImportParseError(null);

    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target?.result as string) as unknown;
        if (
          typeof parsed !== "object" ||
          parsed === null ||
          !("video" in parsed) ||
          !("comments" in parsed)
        ) {
          setImportParseError(
            'O arquivo deve conter as chaves "video" e "comments" no formato exportado pela plataforma.'
          );
          return;
        }
        const data = parsed as ImportRequest;
        if (!data.video?.id) {
          setImportParseError('Campo "video.id" ausente ou inválido.');
          return;
        }
        if (!Array.isArray(data.comments) || data.comments.length === 0) {
          setImportParseError('Campo "comments" ausente ou vazio.');
          return;
        }
        void importCollection(data);
      } catch {
        setImportParseError("Arquivo JSON inválido.");
      }
    };
    reader.readAsText(importFile);
  }

  function handleResume(e: FormEvent) {
    e.preventDefault();
    if (!resumeApiKey.trim()) return;
    void resumeCollection(resumeApiKey.trim());
    setResumeApiKey("");
  }

  function handleNewCollection() {
    clearActive();
    setVideoId("");
    setApiKey("");
    setImportFile(null);
    setImportParseError(null);
    setResumeApiKey("");
  }

  async function handleDownload(collectionId: string, format: "json" | "csv", videoId: string) {
    if (!token) return;
    setDownloadState({ id: collectionId, format, percent: 0 });
    try {
      await collectApi.downloadExport(collectionId, format, token, videoId, (percent) =>
        setDownloadState({ id: collectionId, format, percent })
      );
    } catch {
      // silently ignore download errors
    } finally {
      setDownloadState(null);
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <PageHeader breadcrumbs={[{ label: "Início", to: "/" }, { label: "Coletar Comentários" }]} />

      {/* Main */}
      <main className="flex-1 px-8 py-9 max-w-6xl w-full mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-800 tracking-tight mb-1">
            Coletar Comentários
          </h1>
          <p className="text-sm text-gray-500">
            Colete via YouTube Data API ou importe um arquivo JSON.
          </p>
        </div>

        {/* Tabs */}
        {!active && (
          <div className="flex gap-1 mb-4 border-b border-gray-200">
            <button
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                tab === "collect"
                  ? "border-davint-400 text-davint-500"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
              onClick={() => setTab("collect")}
            >
              Coletar via API
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
        )}

        {/* Form — Coletar via API */}
        {!active && tab === "collect" && (
          <>
            <StepsCard
              title="Passo a passo"
              steps={[
                {
                  label: "Obtenha uma API Key do YouTube",
                  description:
                    'No Google Cloud Console, crie um projeto, habilite "YouTube Data API v3" e gere uma chave de API.',
                },
                {
                  label: "Informe o ID ou URL do vídeo",
                  description:
                    "O ID é o código de 11 caracteres na URL (ex: dQw4w9WgXcQ em youtube.com/watch?v=dQw4w9WgXcQ).",
                },
                {
                  label: "Informe sua API Key",
                  description:
                    "A chave é usada apenas nesta sessão e não é armazenada no banco de dados.",
                },
                {
                  label: "Aguarde nesta página",
                  description:
                    "A coleta processa 100 comentários por vez. Se navegar para outra tela, ela pausa — mas os dados são preservados e você pode retomá-la aqui.",
                },
              ]}
            />
            <div className="flex items-start gap-2.5 p-4 bg-yellow-50 border border-yellow-200 rounded-xl mb-6">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 16 16"
                fill="currentColor"
                className="w-5 h-5 text-yellow-500 shrink-0 mt-0.5"
              >
                <path
                  fillRule="evenodd"
                  d="M6.701 2.25c.577-1 2.02-1 2.598 0l5.196 9a1.5 1.5 0 0 1-1.299 2.25H2.804a1.5 1.5 0 0 1-1.3-2.25l5.197-9ZM8 4a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
                  clipRule="evenodd"
                />
              </svg>
              <div className="text-sm text-yellow-700">
                <p className="font-semibold">
                  Você precisa de uma API key pessoal e intransferível
                </p>
                <p className="mt-1 text-xs">
                  Crie sua chave em{" "}
                  <a
                    href="https://console.cloud.google.com/apis/credentials"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline font-medium"
                  >
                    Google Cloud Console
                  </a>{" "}
                  com a <strong>YouTube Data API v3</strong> habilitada. Cada pesquisador deve ter
                  sua própria chave — não compartilhe entre colegas. A chave não é armazenada pela
                  plataforma.
                </p>
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
              <form onSubmit={handleSubmit} className="flex flex-col gap-5">
                <div className="form-group">
                  <label className="form-label" htmlFor="video_id">
                    ID ou URL do vídeo
                  </label>
                  <input
                    id="video_id"
                    className="form-input"
                    type="text"
                    placeholder="dQw4w9WgXcQ ou https://youtube.com/watch?v=..."
                    value={videoId}
                    onChange={(e) => setVideoId(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="api_key">
                    API Key do YouTube
                  </label>
                  <input
                    id="api_key"
                    className="form-input"
                    type="password"
                    autoComplete="new-password"
                    placeholder="AIza..."
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    required
                    disabled={loading}
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    A chave é usada apenas durante esta coleta e descartada em seguida.
                  </p>
                </div>

                {error && <div className="alert alert-error">{error}</div>}

                <button
                  type="submit"
                  className="btn btn-primary btn-full"
                  disabled={loading || !videoId.trim() || !apiKey.trim()}
                >
                  {loading ? "Iniciando…" : "Iniciar Coleta"}
                </button>
              </form>
            </div>
          </>
        )}

        {/* Form — Importar JSON */}
        {!active && tab === "import" && (
          <>
            <div className="bg-davint-50 rounded-xl p-5 mb-6">
              <h3 className="text-xs font-bold uppercase tracking-wider text-davint-600 mb-3">
                Formato esperado
              </h3>
              <p className="text-xs text-gray-600 mb-3">
                O arquivo deve ser um JSON no formato exportado pela plataforma, com as chaves{" "}
                <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
                  video
                </code>{" "}
                (metadados do vídeo) e{" "}
                <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-gray-200 text-[11px]">
                  comments
                </code>{" "}
                (array de comentários e replies).
              </p>
              <details className="mb-3">
                <summary className="text-xs font-semibold text-davint-600 cursor-pointer hover:text-davint-700">
                  Ver exemplo de JSON
                </summary>
                <pre className="text-[11px] font-mono bg-white border border-gray-200 rounded-lg p-3 text-gray-600 overflow-auto mt-2 leading-relaxed max-h-80">{`{
  "video": {
    "id": "dQw4w9WgXcQ",
    "title": "Never Gonna Give You Up",
    "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
    "channel_title": "Rick Astley",
    "published_at": "2009-10-25T06:57:33",
    "view_count": 1400000000,
    "like_count": 16000000,
    "comment_count": 2500000
  },
  "comments": [
    {
      "comment_id": "Ugxabc123",
      "parent_id": null,
      "author_display_name": "Maria",
      "author_channel_id": "UCxxx",
      "author_channel_published_at": "2012-04-14T14:27:48",
      "author_profile_image_url": "https://...",
      "author_channel_url": "http://www.youtube.com/@Maria",
      "text_original": "Ótimo vídeo!",
      "text_display": "Ótimo vídeo!",
      "like_count": 5,
      "reply_count": 1,
      "published_at": "2024-01-15T10:00:00",
      "updated_at": "2024-01-15T10:00:00"
    },
    {
      "comment_id": "Ugxabc123.reply1",
      "parent_id": "Ugxabc123",
      "author_display_name": "João",
      "author_channel_id": "UCyyy",
      "author_channel_published_at": "2015-08-20T09:15:00",
      "text_original": "Concordo!",
      "text_display": "Concordo!",
      "like_count": 0,
      "reply_count": 0,
      "published_at": "2024-01-15T12:00:00",
      "updated_at": "2024-01-15T12:00:00"
    }
  ]
}`}</pre>
              </details>
              <p className="text-xs text-gray-400">
                Este é o mesmo formato gerado pelo botão de exportação JSON. Coletas exportadas
                podem ser reimportadas diretamente.
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
              <form onSubmit={handleImport} className="flex flex-col gap-5">
                <div className="form-group">
                  <label className="form-label" htmlFor="import_file">
                    Arquivo JSON
                  </label>
                  <input
                    id="import_file"
                    className="form-input"
                    type="file"
                    accept=".json"
                    onChange={(e) => setImportFile(e.target.files?.[0] ?? null)}
                    required
                    disabled={loading}
                  />
                </div>

                {importParseError && <div className="alert alert-error">{importParseError}</div>}
                {error && <div className="alert alert-error">{error}</div>}

                {importProgress && (
                  <div className="flex flex-col gap-1.5">
                    <ProgressBar
                      percent={Math.round((importProgress.sent / importProgress.total) * 100)}
                      label={`${importProgress.sent.toLocaleString("pt-BR")} / ${importProgress.total.toLocaleString("pt-BR")} comentários`}
                    />
                  </div>
                )}

                <button
                  type="submit"
                  className="btn btn-primary btn-full"
                  disabled={loading || !importFile}
                >
                  {loading
                    ? importProgress
                      ? "Importando…"
                      : "Lendo arquivo…"
                    : "Importar Comentários"}
                </button>
              </form>
            </div>
          </>
        )}

        {/* Progress / Result */}
        {active && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
            <div className="flex items-start justify-between mb-4">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-1">
                  Vídeo
                </p>
                <p className="text-base font-mono font-semibold text-gray-800">{active.video_id}</p>
              </div>
              <StatusBadge
                status={getDisplayStatus(
                  active.status,
                  active.enrich_status,
                  enrichPhase,
                  enrichDone
                )}
              />
            </div>

            {/* Coletando ativamente */}
            {isRunning && !isInterrupted && (
              <>
                <div className="flex items-center gap-3 mb-3">
                  <svg
                    className="animate-spin h-5 w-5 text-davint-400 shrink-0"
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
                  <div>
                    <p className="text-sm font-medium text-gray-700">
                      Coletando comentários (100 por página)…
                    </p>
                    {active.total_comments != null && active.total_comments > 0 && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        {active.total_comments.toLocaleString("pt-BR")} coletados até agora
                        {isActivelyPolling && ` · ${formatDuration(elapsed)}`}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-start gap-2 p-3 bg-davint-50 rounded-lg mb-4">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    className="w-4 h-4 text-davint-500 shrink-0 mt-0.5"
                  >
                    <path
                      fillRule="evenodd"
                      d="M15 8A7 7 0 1 1 1 8a7 7 0 0 1 14 0ZM9 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM6.75 8a.75.75 0 0 0 0 1.5h.75v1.75a.75.75 0 0 0 1.5 0v-2.5A.75.75 0 0 0 8.25 8h-1.5Z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <p className="text-xs text-davint-700">
                    Aguarde nesta página enquanto a coleta estiver em andamento. Se navegar para
                    outra tela, a coleta pausa — mas os dados coletados são preservados e você pode
                    retomá-la aqui.
                  </p>
                </div>
              </>
            )}

            {/* Coleta interrompida — navegou para outra página e voltou */}
            {isInterrupted && (
              <div className="mb-4">
                <div className="flex items-start gap-3 mb-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    className="w-4 h-4 text-yellow-500 shrink-0 mt-0.5"
                  >
                    <path
                      fillRule="evenodd"
                      d="M6.701 2.25c.577-1 2.02-1 2.598 0l5.196 9a1.5 1.5 0 0 1-1.299 2.25H2.804a1.5 1.5 0 0 1-1.3-2.25l5.197-9ZM8 4a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div>
                    <p className="text-sm font-semibold text-yellow-800">Coleta interrompida</p>
                    <p className="text-xs text-yellow-700 mt-1">
                      Você navegou para outra página enquanto a coleta estava em andamento. Os dados
                      coletados estão preservados no banco.
                    </p>
                    {active.total_comments != null && active.total_comments > 0 && (
                      <p className="text-xs font-medium text-yellow-700 mt-1">
                        {active.total_comments.toLocaleString("pt-BR")} comentários salvos até a
                        interrupção.
                      </p>
                    )}
                    <p className="text-xs text-yellow-700 mt-1">
                      Para continuar de onde parou, informe a API key abaixo — a coleta retomará da
                      última página salva.
                    </p>
                  </div>
                </div>
                <form onSubmit={handleResume} className="flex gap-2">
                  <input
                    className="form-input flex-1"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Informe a API key para continuar (AIza…)"
                    value={resumeApiKey}
                    onChange={(e) => setResumeApiKey(e.target.value)}
                    disabled={loading}
                    required
                  />
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading || !resumeApiKey.trim()}
                  >
                    {loading ? "Retomando…" : "Continuar"}
                  </button>
                </form>
                {error && <div className="alert alert-error mt-3">{error}</div>}
              </div>
            )}

            {/* Enriquecendo — replies extras e dados dos canais */}
            {isEnriching && (
              <div className="flex flex-col gap-3">
                <p className="text-sm text-gray-600">
                  <span className="font-semibold text-gray-800">{active.total_comments ?? 0}</span>{" "}
                  comentários coletados. Enriquecendo dados...
                  <span className="text-xs text-gray-400 ml-2">{formatDuration(elapsed)}</span>
                </p>
                <div className="flex items-center gap-3">
                  <svg
                    className="animate-spin h-5 w-5 text-davint-400 shrink-0"
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
                  <div>
                    <p className="text-sm font-medium text-gray-700">
                      {enrichPhase === "video"
                        ? "Etapa 1/3 — Obtendo título, canal e estatísticas do vídeo..."
                        : enrichPhase === "replies"
                          ? "Etapa 2/3 — Coletando respostas (replies) dos comentários..."
                          : "Etapa 3/3 — Obtendo data de criação da conta de cada autor..."}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {enrichPhase === "video"
                        ? "Uma única chamada à API do YouTube."
                        : enrichPhase === "replies"
                          ? `${enrichRemaining} comentários com respostas extras a coletar. Cada lote busca até 20 threads.`
                          : `${enrichRemaining} autores sem data de criação. Cada lote consulta até 200 canais.`}
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-2 p-3 bg-davint-50 rounded-lg">
                  <p className="text-xs text-davint-600">
                    Aguarde nesta página. Se navegar para outra tela, o enriquecimento pausa — mas
                    os dados já coletados são preservados.
                  </p>
                </div>
              </div>
            )}

            {/* Enrich interrompido — precisa de API key para retomar */}
            {isEnrichInterrupted && (
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-3">
                  <span className="font-semibold text-gray-800">{active.total_comments ?? 0}</span>{" "}
                  comentários coletados. O enriquecimento foi interrompido.
                </p>
                <div className="flex items-start gap-3 mb-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    className="w-4 h-4 text-yellow-500 shrink-0 mt-0.5"
                  >
                    <path
                      fillRule="evenodd"
                      d="M6.701 2.25c.577-1 2.02-1 2.598 0l5.196 9a1.5 1.5 0 0 1-1.299 2.25H2.804a1.5 1.5 0 0 1-1.3-2.25l5.197-9ZM8 4a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div>
                    <p className="text-sm font-semibold text-yellow-800">
                      Enriquecimento interrompido
                    </p>
                    <p className="text-xs text-yellow-700 mt-1">
                      Os comentários foram coletados, mas faltam respostas extras e/ou datas de
                      criação dos canais. Informe a API key para retomar.
                    </p>
                  </div>
                </div>
                <form onSubmit={handleResume} className="flex gap-2">
                  <input
                    className="form-input flex-1"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Informe a API key para continuar (AIza…)"
                    value={resumeApiKey}
                    onChange={(e) => setResumeApiKey(e.target.value)}
                    disabled={loading}
                    required
                  />
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading || !resumeApiKey.trim()}
                  >
                    Continuar
                  </button>
                </form>
                {error && <div className="alert alert-error mt-3">{error}</div>}
              </div>
            )}

            {/* Totalmente concluído */}
            {isFullyDone && (
              <div className="flex flex-col gap-3">
                <p className="text-sm text-gray-600">
                  <span className="font-semibold text-gray-800">{active.total_comments ?? 0}</span>{" "}
                  comentários coletados com sucesso.
                  {active.duration_seconds != null && (
                    <span className="text-xs text-gray-400 ml-2">
                      Duração: {formatDuration(active.duration_seconds)}
                    </span>
                  )}
                </p>
                {active.channel_dates_failed === true && (
                  <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 16 16"
                      fill="currentColor"
                      className="w-4 h-4 text-yellow-500 shrink-0 mt-0.5"
                    >
                      <path
                        fillRule="evenodd"
                        d="M6.701 2.25c.577-1 2.02-1 2.598 0l5.196 9a1.5 1.5 0 0 1-1.299 2.25H2.804a1.5 1.5 0 0 1-1.3-2.25l5.197-9ZM8 4a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <p className="text-xs text-yellow-700">
                      Não foi possível obter as datas de criação dos canais dos autores. Os demais
                      dados foram coletados normalmente.
                    </p>
                  </div>
                )}
                {active.channel_dates_failed === false && (
                  <p className="text-xs text-green-600">
                    Dados dos autores e respostas coletados com sucesso.
                  </p>
                )}
                <div className="flex gap-3">
                  <button className="btn btn-primary" onClick={() => navigate("/clean")}>
                    Ir para Limpeza →
                  </button>
                  <button className="btn btn-ghost" onClick={handleNewCollection}>
                    Nova Coleta
                  </button>
                </div>
              </div>
            )}

            {active.status === "failed" && (
              <div className="flex flex-col gap-3">
                {error && <div className="alert alert-error">{error}</div>}
                <button className="btn btn-ghost" onClick={handleNewCollection}>
                  Tentar novamente
                </button>
              </div>
            )}
          </div>
        )}

        {/* Collections list */}
        {collections.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-700">Coletas realizadas</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="text-left py-2.5 px-6 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                      Vídeo
                    </th>
                    <th className="text-left py-2.5 pr-4 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                      Status
                    </th>
                    <th className="text-left py-2.5 pr-4 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                      Comentários
                    </th>
                    <th className="text-left py-2.5 pr-4 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                      Duração
                    </th>
                    <th className="text-left py-2.5 pr-4 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                      Concluída em
                    </th>
                    <th className="text-left py-2.5 pr-4 text-[11px] font-bold uppercase tracking-wider text-gray-400">
                      Exportar
                    </th>
                    <th className="text-right py-2.5 pr-6 text-[11px] font-bold uppercase tracking-wider text-gray-400"></th>
                  </tr>
                </thead>
                <tbody className="px-6">
                  {collections.map((col) => (
                    <tr key={col.collection_id} className="border-b border-gray-100 last:border-0">
                      <td className="py-3 pl-6 pr-4 max-w-[280px]">
                        {col.video_title && (
                          <p className="text-sm font-medium text-gray-800 line-clamp-2">
                            {col.video_title}
                          </p>
                        )}
                        <p className="text-xs font-mono text-gray-400">{col.video_id}</p>
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge
                          status={getDisplayStatus(
                            col.status,
                            col.enrich_status,
                            null,
                            col.enrich_status === "done" || col.enrich_status === null
                          )}
                          size="sm"
                        />
                      </td>
                      <td className="py-3 pr-4 text-sm text-gray-600">
                        {col.total_comments ?? "—"}
                      </td>
                      <td className="py-3 pr-4 text-sm text-gray-500">
                        {col.duration_seconds != null ? formatDuration(col.duration_seconds) : "—"}
                      </td>
                      <td className="py-3 pr-4 text-sm text-gray-500">
                        {col.collected_at
                          ? new Date(col.collected_at).toLocaleString("pt-BR", {
                              timeZone: "America/Sao_Paulo",
                            })
                          : "—"}
                      </td>
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-3">
                          {(col.status === "running" ||
                            (col.status === "completed" &&
                              col.enrich_status !== "done" &&
                              col.enrich_status !== null)) &&
                            col.collection_id !== active?.collection_id && (
                              <button
                                className="text-xs font-medium text-davint-400 hover:text-davint-500 hover:underline transition-colors"
                                onClick={() => void restoreFromList(col.collection_id)}
                              >
                                Retomar
                              </button>
                            )}
                          {col.status === "completed" &&
                            (downloadState?.id === col.collection_id ? (
                              <div className="w-20">
                                <ProgressBar
                                  percent={downloadState.percent}
                                  size="sm"
                                  label={`${downloadState.percent}%`}
                                />
                              </div>
                            ) : (
                              <>
                                <button
                                  className="text-xs font-medium text-davint-400 hover:text-davint-500 hover:underline transition-colors"
                                  onClick={() =>
                                    void handleDownload(col.collection_id, "json", col.video_id)
                                  }
                                >
                                  JSON
                                </button>
                                <button
                                  className="text-xs font-medium text-davint-400 hover:text-davint-500 hover:underline transition-colors"
                                  onClick={() =>
                                    void handleDownload(col.collection_id, "csv", col.video_id)
                                  }
                                >
                                  CSV
                                </button>
                              </>
                            ))}
                        </div>
                      </td>
                      <td className="py-3 pr-6 text-right">
                        {col.status !== "running" &&
                          col.status !== "importing" &&
                          !(isActivelyPolling && col.collection_id === active?.collection_id) && (
                            <button
                              className="text-xs font-medium text-red-400 hover:text-red-600 transition-colors"
                              onClick={() => {
                                if (
                                  window.confirm(
                                    `Deletar a coleta "${col.video_title ?? col.video_id}"?\n\nEsta ação remove todos os comentários e não pode ser desfeita.`
                                  )
                                ) {
                                  void deleteCollection(col.collection_id);
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
                          )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
