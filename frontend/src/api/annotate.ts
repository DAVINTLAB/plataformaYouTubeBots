import { API_URL, ApiError, request } from "./http";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface UserItem {
  entry_id: string;
  author_channel_id: string;
  author_display_name: string;
  comment_count: number;
  my_annotated_count: number;
  my_pending_count: number;
}

export interface DatasetUsersResponse {
  dataset_id: string;
  dataset_name: string;
  total_users: number;
  total_comments: number;
  annotated_comments_by_me: number;
  items: UserItem[];
}

export interface MyAnnotation {
  label: string;
  justificativa: string | null;
  annotated_at: string;
}

export interface AnnotatorAnnotation {
  annotator_name: string;
  label: string;
  justificativa: string | null;
  annotated_at: string;
}

export interface CommentWithAnnotation {
  comment_db_id: string;
  text_original: string;
  like_count: number;
  reply_count: number;
  published_at: string;
  my_annotation: MyAnnotation | null;
  all_annotations?: AnnotatorAnnotation[] | null;
}

export interface UserCommentsResponse {
  entry_id: string;
  author_display_name: string;
  author_channel_id: string;
  comments: CommentWithAnnotation[];
}

export interface AnnotationResult {
  annotation_id: string;
  comment_db_id: string;
  label: string;
  conflict_created: boolean;
}

export interface DatasetProgress {
  dataset_id: string;
  dataset_name: string;
  total_comments: number;
  annotated: number;
  bots: number;
  humans: number;
  percent_complete: number;
}

export interface ImportResult {
  imported: number;
  updated: number;
  skipped: number;
  errors: string[];
}

export interface AnnotatorProgress {
  annotator_id: string;
  annotator_name: string;
  dataset_id: string;
  dataset_name: string;
  total_comments: number;
  annotated: number;
  bots: number;
  humans: number;
  percent_complete: number;
}

// ─── API ────────────────────────────────────────────────────────────────────

export const annotateApi = {
  listUsers: (datasetId: string, token: string) =>
    request<DatasetUsersResponse>(`/annotate/users?dataset_id=${datasetId}`, {}, token),

  getComments: (entryId: string, token: string) =>
    request<UserCommentsResponse>(`/annotate/comments/${entryId}`, {}, token),

  submit: (
    data: {
      comment_db_id: string;
      label: "bot" | "humano";
      justificativa?: string | null;
    },
    token: string
  ) =>
    request<AnnotationResult>("/annotate", { method: "POST", body: JSON.stringify(data) }, token),

  myProgress: (token: string) => request<DatasetProgress[]>("/annotate/my-progress", {}, token),

  allProgress: (token: string) => request<AnnotatorProgress[]>("/annotate/all-progress", {}, token),

  importAnnotations: async (
    data: {
      dataset_id?: string;
      dataset_name?: string;
      video_id?: string;
      annotations: Array<{
        comment_db_id: string;
        label: "bot" | "humano";
        justificativa?: string | null;
      }>;
    },
    token: string,
    onProgress?: (sent: number, total: number) => void
  ): Promise<ImportResult> => {
    const CHUNK_SIZE = 2000;
    const all = data.annotations;
    const total = all.length;
    const firstBatch = all.slice(0, CHUNK_SIZE);
    const hasMore = total > CHUNK_SIZE;

    const result = await request<ImportResult>(
      "/annotate/import",
      {
        method: "POST",
        body: JSON.stringify({
          ...data,
          annotations: firstBatch,
          done: !hasMore,
        }),
      },
      token
    );
    onProgress?.(firstBatch.length, total);

    if (!hasMore) return result;

    let offset = CHUNK_SIZE;
    let totalImported = result.imported;
    let totalUpdated = result.updated;

    while (offset < total) {
      const chunk = all.slice(offset, offset + CHUNK_SIZE);
      const isLast = offset + chunk.length >= total;
      const chunkResult = await request<{
        total_imported: number;
        total_updated: number;
        chunk_received: number;
        done: boolean;
      }>(
        "/annotate/import-chunk",
        {
          method: "POST",
          body: JSON.stringify({ annotations: chunk, done: isLast }),
        },
        token
      );
      totalImported += chunkResult.total_imported;
      totalUpdated += chunkResult.total_updated;
      offset += chunk.length;
      onProgress?.(offset, total);
    }

    return {
      imported: totalImported,
      updated: totalUpdated,
      skipped: result.skipped,
      errors: result.errors,
    };
  },

  downloadExport: async (
    format: "json" | "csv",
    token: string,
    datasetId?: string
  ): Promise<void> => {
    const qs = new URLSearchParams();
    qs.set("format", format);
    if (datasetId) qs.set("dataset_id", datasetId);

    const res = await fetch(`${API_URL}/annotate/export?${qs}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { detail?: string };
      throw new ApiError(body.detail ?? "Erro ao exportar anotações.", res.status);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `annotations.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  },
};
