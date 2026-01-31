import type { Session, Message, LogEntry, Skill, AgentIdentity, Task, Job, HealthDetailed, AggregatedMetrics, OutboxMessage, EventEntry, UsageListResponse, UsageSummary, UsageByModel, UsageTimeBucket, UsageBySession, Proposal, ProposalListResponse } from "./types";

function getApiUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  const host = typeof window !== "undefined" ? window.location.hostname : "localhost";
  return `http://${host}:8700`;
}

const API_URL = getApiUrl();

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${error}`);
  }
  return res.json();
}

export const api = {
  sessions: {
    list: () => fetchAPI<Session[]>("/api/sessions"),
    listForChat: (chatId: number) =>
      fetchAPI<Session[]>(`/api/sessions/${chatId}`),
    create: (data: { chat_id: number; name: string; model: string }) =>
      fetchAPI<Session>("/api/sessions", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    activate: (chatId: number, name: string) =>
      fetchAPI<void>(`/api/sessions/${chatId}/${name}/activate`, {
        method: "PUT",
      }),
    setModel: (chatId: number, name: string, model: string) =>
      fetchAPI<void>(`/api/sessions/${chatId}/${name}/model`, {
        method: "PUT",
        body: JSON.stringify({ model }),
      }),
    delete: (chatId: number, name: string) =>
      fetchAPI<void>(`/api/sessions/${chatId}/${name}`, {
        method: "DELETE",
      }),
  },
  logs: {
    query: (params?: {
      hours?: number;
      level?: string;
      source?: string;
      search?: string;
      limit?: number;
    }) => {
      const qs = new URLSearchParams();
      if (params)
        Object.entries(params).forEach(
          ([k, v]) => v !== undefined && qs.set(k, String(v))
        );
      return fetchAPI<LogEntry[]>(`/api/logs?${qs}`);
    },
    summary: (hours?: number) =>
      fetchAPI<Record<string, Record<string, number>>>(
        `/api/logs/summary${hours ? `?hours=${hours}` : ""}`
      ),
  },
  skills: {
    list: () => fetchAPI<Skill[]>("/api/skills"),
    get: (name: string) => fetchAPI<Skill>(`/api/skills/${name}`),
    save: (
      name: string,
      data: { description: string; content: string; tags: string[] }
    ) =>
      fetchAPI<void>(`/api/skills/${name}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (name: string) =>
      fetchAPI<void>(`/api/skills/${name}`, { method: "DELETE" }),
  },
  lore: {
    list: () => fetchAPI<{ name: string; content: string }[]>("/api/lore"),
    get: (name: string) =>
      fetchAPI<{ name: string; content: string }>(`/api/lore/${name}`),
    save: (name: string, content: string) =>
      fetchAPI<void>(`/api/lore/${name}`, {
        method: "PUT",
        body: JSON.stringify({ content }),
      }),
  },
  scratchpad: {
    list: () =>
      fetchAPI<{ name: string; size: number; modified: string }[]>(
        "/api/scratchpad"
      ),
    get: (name: string) =>
      fetchAPI<{ name: string; content: string }>(`/api/scratchpad/${name}`),
    save: (name: string, content: string) =>
      fetchAPI<void>(`/api/scratchpad/${name}`, {
        method: "PUT",
        body: JSON.stringify({ content }),
      }),
    delete: (name: string) =>
      fetchAPI<void>(`/api/scratchpad/${name}`, { method: "DELETE" }),
  },
  tasks: {
    list: (params?: { status?: string; assignee?: string; tag?: string }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && qs.set(k, String(v)));
      return fetchAPI<Task[]>(`/api/tasks?${qs}`);
    },
    get: (id: string) => fetchAPI<Task>(`/api/tasks/${id}`),
    create: (data: Partial<Task>) => fetchAPI<Task>("/api/tasks", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Partial<Task>) => fetchAPI<Task>(`/api/tasks/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    updateStatus: (id: string, status: string) => fetchAPI<void>(`/api/tasks/${id}/status`, { method: "PUT", body: JSON.stringify({ status }) }),
    addNote: (id: string, note: string) => fetchAPI<void>(`/api/tasks/${id}/notes`, { method: "POST", body: JSON.stringify({ note }) }),
    delete: (id: string) => fetchAPI<void>(`/api/tasks/${id}`, { method: "DELETE" }),
    summary: () => fetchAPI<Record<string, number>>("/api/tasks/summary"),
  },
  jobs: {
    list: () => fetchAPI<Job[]>("/api/jobs"),
    get: (id: string) => fetchAPI<Job>(`/api/jobs/${id}`),
    create: (data: Partial<Job>) => fetchAPI<Job>("/api/jobs", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Partial<Job>) => fetchAPI<Job>(`/api/jobs/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    toggle: (id: string) => fetchAPI<void>(`/api/jobs/${id}/toggle`, { method: "PUT" }),
    delete: (id: string) => fetchAPI<void>(`/api/jobs/${id}`, { method: "DELETE" }),
    run: (id: string) => fetchAPI<void>(`/api/jobs/${id}/run`, { method: "POST" }),
    summary: () => fetchAPI<Record<string, number>>("/api/jobs/summary"),
  },
  outbox: {
    list: (params?: { status?: string; agent?: string }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && qs.set(k, String(v)));
      return fetchAPI<OutboxMessage[]>(`/api/outbox?${qs}`);
    },
    create: (data: { chat_id: number; agent_name: string; message: string }) =>
      fetchAPI<{ status: string }>("/api/outbox", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  events: {
    list: (params?: { pattern?: string; source?: string; hours?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && qs.set(k, String(v)));
      return fetchAPI<EventEntry[]>(`/api/events?${qs}`);
    },
  },
  config: {
    get: () => fetchAPI<Record<string, unknown>>("/api/config"),
    update: (data: Record<string, unknown>) =>
      fetchAPI<{ status: string; saved?: Record<string, unknown> }>("/api/config", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    agents: () => fetchAPI<AgentIdentity[]>("/api/agents"),
  },
  health: {
    detailed: () => fetchAPI<HealthDetailed>("/health/detailed"),
  },
  metrics: {
    get: () => fetchAPI<AggregatedMetrics>("/metrics"),
  },
  proposals: {
    list: (params?: { status?: string; limit?: number; offset?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && qs.set(k, String(v)));
      return fetchAPI<ProposalListResponse>(`/api/proposals?${qs}`);
    },
    get: (id: string) => fetchAPI<Proposal>(`/api/proposals/${id}`),
    create: (data: { title: string; description: string; file_path: string; original_content: string; new_content: string; session_id?: string }) =>
      fetchAPI<Proposal>("/api/proposals", { method: "POST", body: JSON.stringify(data) }),
    review: (id: string, data: { status: string; review_notes?: string }) =>
      fetchAPI<Proposal>(`/api/proposals/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    apply: (id: string) =>
      fetchAPI<Proposal>(`/api/proposals/${id}/apply`, { method: "POST" }),
    delete: (id: string) =>
      fetchAPI<void>(`/api/proposals/${id}`, { method: "DELETE" }),
  },
  usage: {
    list: (params?: {
      session_id?: string;
      chat_id?: number;
      model?: string;
      source?: string;
      since?: number;
      until?: number;
      limit?: number;
      offset?: number;
    }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && qs.set(k, String(v)));
      return fetchAPI<UsageListResponse>(`/api/usage?${qs}`);
    },
    summary: (params?: { since?: number; until?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && qs.set(k, String(v)));
      return fetchAPI<UsageSummary>(`/api/usage/summary?${qs}`);
    },
    byModel: (params?: { since?: number; until?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && qs.set(k, String(v)));
      return fetchAPI<UsageByModel[]>(`/api/usage/by-model?${qs}`);
    },
    timeseries: (params?: { since?: number; until?: number; bucket?: string }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && qs.set(k, String(v)));
      return fetchAPI<UsageTimeBucket[]>(`/api/usage/timeseries?${qs}`);
    },
    bySession: (params?: { since?: number; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && qs.set(k, String(v)));
      return fetchAPI<UsageBySession[]>(`/api/usage/by-session?${qs}`);
    },
  },
};
