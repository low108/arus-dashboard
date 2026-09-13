import type { Goal, IntegrationStatus, OverviewData, Transaction } from "@/types/finance";

export const API_URL = process.env.NEXT_PUBLIC_ARUS_API_URL || "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  integrations: () => request<IntegrationStatus>("/api/integrations/status"),
  overview: () => request<OverviewData>("/api/overview"),
  statements: () => request<Array<Record<string, unknown>>>("/api/statements"),
  transactions: () => request<Transaction[]>("/api/transactions"),
  categorizeTransactions: () => request<{ job_id: string; categorized: number; updated_statements: number }>("/api/transactions/categorize", { method: "POST" }),
  activity: (jobId: string) => request<Array<Record<string, unknown>>>(`/api/agent-runs/${jobId}`),
  sync: () => request<Record<string, unknown>>("/api/sync", { method: "POST" }),
  verifyOpenRouter: () => request<Record<string, unknown>>("/api/integrations/openrouter/verify", { method: "POST" }),
  disconnectGmail: () => request<{ connected: boolean }>("/api/auth/google/disconnect", { method: "POST" }),
  importStatement: (form: FormData) => request<Record<string, unknown>>("/api/statements/import", { method: "POST", body: form }),
  goals: () => request<Goal[]>("/api/goals"),
  createGoal: (payload: Omit<Goal, "id" | "created_at" | "updated_at">) => request<Goal>("/api/goals", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  updateGoal: (id: number, payload: Partial<Omit<Goal, "id" | "created_at" | "updated_at">>) => request<Goal>(`/api/goals/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  deleteGoal: (id: number) => request<void>(`/api/goals/${id}`, { method: "DELETE" }),
};
