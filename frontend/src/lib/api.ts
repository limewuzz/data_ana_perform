import { useSessionStore } from "@/store/session";

export type Role = "annotator" | "reviewer" | "admin";

export type TokenResponse = { access_token: string; token_type: "bearer" };
export type User = { id: number; email: string; name?: string | null; role: Role; created_at?: string | null };
export type ModelInfo = { id: string; name: string; provider: string; enabled: boolean };
export type Task = {
  id: number;
  prompt: string;
  category?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  response_count?: number | null;
  annotation_count?: number | null;
  kappa?: number | null;
  responses: Array<{ id: number; model_id: string; content: string; created_at: string }>;
};
export type ReviewTaskItem = {
  task_id: number;
  kappa?: number | null;
  prompt: string;
  status: string;
  review_status: string;
  small_margin_ratio?: number;
  pair_count?: number;
  avg_duration_ms?: number;
};
export type ReviewAnnotatorItem = {
  annotator_id: number;
  task_count: number;
  annotation_count?: number;
  drop_rate: number;
  avg_duration_ms?: number | null;
  avg_kappa_with_others?: number | null;
  flags?: string[];
  conflict_pairs?: number;
  total_pairs?: number;
  conflict_rate?: number;
};
export type QueueProgress = { total_tasks: number; annotated_tasks: number; remaining_tasks: number };
export type QueueHistory = { items: Array<{ task_id: number; created_at: string }> };
export type ReviewEvent = { id: number; task_id: number; reviewer_id: number; action: string; reason?: string | null; source_set?: string | null; created_at: string };
export type ExportJob = { id: string; format: string; file_type: string; status: string; created_at: string; download_url?: string | null };
export type DashboardStats = {
  overview: {
    total_tasks: number;
    completed_tasks: number;
    dropped_tasks: number;
    drop_rate: number;
    avg_duration_ms?: number | null;
    global_kappa?: number | null;
    usable_data_ratio: number;
    low_distinctness_ratio: number;
  };
  kappa_histogram: number[];
  low_kappa_tasks: Array<{ task_id: number; kappa?: number | null }>;
  category_distribution: Array<{ category: string; task_count: number }>;
  similarity_histogram: number[];
  low_distinctness_tasks: Array<{ task_id: number; similarity: number }>;
};
export type AnnotatorStats = { items: Array<{ annotator_id: number; task_count: number; avg_duration_ms?: number | null; drop_rate: number; avg_kappa_with_others?: number | null; position_bias?: number | null }> };
export type KappaStats = { global_kappa?: number | null; per_task: Array<{ task_id: number; kappa?: number | null }>; per_category: Array<{ category: string; task_count: number; kappa?: number | null }> };
export type ModelConfig = { id: number; model_id: string; name: string; provider: string; enabled: boolean; base_url?: string | null; api_key_env?: string | null; system_prompt?: string | null; params?: Record<string, unknown> | null };

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "http://127.0.0.1:8000";

function buildHeaders(init?: RequestInit): Headers {
  const token = useSessionStore.getState().token;
  const headers = new Headers(init?.headers || {});
  if (!headers.has("content-type") && init?.body) {
    headers.set("content-type", "application/json");
  }
  if (token) headers.set("authorization", `Bearer ${token}`);
  return headers;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = buildHeaders(init);
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return response.json() as Promise<T>;
  return response.text() as unknown as T;
}

async function download(path: string): Promise<{ blob: Blob; filename: string | null }> {
  const response = await fetch(`${API_BASE_URL}${path}`, { headers: buildHeaders() });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  const disposition = response.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return { blob: await response.blob(), filename: match?.[1] || null };
}

export const api = {
  baseUrl: API_BASE_URL,
  login: (payload: { email: string; password: string }) => request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  register: (payload: { email: string; password: string; name?: string; role?: Role }) => request<TokenResponse>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request<User>("/api/users/me"),
  users: () => request<User[]>("/api/users"),
  updateUser: (id: number, payload: { name?: string; role?: Role }) => request<User>(`/api/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  models: () => request<ModelInfo[]>("/api/models"),
  tasks: (params = "") => request<Task[]>(`/api/tasks${params ? `?${params}` : ""}`),
  task: (id: number) => request<Task>(`/api/tasks/${id}`),
  createTask: (payload: { prompt: string; model_ids: string[]; category?: string }) => request<Task>("/api/tasks", { method: "POST", body: JSON.stringify(payload) }),
  importTasks: (payload: { tasks: Array<{ prompt: string; model_ids: string[]; category?: string }> }) => request<{ created: number[] }>("/api/tasks/import", { method: "POST", body: JSON.stringify(payload) }),
  createAnnotation: (payload: Record<string, unknown>) => request("/api/annotations", { method: "POST", body: JSON.stringify(payload) }),
  nextTask: (payload: Record<string, unknown>) => request<{ task?: Task | null }>("/api/queue/next", { method: "POST", body: JSON.stringify(payload) }),
  claimTask: (taskId: number) => request(`/api/queue/claim/${taskId}`, { method: "POST" }),
  completeTask: (taskId: number) => request(`/api/queue/complete/${taskId}`, { method: "POST" }),
  queueProgress: () => request<QueueProgress>("/api/queue/progress"),
  queueHistory: () => request<QueueHistory>("/api/queue/history?limit=20&offset=0"),
  dashboard: () => request<DashboardStats>("/api/stats/dashboard"),
  kappa: () => request<KappaStats>("/api/stats/kappa"),
  annotators: () => request<AnnotatorStats>("/api/stats/annotators"),
  reviewSet: (path: string) => request<any>(path),
  reviewEvents: () => request<ReviewEvent[]>("/api/review-sets/events"),
  reviewAction: (taskId: number, action: string) => request(`/api/review-sets/tasks/${taskId}/action`, { method: "POST", body: JSON.stringify({ action }) }),
  bulkReviewAction: (payload: Record<string, unknown>) => request("/api/review-sets/bulk-action", { method: "POST", body: JSON.stringify(payload) }),
  applySetAction: (payload: Record<string, unknown>) => request<any>("/api/review-sets/apply-set-action", { method: "POST", body: JSON.stringify(payload) }),
  exportData: (payload: Record<string, unknown>) => request<ExportJob | string>("/api/export", { method: "POST", body: JSON.stringify(payload) }),
  exportJobs: () => request<ExportJob[]>("/api/export/jobs?limit=20&offset=0"),
  downloadExportJob: (jobId: string) => download(`/api/export/jobs/${jobId}/download`),
  deleteExportJob: (jobId: string) => request(`/api/export/jobs/${jobId}`, { method: "DELETE" }),
  modelConfigs: () => request<ModelConfig[]>("/api/model-configs"),
  createModelConfig: (payload: Record<string, unknown>) => request<ModelConfig>("/api/model-configs", { method: "POST", body: JSON.stringify(payload) }),
  updateModelConfig: (id: number, payload: Record<string, unknown>) => request<ModelConfig>(`/api/model-configs/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteModelConfig: (id: number) => request(`/api/model-configs/${id}`, { method: "DELETE" }),
};
