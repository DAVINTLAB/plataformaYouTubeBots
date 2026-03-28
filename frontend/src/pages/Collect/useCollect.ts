import { useCallback, useEffect, useRef, useState } from "react";
import { collectApi, CollectionStarted, CollectionSummary, ImportRequest } from "../../api/collect";
import { useAuthContext } from "../../contexts/AuthContext";

const STORAGE_KEY = "davint_active_collection_id";

interface CollectState {
  loading: boolean;
  error: string | null;
  active: CollectionStarted | null;
  collections: CollectionSummary[];
  isActivelyPolling: boolean;
}

export function useCollect() {
  const { token } = useAuthContext();
  const [state, setState] = useState<CollectState>({
    loading: false,
    error: null,
    active: null,
    collections: [],
    isActivelyPolling: false,
  });

  // apiKey kept only in a ref — never in state (avoids accidental persistence)
  const apiKeyRef = useRef<string>("");
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const restoreAttemptedRef = useRef(false);

  const stopPolling = useCallback(() => {
    if (pollingRef.current !== null) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    setState((s) => ({ ...s, isActivelyPolling: false }));
  }, []);

  const loadCollections = useCallback(async () => {
    if (!token) return;
    try {
      const list = await collectApi.list(token);
      setState((s) => ({ ...s, collections: list }));
    } catch {
      // silently ignore list reload errors
    }
  }, [token]);

  // Advance pagination: keep calling next-page until done
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
          apiKeyRef.current = "";
          sessionStorage.removeItem(STORAGE_KEY);
          void loadCollections();
        }
      } catch (err) {
        stopPolling();
        apiKeyRef.current = "";
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao continuar coleta.",
        }));
        void loadCollections();
      }
    },
    [token, stopPolling, loadCollections]
  );

  // Poll status while running (fallback: status endpoint)
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
              }
            : s.active,
        }));
        if (status.status === "completed" || status.status === "failed") {
          stopPolling();
          apiKeyRef.current = "";
          sessionStorage.removeItem(STORAGE_KEY);
          void loadCollections();
        }
      } catch {
        stopPolling();
      }
    },
    [token, stopPolling, loadCollections]
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

  const startCollection = useCallback(
    async (videoId: string, apiKey: string) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null, active: null }));
      apiKeyRef.current = apiKey;

      try {
        const result = await collectApi.start({ video_id: videoId, api_key: apiKey }, token);
        sessionStorage.setItem(STORAGE_KEY, result.collection_id);
        setState((s) => ({ ...s, active: result, loading: false }));

        if (result.status === "completed" || result.status === "failed") {
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
    [token, loadCollections, _startPollingLoop]
  );

  // Resume an interrupted collection (next_page_token kept in DB)
  const resumeCollection = useCallback(
    async (apiKey: string) => {
      if (!token || !state.active) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      apiKeyRef.current = apiKey;

      try {
        const next = await collectApi.nextPage(
          { collection_id: state.active.collection_id, api_key: apiKey },
          token
        );
        setState((s) => ({ ...s, active: next, loading: false }));

        if (next.status === "completed" || next.status === "failed") {
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
    [token, state.active, loadCollections, _startPollingLoop]
  );

  const importCollectionFn = useCallback(
    async (data: ImportRequest) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null, active: null }));
      try {
        const result = await collectApi.importCollection(data, token);
        setState((s) => ({ ...s, active: result, loading: false }));
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
    setState((s) => ({ ...s, active: null, error: null, isActivelyPolling: false }));
    apiKeyRef.current = "";
    stopPolling();
  }, [stopPolling]);

  // Restore interrupted collection from sessionStorage on mount
  useEffect(() => {
    if (!token || restoreAttemptedRef.current) return;
    restoreAttemptedRef.current = true;

    const savedId = sessionStorage.getItem(STORAGE_KEY);
    if (!savedId) return;

    void (async () => {
      try {
        const status = await collectApi.getStatus(savedId, token);
        setState((s) => {
          if (s.active) return s; // already tracking a collection
          return {
            ...s,
            active: {
              collection_id: status.collection_id,
              video_id: status.video_id,
              status: status.status,
              total_comments: status.total_comments,
              channel_dates_failed: status.channel_dates_failed ?? null,
              next_page_token: null, // unknown after restore; backend has it
              created_at: status.collected_at ?? new Date().toISOString(),
            },
          };
        });
        if (status.status !== "running") {
          sessionStorage.removeItem(STORAGE_KEY);
        }
      } catch {
        sessionStorage.removeItem(STORAGE_KEY);
      }
    })();
  }, [token]);

  // Warn on browser-level navigation (tab close, URL bar) when polling is active
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

  // Cleanup polling on unmount (does NOT clear sessionStorage — intentional)
  useEffect(() => {
    return () => {
      if (pollingRef.current !== null) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
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
    startCollection,
    resumeCollection,
    importCollection: importCollectionFn,
    deleteCollection: deleteCollectionFn,
    clearActive,
    loadCollections,
  };
}
