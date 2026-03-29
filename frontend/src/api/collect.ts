import { API_URL, ApiError, request } from "./http";

export interface CollectionStarted {
  collection_id: string;
  video_id: string;
  status: "pending" | "running" | "completed" | "failed";
  total_comments: number | null;
  next_page_token: string | null;
  channel_dates_failed: boolean | null;
  enrich_status: string | null;
  duration_seconds: number | null;
  created_at: string;
}

export interface CollectionStatus {
  collection_id: string;
  video_id: string;
  status: "pending" | "running" | "completed" | "failed";
  total_comments: number | null;
  channel_dates_failed: boolean | null;
  enrich_status: string | null;
  duration_seconds: number | null;
  collected_at: string | null;
  collected_by: string | null;
}

export interface CollectionSummary {
  collection_id: string;
  video_id: string;
  video_title: string | null;
  status: "pending" | "running" | "completed" | "failed";
  total_comments: number | null;
  channel_dates_failed: boolean | null;
  enrich_status: string | null;
  duration_seconds: number | null;
  collected_at: string | null;
}

export interface EnrichResponse {
  phase: "video" | "replies" | "channels";
  processed: number;
  remaining: number;
  done: boolean;
}

// Formato flat — idêntico ao JSON exportado pela plataforma
export interface ImportRequest {
  video: {
    id: string;
    title?: string | null;
    channel_id?: string | null;
    channel_title?: string | null;
    published_at?: string | null;
    view_count?: number | null;
    like_count?: number | null;
    comment_count?: number | null;
  };
  comments: Array<{
    comment_id: string;
    parent_id?: string | null;
    author_display_name?: string;
    author_channel_id?: string | null;
    author_channel_published_at?: string | null;
    author_profile_image_url?: string | null;
    author_channel_url?: string | null;
    text_original: string;
    text_display?: string | null;
    like_count?: number;
    reply_count?: number;
    published_at: string;
    updated_at: string;
  }>;
}

export const collectApi = {
  start: (data: { video_id: string; api_key: string }, token: string) =>
    request<CollectionStarted>("/collect", { method: "POST", body: JSON.stringify(data) }, token),

  nextPage: (data: { collection_id: string; api_key: string }, token: string) =>
    request<CollectionStarted>(
      "/collect/next-page",
      { method: "POST", body: JSON.stringify(data) },
      token
    ),

  importCollection: (data: ImportRequest, token: string) =>
    request<CollectionStarted>(
      "/collect/import",
      { method: "POST", body: JSON.stringify(data) },
      token
    ),

  enrich: (collectionId: string, apiKey: string, token: string) =>
    request<EnrichResponse>(
      `/collect/${collectionId}/enrich`,
      { method: "POST", body: JSON.stringify({ api_key: apiKey }) },
      token
    ),

  getStatus: (collectionId: string, token: string) =>
    request<CollectionStatus>(`/collect/status?collection_id=${collectionId}`, {}, token),

  list: (token: string) => request<CollectionSummary[]>("/collect", {}, token),

  delete: (collectionId: string, token: string) =>
    request<void>(`/collect/${collectionId}`, { method: "DELETE" }, token),

  downloadExport: async (
    collectionId: string,
    format: "json" | "csv",
    token: string,
    videoId: string,
    onProgress?: (percent: number) => void
  ): Promise<void> => {
    const res = await fetch(`${API_URL}/collect/${collectionId}/export?format=${format}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { detail?: string };
      throw new ApiError(body.detail ?? "Erro ao exportar.", res.status);
    }

    const total = res.headers.get("Content-Length");
    const totalBytes = total ? parseInt(total, 10) : null;

    // Sem Content-Length ou sem suporte a ReadableStream: download direto
    if (!totalBytes || !res.body) {
      const blob = await res.blob();
      _triggerDownload(blob, `${videoId}_comments.${format}`);
      onProgress?.(100);
      return;
    }

    const reader = res.body.getReader();
    const chunks: Uint8Array[] = [];
    let received = 0;

    let done = false;
    while (!done) {
      const result = await reader.read();
      done = result.done;
      const value = result.value;
      if (value) {
        chunks.push(value);
        received += value.length;
        onProgress?.(Math.min(99, Math.round((received / totalBytes) * 100)));
      }
    }

    const blob = new Blob(chunks as unknown as BlobPart[]);
    _triggerDownload(blob, `${videoId}_comments.${format}`);
    onProgress?.(100);
  },
};

function _triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
