import { useCallback, useState } from "react";
import {
  annotateApi,
  AnnotationResult,
  AnnotatorProgress,
  DatasetProgress,
  DatasetUsersResponse,
  ImportResult,
  UserCommentsResponse,
} from "../api/annotate";
import { useAuthContext } from "../contexts/AuthContext";

interface AnnotateState {
  loading: boolean;
  error: string | null;
  datasetUsers: DatasetUsersResponse | null;
  userComments: UserCommentsResponse | null;
  progress: DatasetProgress[];
  allProgress: AnnotatorProgress[];
  importResult: ImportResult | null;
}

export function useAnnotate() {
  const { token } = useAuthContext();
  const [state, setState] = useState<AnnotateState>({
    loading: false,
    error: null,
    datasetUsers: null,
    userComments: null,
    progress: [],
    allProgress: [],
    importResult: null,
  });

  const clearError = useCallback(() => {
    setState((s) => ({ ...s, error: null }));
  }, []);

  const clearImportResult = useCallback(() => {
    setState((s) => ({ ...s, importResult: null }));
  }, []);

  const fetchDatasetUsers = useCallback(
    async (datasetId: string, page = 1, pageSize = 20) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await annotateApi.listUsers(datasetId, token, page, pageSize);
        setState((s) => ({ ...s, loading: false, datasetUsers: result, userComments: null }));
        return result;
      } catch (err) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao listar usuários do dataset.",
        }));
      }
    },
    [token]
  );

  const fetchUserComments = useCallback(
    async (entryId: string) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await annotateApi.getComments(entryId, token);
        setState((s) => ({ ...s, loading: false, userComments: result }));
        return result;
      } catch (err) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao carregar comentários.",
        }));
      }
    },
    [token]
  );

  const submitAnnotation = useCallback(
    async (
      commentDbId: string,
      label: "bot" | "humano",
      justificativa?: string | null
    ): Promise<AnnotationResult | undefined> => {
      if (!token) return;
      try {
        const result = await annotateApi.submit(
          { comment_db_id: commentDbId, label, justificativa },
          token
        );

        // Atualizar o comentário no state local
        setState((s) => {
          if (!s.userComments) return s;
          const updated = s.userComments.comments.map((c) =>
            c.comment_db_id === commentDbId
              ? {
                  ...c,
                  my_annotation: {
                    label,
                    justificativa: justificativa ?? null,
                    annotated_at: new Date().toISOString(),
                  },
                }
              : c
          );
          return {
            ...s,
            userComments: { ...s.userComments, comments: updated },
          };
        });

        return result;
      } catch (err) {
        setState((s) => ({
          ...s,
          error: err instanceof Error ? err.message : "Erro ao salvar anotação.",
        }));
      }
    },
    [token]
  );

  const fetchProgress = useCallback(async () => {
    if (!token) return;
    try {
      const result = await annotateApi.myProgress(token);
      setState((s) => ({ ...s, progress: result }));
    } catch (err) {
      setState((s) => ({
        ...s,
        error: err instanceof Error ? err.message : "Erro ao carregar progresso.",
      }));
    }
  }, [token]);

  const fetchAllProgress = useCallback(async () => {
    if (!token) return;
    try {
      const result = await annotateApi.allProgress(token);
      setState((s) => ({ ...s, allProgress: result }));
    } catch (err) {
      setState((s) => ({
        ...s,
        error: err instanceof Error ? err.message : "Erro ao carregar progresso dos anotadores.",
      }));
    }
  }, [token]);

  const importAnnotations = useCallback(
    async (data: {
      dataset_id?: string;
      dataset_name?: string;
      video_id?: string;
      annotations: Array<{
        comment_db_id: string;
        label: "bot" | "humano";
        justificativa?: string | null;
      }>;
    }) => {
      if (!token) return;
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await annotateApi.importAnnotations(data, token);
        setState((s) => ({ ...s, loading: false, importResult: result }));
        return result;
      } catch (err) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao importar anotações.",
        }));
      }
    },
    [token]
  );

  const downloadExport = useCallback(
    async (format: "json" | "csv", datasetId?: string) => {
      if (!token) return;
      try {
        await annotateApi.downloadExport(format, token, datasetId);
      } catch (err) {
        setState((s) => ({
          ...s,
          error: err instanceof Error ? err.message : "Erro ao exportar anotações.",
        }));
      }
    },
    [token]
  );

  return {
    ...state,
    clearError,
    clearImportResult,
    fetchDatasetUsers,
    fetchUserComments,
    submitAnnotation,
    fetchProgress,
    fetchAllProgress,
    importAnnotations,
    downloadExport,
  };
}
