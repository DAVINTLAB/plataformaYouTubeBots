import { useCallback, useState } from "react";
import {
  reviewApi,
  BotCommentItem,
  ConflictDetail,
  ConflictListItem,
  ImportResult,
  PaginatedResponse,
  ReviewStats,
} from "../api/review";
import { useAuthContext } from "../contexts/AuthContext";

interface ReviewState {
  loading: boolean;
  error: string | null;
  conflictsData: PaginatedResponse<ConflictListItem> | null;
  conflictDetail: ConflictDetail | null;
  botsData: PaginatedResponse<BotCommentItem> | null;
  stats: ReviewStats | null;
  importResult: ImportResult | null;
}

export function useReview() {
  const { token } = useAuthContext();
  const [state, setState] = useState<ReviewState>({
    loading: false,
    error: null,
    conflictsData: null,
    conflictDetail: null,
    botsData: null,
    stats: null,
    importResult: null,
  });

  const clearError = useCallback(() => {
    setState((s) => ({ ...s, error: null }));
  }, []);

  const clearImportResult = useCallback(() => {
    setState((s) => ({ ...s, importResult: null }));
  }, []);

  const fetchConflicts = useCallback(
    async (params?: {
      status?: string;
      video_id?: string;
      dataset_id?: string;
      page?: number;
      page_size?: number;
    }) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await reviewApi.listConflicts(token, params);
        setState((s) => ({ ...s, loading: false, conflictsData: result }));
        return result;
      } catch (err) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao listar conflitos.",
        }));
      }
    },
    [token]
  );

  const fetchConflictDetail = useCallback(
    async (conflictId: string) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await reviewApi.getConflict(conflictId, token);
        setState((s) => ({
          ...s,
          loading: false,
          conflictDetail: result,
        }));
        return result;
      } catch (err) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao carregar conflito.",
        }));
      }
    },
    [token]
  );

  const resolveConflict = useCallback(
    async (conflictId: string, label: "bot" | "humano") => {
      if (!token) return;
      try {
        const result = await reviewApi.resolve(
          { conflict_id: conflictId, resolved_label: label },
          token
        );

        // Update conflict in local state
        setState((s) => ({
          ...s,
          conflictsData: s.conflictsData
            ? {
                ...s.conflictsData,
                items: s.conflictsData.items.map((c) =>
                  c.conflict_id === conflictId ? { ...c, status: "resolved" } : c
                ),
              }
            : null,
          conflictDetail: s.conflictDetail
            ? {
                ...s.conflictDetail,
                status: "resolved",
                resolved_label: result.resolved_label,
                resolved_by: result.resolved_by,
                resolved_at: result.resolved_at,
              }
            : null,
        }));

        return result;
      } catch (err) {
        setState((s) => ({
          ...s,
          error: err instanceof Error ? err.message : "Erro ao resolver conflito.",
        }));
      }
    },
    [token]
  );

  const fetchBots = useCallback(
    async (params?: {
      video_id?: string;
      dataset_id?: string;
      page?: number;
      page_size?: number;
    }) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await reviewApi.listBots(token, params);
        setState((s) => ({ ...s, loading: false, botsData: result }));
        return result;
      } catch (err) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao listar bots.",
        }));
      }
    },
    [token]
  );

  const fetchStats = useCallback(async () => {
    if (!token) return;
    try {
      const result = await reviewApi.stats(token);
      setState((s) => ({ ...s, stats: result }));
      return result;
    } catch (err) {
      setState((s) => ({
        ...s,
        error: err instanceof Error ? err.message : "Erro ao carregar estatísticas.",
      }));
    }
  }, [token]);

  const importReview = useCallback(
    async (data: Parameters<typeof reviewApi.importReview>[0]) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await reviewApi.importReview(data, token);
        setState((s) => ({ ...s, loading: false, importResult: result }));
        return result;
      } catch (err) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao importar revisão.",
        }));
      }
    },
    [token]
  );

  const downloadExport = useCallback(
    async (format: "json" | "csv", datasetId: string) => {
      if (!token) return;
      try {
        await reviewApi.downloadExport(format, token, datasetId);
      } catch (err) {
        setState((s) => ({
          ...s,
          error: err instanceof Error ? err.message : "Erro ao exportar revisão.",
        }));
      }
    },
    [token]
  );

  return {
    ...state,
    clearError,
    clearImportResult,
    fetchConflicts,
    fetchConflictDetail,
    resolveConflict,
    fetchBots,
    fetchStats,
    importReview,
    downloadExport,
  };
}
