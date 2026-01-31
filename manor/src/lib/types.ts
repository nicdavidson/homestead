export interface Session {
  chat_id: number;
  name: string;
  model: string;
  is_active: boolean;
  message_count: number;
  created_at: string;
  last_active_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  session_name: string;
  model?: string;
}

export interface LogEntry {
  id: number;
  timestamp: string;
  level: string;
  source: string;
  message: string;
  data?: Record<string, unknown>;
}

export interface Skill {
  name: string;
  description: string;
  tags: string[];
  content: string;
}

export interface AgentIdentity {
  name: string;
  display_name: string;
  emoji: string;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  status: "pending" | "in_progress" | "blocked" | "completed" | "cancelled";
  priority: "low" | "normal" | "high" | "urgent";
  assignee: string;
  blockers: Blocker[];
  depends_on: string[];
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  tags: string[];
  notes: string[];
  source: string;
}

export interface Blocker {
  type: "human_input" | "human_approval" | "human_action" | "dependency";
  description: string;
  created_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution: string | null;
}

export interface Job {
  id: string;
  name: string;
  description: string;
  schedule_type: "cron" | "interval" | "once";
  schedule_value: string;
  action_type: "outbox" | "command" | "webhook";
  action_config: Record<string, unknown>;
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  run_count: number;
  created_at: string;
  tags: string[];
  source: string;
}

export interface OutboxMessage {
  id: number;
  chat_id: number;
  agent_name: string;
  message: string;
  parse_mode: string;
  created_at: number;
  sent_at: number | null;
  status: "pending" | "sent" | "failed";
}

export interface EventEntry {
  id: number;
  timestamp: number;
  topic: string;
  source: string;
  payload: Record<string, unknown>;
  processed: boolean;
}

// --- Health & Metrics ---

export interface DatabaseHealth {
  name: string;
  status: "healthy" | "unhealthy";
  size: string;
  path?: string;
}

export interface DirectoryHealth {
  name: string;
  file_count: number;
  path?: string;
}

export interface HealthDetailed {
  status: "healthy" | "degraded" | "unhealthy";
  databases: DatabaseHealth[];
  directories: DirectoryHealth[];
  system: {
    python_version: string;
    platform: string;
    hostname: string;
  };
}

export interface LogMetrics {
  last_1h: Record<string, number>;
  last_24h: Record<string, number>;
}

export interface TaskMetrics {
  total: number;
  by_status: Record<string, number>;
}

export interface SessionMetrics {
  total: number;
  active: number;
  total_messages: number;
}

export interface JobMetrics {
  total: number;
  enabled: number;
  total_runs: number;
}

export interface OutboxMetrics {
  pending: number;
  sent: number;
  failed: number;
}

export interface UsageMetrics {
  records_24h: number;
  tokens_24h: number;
  cost_24h: number;
}

export interface AggregatedMetrics {
  logs: LogMetrics;
  tasks: TaskMetrics;
  sessions: SessionMetrics;
  jobs: JobMetrics;
  outbox: OutboxMetrics;
  usage?: UsageMetrics;
}

// --- Proposals ---

export interface ProposalFile {
  file_path: string;
  diff: string;
}

export interface Proposal {
  id: string;
  session_id: string;
  title: string;
  description: string;
  diff: string;
  file_paths: string[];
  files: ProposalFile[];
  status: "pending" | "approved" | "rejected" | "applied" | "failed";
  created_at: number;
  reviewed_at: number | null;
  applied_at: number | null;
  review_notes: string;
  pr_url: string;
  commit_sha: string;
}

export interface ProposalListResponse {
  total: number;
  proposals: Proposal[];
}

// --- Usage Monitoring ---

export interface UsageRecord {
  id: string;
  session_id: string;
  chat_id: number;
  session_name: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  cost_usd: number | null;
  num_turns: number;
  source: string;
  started_at: number;
  completed_at: number | null;
  recorded_at: number;
  extra: Record<string, unknown>;
}

export interface UsageListResponse {
  total: number;
  records: UsageRecord[];
}

export interface UsageSummary {
  total_records: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cache_creation: number;
  total_cache_read: number;
  total_tokens: number;
  total_cost_usd: number;
  total_turns: number;
  earliest: number | null;
  latest: number | null;
}

export interface UsageByModel {
  model: string;
  records: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export interface UsageTimeBucket {
  bucket: string;
  records: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
  turns: number;
}

export interface UsageBySession {
  session_id: string;
  session_name: string;
  chat_id: number;
  records: number;
  total_tokens: number;
  cost_usd: number;
  last_used: number;
}
