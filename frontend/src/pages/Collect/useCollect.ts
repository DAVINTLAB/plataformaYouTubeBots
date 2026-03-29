import { useCallback, useEffect, useRef, useState } from "react";
import {
  collectApi,
  CollectionStarted,
  CollectionSummary,
  EnrichResponse,
  ImportRequest,
} from "../../api/collect";
import { useAuthContext } from "../../contexts/AuthContext";

const STORAGE_KEY = "davint_active_collection_id";

interface CollectState {
  loading: boolean;
  error: string | null;
  active: CollectionStarted | null;
  collections: CollectionSummary[];
  isActivelyPolling: boolean;
  // Enrich progress
  enrichPhase: "video" | "replies" | "channels" | null;
  enrichRemaining: number;
  enrichDone: boolean;
}

export function useCollect() {
  const { token } = useAuthContext();
  const [state, setState] = useState<CollectState>({
    loading: false,
    error: null,
    active: null,
    collections: [],
    isActivelyPolling: false,
    enrichPhase: null,
    enrichRemaining: 0,
    enrichDone: false,
  });

  const apiKeyRef = useRef<string>("");
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const enrichPollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const restoreAttemptedRef = useRef(false);
  // Guard to prevent overlapping enrich calls
  const enrichingRef = useRef(false);

  const stopPolling = useCallback(() => {
    if (pollingRef.current !== null) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const stopEnrichPolling = useCallback(() => {
    if (enrichPollingRef.current !== null) {
      clearInterval(enrichPollingRef.current);
      enrichPollingRef.current = null;
    }
    enrichingRef.current = false;
  }, []);

  const stopAll = useCallback(() => {
    stopPolling();
    stopEnrichPolling();
    setState((s) => ({ ...s, isActivelyPolling: false }));
  }, [stopPolling, stopEnrichPolling]);

  const loadCollections = useCallback(async () => {
    if (!token) return;
    try {
      const list = await collectApi.list(token);
      setState((s) => ({ ...s, collections: list }));
    } catch {
      // silently ignore list reload errors
    }
  }, [token]);

  // ─── Enrich loop ────────────────────────────────────────────────────────

  const advanceEnrich = useCallback(
    async (collectionId: string) => {
      if (!token || enrichingRef.current) return;
      enrichingRef.current = true;
      try {
        const result: EnrichResponse = await collectApi.enrich(
          collectionId,
          apiKeyRef.current,
          token
        );
        setState((s) => ({
          ...s,
          enrichPhase: result.phase,
          enrichRemaining: result.remaining,
          enrichDone: result.done,
          active: s.active ? { ...s.active, total_comments: s.active.total_comments } : s.active,
        }));
        if (result.done) {
          stopEnrichPolling();
          setState((s) => ({ ...s, isActivelyPolling: false }));
          apiKeyRef.current = "";
          sessionStorage.removeItem(STORAGE_KEY);
          void loadCollections();
        }
      } catch (err) {
        stopEnrichPolling();
        setState((s) => ({
          ...s,
          isActivelyPolling: false,
          error: err instanceof Error ? err.message : "Erro ao enriquecer coleta.",
        }));
        apiKeyRef.current = "";
        void loadCollections();
      } finally {
        enrichingRef.current = false;
      }
    },
    [token, stopEnrichPolling, loadCollections]
  );

  const _startEnrichLoop = useCallback(
    (collectionId: string) => {
      // First call immediately
      void advanceEnrich(collectionId);
      enrichPollingRef.current = setInterval(() => {
        void advanceEnrich(collectionId);
      }, 3000);
      setState((s) => ({ ...s, isActivelyPolling: true }));
    },
    [advanceEnrich]
  );

  // ─── Collection page loop ──────────────────────────────────────────────

  const advanceCollection = useCallback(
    async (current: CollectionStarted) => {
      if (!token) return;
      if (!current.next_page_token) return;

      try {
        const next = await collectApi.nextPage(
          { collection_id: current.collection_id, api_key: apiKeyRef.current },
          token
        );
        setState((s) => ({ ...s, active: next }));

        if (next.status === "completed" || next.status === "failed") {
          stopPolling();
          if (next.status === "completed" && next.enrich_status === "pending") {
            // Transition to enrich loop
            _startEnrichLoop(next.collection_id);
          } else {
            setState((s) => ({ ...s, isActivelyPolling: false }));
            apiKeyRef.current = "";
            sessionStorage.removeItem(STORAGE_KEY);
            void loadCollections();
          }
        }
      } catch (err) {
        stopPolling();
        apiKeyRef.current = "";
        setState((s) => ({
          ...s,
          loading: false,
          isActivelyPolling: false,
          error: err instanceof Error ? err.message : "Erro ao continuar coleta.",
        }));
        void loadCollections();
      }
    },
    [token, stopPolling, loadCollections, _startEnrichLoop]
  );

  const pollStatus = useCallback(
    async (collectionId: string) => {
      if (!token) return;
      try {
        const status = await collectApi.getStatus(collectionId, token);
        setState((s) => ({
          ...s,
          active: s.active
            ? {
                ...s.active,
                status: status.status,
                total_comments: status.total_comments,
                enrich_status: status.enrich_status,
              }
            : s.active,
        }));
        if (status.status === "completed" || status.status === "failed") {
          stopPolling();
          if (
            status.status === "completed" &&
            (status.enrich_status === "pending" || status.enrich_status === "enriching")
          ) {
            _startEnrichLoop(collectionId);
          } else {
            setState((s) => ({ ...s, isActivelyPolling: false }));
            apiKeyRef.current = "";
            sessionStorage.removeItem(STORAGE_KEY);
            void loadCollections();
          }
        }
      } catch {
        stopPolling();
        setState((s) => ({ ...s, isActivelyPolling: false }));
      }
    },
    [token, stopPolling, loadCollections, _startEnrichLoop]
  );

  const _startPollingLoop = useCallback(
    (collectionId: string) => {
      pollingRef.current = setInterval(() => {
        setState((s) => {
          if (!s.active) return s;
          if (s.active.next_page_token) {
            void advanceCollection(s.active);
          } else {
            void pollStatus(collectionId);
          }
          return s;
        });
      }, 2000);
      setState((s) => ({ ...s, isActivelyPolling: true }));
    },
    [advanceCollection, pollStatus]
  );

  // ─── Public actions ────────────────────────────────────────────────────

  const startCollection = useCallback(
    async (videoId: string, apiKey: string) => {
      if (!token) return;
      setState((s) => ({
        ...s,
        loading: true,
        error: null,
        active: null,
        enrichPhase: null,
        enrichRemaining: 0,
        enrichDone: false,
      }));
      apiKeyRef.current = apiKey;

      try {
        await collectApi.warmup();
        const result = await collectApi.start({ video_id: videoId, api_key: apiKey }, token);
        sessionStorage.setItem(STORAGE_KEY, result.collection_id);
        setState((s) => ({ ...s, active: result, loading: false }));

        if (result.status === "completed") {
          if (result.enrich_status === "pending") {
            _startEnrichLoop(result.collection_id);
          } else {
            apiKeyRef.current = "";
            sessionStorage.removeItem(STORAGE_KEY);
            void loadCollections();
          }
          return;
        }
        if (result.status === "failed") {
          apiKeyRef.current = "";
          sessionStorage.removeItem(STORAGE_KEY);
          void loadCollections();
          return;
        }

        _startPollingLoop(result.collection_id);
      } catch (err) {
        apiKeyRef.current = "";
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao iniciar coleta.",
        }));
      }
    },
    [token, loadCollections, _startPollingLoop, _startEnrichLoop]
  );

  const resumeCollection = useCallback(
    async (apiKey: string) => {
      if (!token || !state.active) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      apiKeyRef.current = apiKey;

      const active = state.active;

      // If collection is completed but enrich pending → resume enrich
      if (
        active.status === "completed" &&
        (active.enrich_status === "pending" || active.enrich_status === "enriching")
      ) {
        setState((s) => ({ ...s, loading: false }));
        _startEnrichLoop(active.collection_id);
        return;
      }

      // Otherwise resume page collection
      try {
        await collectApi.warmup();
        const next = await collectApi.nextPage(
          { collection_id: active.collection_id, api_key: apiKey },
          token
        );
        setState((s) => ({ ...s, active: next, loading: false }));

        if (next.status === "completed") {
          if (next.enrich_status === "pending") {
            _startEnrichLoop(next.collection_id);
          } else {
            apiKeyRef.current = "";
            sessionStorage.removeItem(STORAGE_KEY);
            void loadCollections();
          }
          return;
        }
        if (next.status === "failed") {
          apiKeyRef.current = "";
          sessionStorage.removeItem(STORAGE_KEY);
          void loadCollections();
          return;
        }

        _startPollingLoop(next.collection_id);
      } catch (err) {
        apiKeyRef.current = "";
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao retomar coleta.",
        }));
      }
    },
    [token, state.active, loadCollections, _startPollingLoop, _startEnrichLoop]
  );

  const importCollectionFn = useCallback(
    async (data: ImportRequest) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null, active: null }));
      try {
        const result = await collectApi.importCollection(data, token);
        setState((s) => ({
          ...s,
          active: result,
          loading: false,
          enrichDone: true,
        }));
        void loadCollections();
      } catch (err) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao importar arquivo.",
        }));
      }
    },
    [token, loadCollections]
  );

  const deleteCollectionFn = useCallback(
    async (collectionId: string) => {
      if (!token) return;
      try {
        await collectApi.delete(collectionId, token);
        void loadCollections();
      } catch (err) {
        setState((s) => ({
          ...s,
          error: err instanceof Error ? err.message : "Erro ao deletar coleta.",
        }));
      }
    },
    [token, loadCollections]
  );

  const clearActive = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY);
    setState((s) => ({
      ...s,
      active: null,
      error: null,
      isActivelyPolling: false,
      enrichPhase: null,
      enrichRemaining: 0,
      enrichDone: false,
    }));
    apiKeyRef.current = "";
    stopAll();
  }, [stopAll]);

  // ─── Restore interrupted collection/enrich ─────────────────────────────

  useEffect(() => {
    if (!token || restoreAttemptedRef.current) return;
    restoreAttemptedRef.current = true;

    const savedId = sessionStorage.getItem(STORAGE_KEY);
    if (!savedId) return;

    void (async () => {
      try {
        const status = await collectApi.getStatus(savedId, token);
        setState((s) => {
          if (s.active) return s;
          return {
            ...s,
            active: {
              collection_id: status.collection_id,
              video_id: status.video_id,
              status: status.status,
              total_comments: status.total_comments,
              channel_dates_failed: status.channel_dates_failed ?? null,
              enrich_status: status.enrich_status ?? null,
              duration_seconds: status.duration_seconds ?? null,
              next_page_token: null,
              created_at: status.collected_at ?? new Date().toISOString(),
            },
          };
        });
        if (
          status.status !== "running" &&
          status.enrich_status !== "pending" &&
          status.enrich_status !== "enriching"
        ) {
          sessionStorage.removeItem(STORAGE_KEY);
        }
      } catch {
        sessionStorage.removeItem(STORAGE_KEY);
      }
    })();
  }, [token]);

  // Warn on browser-level navigation when polling is active
  useEffect(() => {
    if (!state.isActivelyPolling) return;
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [state.isActivelyPolling]);

  // Load collection list on mount
  useEffect(() => {
    void loadCollections();
  }, [loadCollections]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current !== null) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
      if (enrichPollingRef.current !== null) {
        clearInterval(enrichPollingRef.current);
        enrichPollingRef.current = null;
      }
      apiKeyRef.current = "";
    };
  }, []);

  return {
    loading: state.loading,
    error: state.error,
    active: state.active,
    collections: state.collections,
    isActivelyPolling: state.isActivelyPolling,
    enrichPhase: state.enrichPhase,
    enrichRemaining: state.enrichRemaining,
    enrichDone: state.enrichDone,
    startCollection,
    resumeCollection,
    importCollection: importCollectionFn,
    deleteCollection: deleteCollectionFn,
    clearActive,
    loadCollections,
  };
}
