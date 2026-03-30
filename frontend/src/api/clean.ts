import { API_URL, ApiError, request } from "./http";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface CriteriaCount {
  selected_users: number;
  threshold_chars?: number;
  threshold_seconds?: number;
}

export interface CentralMeasures {
  mean: number;
  mode: number;
  median: number;
  iqr_lower: number;
  iqr_upper: number;
}

export interface PreviewResponse {
  collection_id: string;
  total_users: number;
  central_measures: CentralMeasures;
  by_criteria: Record<string, CriteriaCount>;
  union_if_combined: number;
}

export interface DatasetResponse {
  dataset_id: string;
  name: string;
  collection_id: string;
  video_id: string;
  total_users_original: number;
  total_users_selected: number;
  criteria_applied: string[];
  created_at: string;
}

export interface DatasetSummary {
  dataset_id: string;
  name: string;
  video_id: string;
  total_users_selected: number;
  criteria_applied: string[];
  created_at: string;
}

export interface DatasetCreateRequest {
  collection_id: string;
  criteria: string[];
  thresholds?: {
    threshold_chars?: number;
    threshold_seconds?: number;
  };
}

// ─── API ────────────────────────────────────────────────────────────────────

export const cleanApi = {
  preview: (
    params: {
      collection_id: string;
      criteria: string;
      threshold_chars?: number;
      threshold_seconds?: number;
    },
    token: string
  ) => {
    const qs = new URLSearchParams();
    qs.set("collection_id", params.collection_id);
    qs.set("criteria", params.criteria);
    if (params.threshold_chars != null) qs.set("threshold_chars", String(params.threshold_chars));
    if (params.threshold_seconds != null)
      qs.set("threshold_seconds", String(params.threshold_seconds));

    return request<PreviewResponse>(`/clean/preview?${qs}`, {}, token);
  },

  create: (data: DatasetCreateRequest, token: string) =>
    request<DatasetResponse>("/clean", { method: "POST", body: JSON.stringify(data) }, token),

  list: (token: string, videoId?: string) => {
    const qs = videoId ? `?video_id=${videoId}` : "";
    return request<DatasetSummary[]>(`/clean/datasets${qs}`, {}, token);
  },

  download: async (
    datasetId: string,
    format: "json" | "csv",
    token: string,
    datasetName: string
  ): Promise<void> => {
    const res = await fetch(`${API_URL}/clean/datasets/${datasetId}/download?format=${format}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { detail?: string };
      throw new ApiError(body.detail ?? "Erro ao baixar dataset.", res.status);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${datasetName}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  },

  delete: (datasetId: string, token: string) =>
    request<void>(`/clean/datasets/${datasetId}`, { method: "DELETE" }, token),

  import: (
    data: {
      dataset: { name: string; video_id: string; criteria_applied: string[] };
      users: Array<{
        author_channel_id: string;
        author_display_name: string;
        comment_count: number;
        matched_criteria: string[];
      }>;
    },
    token: string
  ) =>
    request<DatasetResponse>(
      "/clean/import",
      { method: "POST", body: JSON.stringify(data) },
      token
    ),
};
