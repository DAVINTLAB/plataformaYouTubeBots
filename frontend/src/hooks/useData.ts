import { useCallback, useEffect, useState } from "react";
import {
  dataApi,
  DataAnnotationProgress,
  DataCollection,
  DataDataset,
  DataSummary,
} from "../api/data";
import { annotateApi } from "../api/annotate";
import { cleanApi } from "../api/clean";
import { collectApi } from "../api/collect";
import { reviewApi } from "../api/review";
import { useAuthContext } from "../contexts/AuthContext";

interface DataState {
  loading: boolean;
  error: string | null;
  summary: DataSummary | null;
  collections: DataCollection[];
  datasets: DataDataset[];
  annotations: DataAnnotationProgress[];
}

export function useData() {
  const { token } = useAuthContext();
  const [state, setState] = useState<DataState>({
    loading: false,
    error: null,
    summary: null,
    collections: [],
    datasets: [],
    annotations: [],
  });

  const loadAll = useCallback(async () => {
    if (!token) return;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const [summary, collections, datasets, annotations] = await Promise.all([
        dataApi.summary(token),
        dataApi.collections(token),
        dataApi.datasets(token),
        dataApi.annotations(token),
      ]);
      setState({
        loading: false,
        error: null,
        summary,
        collections,
        datasets,
        annotations,
      });
    } catch (err) {
      setState((s) => ({
        ...s,
        loading: false,
        error: err instanceof Error ? err.message : "Erro ao carregar dados.",
      }));
    }
  }, [token]);

  const deleteCollection = useCallback(
    async (collectionId: string) => {
      if (!token) return;
      await collectApi.delete(collectionId, token);
      await loadAll();
    },
    [token, loadAll]
  );

  const exportCollection = useCallback(
    async (collectionId: string, format: "json" | "csv", videoId: string) => {
      if (!token) return;
      await collectApi.downloadExport(collectionId, format, token, videoId);
    },
    [token]
  );

  const downloadDataset = useCallback(
    async (datasetId: string, format: "json" | "csv", datasetName: string) => {
      if (!token) return;
      await cleanApi.download(datasetId, format, token, datasetName);
    },
    [token]
  );

  const deleteDataset = useCallback(
    async (datasetId: string) => {
      if (!token) return;
      await cleanApi.delete(datasetId, token);
      await loadAll();
    },
    [token, loadAll]
  );

  const exportAnnotations = useCallback(
    async (datasetId: string, format: "json" | "csv") => {
      if (!token) return;
      await annotateApi.downloadExport(format, token, datasetId);
    },
    [token]
  );

  const exportReview = useCallback(
    async (datasetId: string, format: "json" | "csv") => {
      if (!token) return;
      await reviewApi.downloadExport(format, token, datasetId);
    },
    [token]
  );

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  return {
    ...state,
    loadAll,
    deleteCollection,
    deleteDataset,
    exportCollection,
    exportAnnotations,
    downloadDataset,
    exportReview,
  };
}
