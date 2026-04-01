import { request } from "./http";

// ── Visão Geral ───────────────────────────────────────────────────

export interface GlobalSummary {
  total_datasets: number;
  total_comments_annotated: number;
  total_comments_in_datasets: number;
  annotation_progress: number;
  total_bots: number;
  total_humans: number;
  total_conflicts: number;
  pending_conflicts: number;
  agreement_rate: number;
}

export interface GlobalDashboardResponse {
  summary: GlobalSummary;
  active_criteria_filter: string[];
  label_distribution_chart: string;
  comparativo_por_dataset_chart: string;
  annotations_over_time_chart: string;
  bot_rate_by_dataset_chart: string;
  agreement_by_dataset_chart: string;
  criteria_effectiveness_chart: string;
}

// ── Eficácia por Critério ─────────────────────────────────────────

export interface CriteriaEffectivenessItem {
  criteria: string;
  group: string;
  total_datasets: number;
  total_comments_selected: number;
  total_bots: number;
  bot_rate: number;
}

// ── Por Vídeo ─────────────────────────────────────────────────────

export interface VideoSummary {
  total_comments_collected: number;
  total_comments_in_datasets: number;
  total_annotated: number;
  total_bots: number;
  total_humans: number;
  total_conflicts: number;
  pending_conflicts: number;
  agreement_rate: number;
}

export interface VideoHighlight {
  label: string;
  value: string;
  detail: string | null;
}

export interface VideoDashboardResponse {
  video_id: string;
  summary: VideoSummary;
  highlights: VideoHighlight[];
  active_criteria_filter: string[];
  label_distribution_chart: string;
  comparativo_por_dataset_chart: string;
  bot_rate_by_criteria_chart: string;
  comment_timeline_chart: string;
}

// ── Meu Progresso ─────────────────────────────────────────────────

export interface UserSummary {
  total_datasets_assigned: number;
  datasets_completed: number;
  datasets_pending: number;
  total_annotated: number;
  total_pending: number;
  bots: number;
  humans: number;
  conflicts_generated: number;
}

export interface UserDatasetProgress {
  dataset_id: string;
  dataset_name: string;
  video_id: string;
  total_comments: number;
  annotated_by_me: number;
  pending: number;
  percent_complete: number;
  my_bots: number;
  my_conflicts: number;
  status: string;
}

export interface UserDashboardResponse {
  summary: UserSummary;
  datasets: UserDatasetProgress[];
  my_label_distribution_chart: string;
  my_progress_by_dataset_chart: string;
  my_annotations_over_time_chart: string;
}

// ── Tabela de Bots ────────────────────────────────────────────────

export interface BotCommentItem {
  dataset_name: string;
  author_display_name: string;
  text_original: string;
  concordance_pct: number;
  conflict_status: string | null;
  annotators_count: number;
  criteria: string[];
}

export interface BotCommentsResponse {
  total: number;
  items: BotCommentItem[];
}

// ── API ───────────────────────────────────────────────────────────

export const dashboardApi = {
  global: (token: string, criteria?: string[]) => {
    const params = criteria?.length ? `?criteria=${criteria.join(",")}` : "";
    return request<GlobalDashboardResponse>(`/dashboard/global${params}`, {}, token);
  },

  video: (token: string, videoId: string, criteria?: string[]) => {
    const criteriaParam = criteria?.length ? `&criteria=${criteria.join(",")}` : "";
    return request<VideoDashboardResponse>(
      `/dashboard/video?video_id=${encodeURIComponent(videoId)}${criteriaParam}`,
      {},
      token
    );
  },

  user: (token: string) => request<UserDashboardResponse>("/dashboard/user", {}, token),

  bots: (
    token: string,
    params?: {
      dataset_id?: string;
      video_id?: string;
      author?: string;
      search?: string;
      criteria?: string[];
      page?: number;
      page_size?: number;
    }
  ) => {
    const qs = new URLSearchParams();
    if (params?.dataset_id) qs.set("dataset_id", params.dataset_id);
    if (params?.video_id) qs.set("video_id", params.video_id);
    if (params?.author) qs.set("author", params.author);
    if (params?.search) qs.set("search", params.search);
    if (params?.criteria?.length) qs.set("criteria", params.criteria.join(","));
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    const query = qs.toString();
    return request<BotCommentsResponse>(`/dashboard/bots${query ? `?${query}` : ""}`, {}, token);
  },

  criteriaEffectiveness: (token: string, videoId?: string) => {
    const params = videoId ? `?video_id=${encodeURIComponent(videoId)}` : "";
    return request<CriteriaEffectivenessItem[]>(
      `/dashboard/criteria-effectiveness${params}`,
      {},
      token
    );
  },
};
