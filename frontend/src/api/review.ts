import { API_URL, ApiError, request } from "./http";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface ConflictListItem {
  conflict_id: string;
  comment_id: string;
  dataset_id: string;
  dataset_name: string;
  author_display_name: string;
  text_original: string;
  label_a: string;
  annotator_a: string;
  justificativa_a: string | null;
  label_b: string;
  annotator_b: string;
  justificativa_b: string | null;
  status: string;
  created_at: string;
}

export interface ConflictComment {
  comment_db_id: string;
  text_original: string;
  like_count: number;
  reply_count: number;
  published_at: string;
}

export interface AnnotationSide {
  annotator: string;
  label: string;
  justificativa: string | null;
  annotated_at: string;
}

export interface ConflictDetail {
  conflict_id: string;
  status: string;
  dataset_name: string;
  author_channel_id: string;
  author_display_name: string;
  comments: ConflictComment[];
  annotation_a: AnnotationSide;
  annotation_b: AnnotationSide;
  resolved_by: string | null;
  resolved_label: string | null;
  resolved_at: string | null;
}

export interface ResolveResponse {
  conflict_id: string;
  status: string;
  resolved_label: string;
  resolved_by: string;
  resolved_at: string;
}

export interface BotAnnotationDetail {
  annotator_name: string;
  label: string;
  justificativa: string | null;
}

export interface BotCommentItem {
  comment_db_id: string;
  text_original: string;
  author_display_name: string;
  author_channel_id: string;
  dataset_id: string;
  dataset_name: string;
  annotations: BotAnnotationDetail[];
  has_conflict: boolean;
  conflict_id: string | null;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: T[];
}

export interface ReviewStats {
  total_conflicts: number;
  pending_conflicts: number;
  resolved_conflicts: number;
  total_bots_flagged: number;
}

export interface ImportResult {
  imported: number;
  skipped: number;
  errors: string[];
}

// ─── API ────────────────────────────────────────────────────────────────────

export const reviewApi = {
  listConflicts: (
    token: string,
    params?: {
      status?: string;
      video_id?: string;
      dataset_id?: string;
      page?: number;
      page_size?: number;
    }
  ) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.video_id) qs.set("video_id", params.video_id);
    if (params?.dataset_id) qs.set("dataset_id", params.dataset_id);
    qs.set("page", String(params?.page ?? 1));
    qs.set("page_size", String(params?.page_size ?? 20));
    return request<PaginatedResponse<ConflictListItem>>(`/review/conflicts?${qs}`, {}, token);
  },

  getConflict: (conflictId: string, token: string) =>
    request<ConflictDetail>(`/review/conflicts/${conflictId}`, {}, token),

  resolve: (data: { conflict_id: string; resolved_label: "bot" | "humano" }, token: string) =>
    request<ResolveResponse>(
      "/review/resolve",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      token
    ),

  listBots: (
    token: string,
    params?: { video_id?: string; dataset_id?: string; page?: number; page_size?: number }
  ) => {
    const qs = new URLSearchParams();
    if (params?.video_id) qs.set("video_id", params.video_id);
    if (params?.dataset_id) qs.set("dataset_id", params.dataset_id);
    qs.set("page", String(params?.page ?? 1));
    qs.set("page_size", String(params?.page_size ?? 20));
    return request<PaginatedResponse<BotCommentItem>>(`/review/bots?${qs}`, {}, token);
  },

  stats: (token: string) => request<ReviewStats>("/review/stats", {}, token),

  importReview: async (
    data: {
      dataset_name: string;
      video_id: string;
      comments: Array<{
        comment_db_id: string;
        author_channel_id: string;
        author_display_name: string;
        text_original: string;
        final_label: "bot" | "humano";
        annotations?: Array<{
          annotator: string;
          label: string;
          justificativa?: string | null;
        }>;
        resolution?: {
          resolved_by?: string;
          resolved_label: string;
          resolved_at?: string;
        } | null;
      }>;
    },
    token: string,
    onProgress?: (sent: number, total: number) => void
  ): Promise<ImportResult> => {
    const CHUNK_SIZE = 2000;
    const all = data.comments;
    const total = all.length;
    const firstBatch = all.slice(0, CHUNK_SIZE);
    const hasMore = total > CHUNK_SIZE;

    const result = await request<ImportResult>(
      "/review/import",
      {
        method: "POST",
        body: JSON.stringify({
          ...data,
          comments: firstBatch,
          done: !hasMore,
        }),
      },
      token
    );
    onProgress?.(firstBatch.length, total);

    if (!hasMore) return result;

    let offset = CHUNK_SIZE;
    let totalImported = result.imported;

    while (offset < total) {
      const chunk = all.slice(offset, offset + CHUNK_SIZE);
      const isLast = offset + chunk.length >= total;
      const chunkResult = await request<{
        total_imported: number;
        chunk_received: number;
        done: boolean;
      }>(
        "/review/import-chunk",
        {
          method: "POST",
          body: JSON.stringify({ comments: chunk, done: isLast }),
        },
        token
      );
      totalImported += chunkResult.total_imported;
      offset += chunk.length;
      onProgress?.(offset, total);
    }

    return {
      imported: totalImported,
      skipped: result.skipped,
      errors: result.errors,
    };
  },

  downloadExport: async (
    format: "json" | "csv",
    token: string,
    datasetId: string
  ): Promise<void> => {
    const qs = new URLSearchParams();
    qs.set("format", format);
    qs.set("dataset_id", datasetId);

    const res = await fetch(`${API_URL}/review/export?${qs}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { detail?: string };
      throw new ApiError(body.detail ?? "Erro ao exportar revisão.", res.status);
    }

    // Use filename from Content-Disposition if available
    const cd = res.headers.get("Content-Disposition") ?? "";
    const filenameMatch = cd.match(/filename="(.+?)"/);
    const filename = filenameMatch ? filenameMatch[1] : `review.${format}`;

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
};
