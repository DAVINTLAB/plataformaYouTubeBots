import { useCallback, useState } from "react";
import {
  cleanApi,
  DatasetCreateRequest,
  DatasetResponse,
  DatasetSummary,
  PreviewResponse,
} from "../api/clean";
import { useAuthContext } from "../contexts/AuthContext";

interface CleanState {
  loading: boolean;
  error: string | null;
  preview: PreviewResponse | null;
  datasets: DatasetSummary[];
  createdDataset: DatasetResponse | null;
}

export function useClean() {
  const { token } = useAuthContext();
  const [state, setState] = useState<CleanState>({
    loading: false,
    error: null,
    preview: null,
    datasets: [],
    createdDataset: null,
  });

  const clearError = useCallback(() => {
    setState((s) => ({ ...s, error: null }));
  }, []);

  const clearPreview = useCallback(() => {
    setState((s) => ({ ...s, preview: null }));
  }, []);

  const fetchPreview = useCallback(
    async (
      collectionId: string,
      criteria: string[],
      thresholds: { threshold_chars: number; threshold_seconds: number }
    ) => {
      if (!token || criteria.length === 0) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await cleanApi.preview(
          {
            collection_id: collectionId,
            criteria: criteria.join(","),
            threshold_chars: thresholds.threshold_chars,
            threshold_seconds: thresholds.threshold_seconds,
          },
          token
        );
        setState((s) => ({ ...s, loading: false, preview: result }));
      } catch (err) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao carregar preview.",
        }));
      }
    },
    [token]
  );

  const createDataset = useCallback(
    async (data: DatasetCreateRequest) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await cleanApi.create(data, token);
        setState((s) => ({
          ...s,
          loading: false,
          createdDataset: result,
          preview: null,
        }));
        return result;
      } catch (err) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao criar dataset.",
        }));
      }
    },
    [token]
  );

  const fetchDatasets = useCallback(
    async (videoId?: string) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await cleanApi.list(token, videoId);
        setState((s) => ({ ...s, loading: false, datasets: result }));
      } catch (err) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao listar datasets.",
        }));
      }
    },
    [token]
  );

  const downloadDataset = useCallback(
    async (datasetId: string, format: "json" | "csv", datasetName: string) => {
      if (!token) return;
      try {
        await cleanApi.download(datasetId, format, token, datasetName);
      } catch (err) {
        setState((s) => ({
          ...s,
          error: err instanceof Error ? err.message : "Erro ao baixar dataset.",
        }));
      }
    },
    [token]
  );

  const importDataset = useCallback(
    async (data: {
      dataset: { name: string; video_id: string; criteria_applied: string[] };
      users: Array<{
        author_channel_id: string;
        author_display_name: string;
        comment_count: number;
        matched_criteria: string[];
      }>;
    }) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await cleanApi.import(data, token);
        setState((s) => ({
          ...s,
          loading: false,
          createdDataset: result,
        }));
        return result;
      } catch (err) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao importar dataset.",
        }));
      }
    },
    [token]
  );

  const deleteDataset = useCallback(
    async (datasetId: string) => {
      if (!token) return;
      try {
        await cleanApi.delete(datasetId, token);
        setState((s) => ({
          ...s,
          datasets: s.datasets.filter((d) => d.dataset_id !== datasetId),
        }));
      } catch (err) {
        setState((s) => ({
          ...s,
          error: err instanceof Error ? err.message : "Erro ao deletar dataset.",
        }));
      }
    },
    [token]
  );

  return {
    ...state,
    clearError,
    clearPreview,
    fetchPreview,
    createDataset,
    fetchDatasets,
    downloadDataset,
    importDataset,
    deleteDataset,
  };
}
