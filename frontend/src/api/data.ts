import { request } from "./http";

export interface DataSummary {
  collections_count: number;
  comments_count: number;
  datasets_count: number;
  annotations_count: number;
  estimated_size_mb: number;
}

export interface DataCollection {
  collection_id: string;
  video_id: string;
  video_title: string | null;
  total_comments: number | null;
  status: string;
  enrich_status: string | null;
  channel_dates_failed: boolean | null;
  total_users: number;
  collected_by: string;
  created_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
}

export interface DataDataset {
  dataset_id: string;
  name: string;
  collection_id: string;
  video_id: string;
  criteria: string[];
  total_users_original: number;
  total_selected: number;
  total_comments: number;
  created_by: string;
  created_at: string;
}

export interface DataAnnotationProgress {
  dataset_id: string;
  dataset_name: string;
  total: number;
  annotated: number;
  pending: number;
  conflicts: number;
  conflicts_resolved: number;
  annotators_count: number;
  bots_users: number;
  bots_comments: number;
}

export const dataApi = {
  summary: (token: string) => request<DataSummary>("/data/summary", {}, token),

  collections: (token: string) => request<DataCollection[]>("/data/collections", {}, token),

  datasets: (token: string) => request<DataDataset[]>("/data/datasets", {}, token),

  annotations: (token: string) => request<DataAnnotationProgress[]>("/data/annotations", {}, token),
};
