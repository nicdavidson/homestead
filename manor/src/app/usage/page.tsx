"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type {
  UsageSummary,
  UsageByModel,
  UsageTimeBucket,
  UsageBySession,
  UsageListResponse,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function classNames(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function formatCost(usd: number | null): string {
  if (usd === null || usd === undefined) return "--";
  if (usd < 0.01 && usd > 0) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

function formatTimestamp(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const MODEL_COLORS: Record<string, string> = {
  "claude-opus-4-5-20251101": "#f59e0b",
  "claude-sonnet-4-20250514": "#3b82f6",
  "claude-haiku-3-5-20241022": "#22c55e",
  "claude-sonnet-4-5-20250514": "#8b5cf6",
};
const FALLBACK_COLORS = ["#ec4899", "#14b8a6", "#f97316", "#6366f1", "#a855f7"];

function getModelColor(model: string, idx: number): string {
  return MODEL_COLORS[model] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
}

function shortModel(model: string): string {
  return model
    .replace("claude-", "")
    .replace(/-\d{8}$/, "")
    .replace(/-/g, " ");
}

const TIME_RANGES = {
  "24h": { label: "24h", seconds: 86400, bucket: "hour" as const },
  "7d": { label: "7d", seconds: 604800, bucket: "day" as const },
  "30d": { label: "30d", seconds: 2592000, bucket: "day" as const },
  all: { label: "All", seconds: 0, bucket: "day" as const },
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Card({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={classNames(
        "rounded-xl border border-neutral-800 bg-neutral-900 p-5",
        className
      )}
    >
      {children}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <Card>
      <p className="text-xs text-neutral-500 mb-1 font-medium">{label}</p>
      <p
        className={classNames(
          "text-2xl font-bold tabular-nums font-mono",
          color || "text-neutral-100"
        )}
      >
        {value}
      </p>
      {sub && (
        <p className="text-[11px] text-neutral-600 mt-1">{sub}</p>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Token Usage Bar Chart
// ---------------------------------------------------------------------------

function TokenBars({ data }: { data: UsageTimeBucket[] }) {
  if (data.length === 0) {
    return (
      <Card>
        <h3 className="text-sm font-semibold text-neutral-300 mb-4">
          Token Usage Over Time
        </h3>
        <p className="text-xs text-neutral-600 text-center py-8">
          No usage data yet
        </p>
      </Card>
    );
  }

  const maxTokens = Math.max(...data.map((d) => d.total_tokens), 1);

  return (
    <Card>
      <h3 className="text-sm font-semibold text-neutral-300 mb-4">
        Token Usage Over Time
      </h3>
      <div className="flex items-end gap-1 h-40">
        {data.map((bucket, i) => {
          const inputPct = (bucket.input_tokens / maxTokens) * 100;
          const outputPct = (bucket.output_tokens / maxTokens) * 100;
          return (
            <div
              key={bucket.bucket}
              className="flex-1 flex flex-col items-stretch justify-end h-full group relative"
              title={`${bucket.bucket}\nInput: ${formatTokens(bucket.input_tokens)}\nOutput: ${formatTokens(bucket.output_tokens)}\nCost: ${formatCost(bucket.cost_usd)}`}
            >
              <div
                className="bg-amber-500/80 rounded-t-sm transition-all"
                style={{ height: `${inputPct}%` }}
              />
              <div
                className="bg-blue-500/80 rounded-b-sm transition-all"
                style={{ height: `${outputPct}%` }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-4 mt-3 text-[11px] text-neutral-500">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-amber-500/80" />
          Input
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-blue-500/80" />
          Output
        </div>
        <span className="ml-auto tabular-nums">
          Max: {formatTokens(maxTokens)}
        </span>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Model Donut
// ---------------------------------------------------------------------------

function ModelDonut({ models }: { models: UsageByModel[] }) {
  if (models.length === 0) {
    return (
      <Card>
        <h3 className="text-sm font-semibold text-neutral-300 mb-4">
          Cost by Model
        </h3>
        <p className="text-xs text-neutral-600 text-center py-8">
          No usage data yet
        </p>
      </Card>
    );
  }

  const totalCost = models.reduce((s, m) => s + (m.cost_usd || 0), 0) || 1;

  let accumulated = 0;
  const segments: string[] = [];
  models.forEach((m, i) => {
    const pct = ((m.cost_usd || 0) / totalCost) * 100;
    const color = getModelColor(m.model, i);
    segments.push(`${color} ${accumulated}% ${accumulated + pct}%`);
    accumulated += pct;
  });

  const gradient =
    totalCost <= 0
      ? "conic-gradient(#404040 0% 100%)"
      : `conic-gradient(${segments.join(", ")})`;

  return (
    <Card>
      <h3 className="text-sm font-semibold text-neutral-300 mb-4">
        Cost by Model
      </h3>
      <div className="flex items-center gap-6">
        <div className="relative w-28 h-28 flex-shrink-0">
          <div
            className="w-full h-full rounded-full"
            style={{ background: gradient }}
          />
          <div className="absolute inset-3 bg-neutral-900 rounded-full flex items-center justify-center">
            <span className="text-sm font-bold text-neutral-100 tabular-nums">
              {formatCost(totalCost <= 1 ? 0 : totalCost)}
            </span>
          </div>
        </div>
        <div className="space-y-1.5 min-w-0 flex-1">
          {models.map((m, i) => (
            <div key={m.model} className="flex items-center gap-2 text-xs">
              <span
                className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                style={{ backgroundColor: getModelColor(m.model, i) }}
              />
              <span className="text-neutral-400 truncate">
                {shortModel(m.model)}
              </span>
              <span className="text-neutral-500 ml-auto font-mono tabular-nums whitespace-nowrap">
                {formatCost(m.cost_usd)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Token Breakdown Bars
// ---------------------------------------------------------------------------

function TokenBreakdown({ summary }: { summary: UsageSummary }) {
  const categories = [
    { label: "Input", value: summary.total_input_tokens, color: "bg-amber-500" },
    { label: "Output", value: summary.total_output_tokens, color: "bg-blue-500" },
    { label: "Cache Create", value: summary.total_cache_creation, color: "bg-purple-500" },
    { label: "Cache Read", value: summary.total_cache_read, color: "bg-emerald-500" },
  ];
  const max = Math.max(...categories.map((c) => c.value), 1);

  return (
    <Card>
      <h3 className="text-sm font-semibold text-neutral-300 mb-4">
        Token Breakdown
      </h3>
      <div className="space-y-2">
        {categories.map((cat) => {
          const pct = Math.max((cat.value / max) * 100, cat.value > 0 ? 3 : 0);
          return (
            <div key={cat.label} className="flex items-center gap-3">
              <span className="text-[11px] text-neutral-500 w-24 text-right">
                {cat.label}
              </span>
              <div className="flex-1 h-5 bg-neutral-800 rounded overflow-hidden">
                <div
                  className={classNames("h-full rounded transition-all duration-500", cat.color)}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs text-neutral-400 w-16 text-right font-mono tabular-nums">
                {formatTokens(cat.value)}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Sessions Table
// ---------------------------------------------------------------------------

function SessionsTable({ sessions }: { sessions: UsageBySession[] }) {
  if (sessions.length === 0) return null;

  return (
    <Card>
      <h3 className="text-sm font-semibold text-neutral-300 mb-4">
        Top Sessions by Cost
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-neutral-500 uppercase tracking-wider border-b border-neutral-800">
              <th className="text-left pb-2 font-medium">Session</th>
              <th className="text-right pb-2 font-medium">Interactions</th>
              <th className="text-right pb-2 font-medium">Tokens</th>
              <th className="text-right pb-2 font-medium">Cost</th>
              <th className="text-right pb-2 font-medium">Last Used</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr
                key={s.session_id}
                className="border-b border-neutral-800/50 hover:bg-neutral-800/30"
              >
                <td className="py-2 text-neutral-300 font-medium">
                  {s.session_name || s.session_id.slice(0, 8)}
                </td>
                <td className="py-2 text-neutral-400 text-right font-mono tabular-nums">
                  {s.records}
                </td>
                <td className="py-2 text-neutral-400 text-right font-mono tabular-nums">
                  {formatTokens(s.total_tokens)}
                </td>
                <td className="py-2 text-amber-400 text-right font-mono tabular-nums">
                  {formatCost(s.cost_usd)}
                </td>
                <td className="py-2 text-neutral-500 text-right tabular-nums">
                  {formatTimestamp(s.last_used)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Records Table
// ---------------------------------------------------------------------------

function RecordsTable({
  data,
  page,
  onPageChange,
}: {
  data: UsageListResponse;
  page: number;
  onPageChange: (p: number) => void;
}) {
  const pageSize = 50;
  const totalPages = Math.ceil(data.total / pageSize);

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-neutral-300">
          Usage Records
        </h3>
        <span className="text-[11px] text-neutral-600 tabular-nums">
          {data.total} total
        </span>
      </div>
      {data.records.length === 0 ? (
        <p className="text-xs text-neutral-600 text-center py-6">
          No records yet. Send a chat message to start tracking.
        </p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-neutral-500 uppercase tracking-wider border-b border-neutral-800">
                  <th className="text-left pb-2 font-medium">Time</th>
                  <th className="text-left pb-2 font-medium">Session</th>
                  <th className="text-left pb-2 font-medium">Model</th>
                  <th className="text-right pb-2 font-medium">Input</th>
                  <th className="text-right pb-2 font-medium">Output</th>
                  <th className="text-right pb-2 font-medium">Total</th>
                  <th className="text-right pb-2 font-medium">Cost</th>
                  <th className="text-right pb-2 font-medium">Turns</th>
                </tr>
              </thead>
              <tbody>
                {data.records.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-neutral-800/50 hover:bg-neutral-800/30"
                  >
                    <td className="py-2 text-neutral-400 tabular-nums whitespace-nowrap">
                      {formatTimestamp(r.started_at)}
                    </td>
                    <td className="py-2 text-neutral-300">
                      {r.session_name || r.session_id.slice(0, 8)}
                    </td>
                    <td className="py-2 text-neutral-400">
                      {shortModel(r.model)}
                    </td>
                    <td className="py-2 text-neutral-400 text-right font-mono tabular-nums">
                      {formatTokens(r.input_tokens)}
                    </td>
                    <td className="py-2 text-neutral-400 text-right font-mono tabular-nums">
                      {formatTokens(r.output_tokens)}
                    </td>
                    <td className="py-2 text-neutral-300 text-right font-mono tabular-nums">
                      {formatTokens(r.total_tokens)}
                    </td>
                    <td className="py-2 text-amber-400 text-right font-mono tabular-nums">
                      {formatCost(r.cost_usd)}
                    </td>
                    <td className="py-2 text-neutral-500 text-right font-mono tabular-nums">
                      {r.num_turns}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-neutral-800">
              <span className="text-[11px] text-neutral-600 tabular-nums">
                Page {page + 1} of {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => onPageChange(page - 1)}
                  disabled={page === 0}
                  className="px-2 py-1 text-[11px] rounded border border-neutral-800 text-neutral-500 hover:text-neutral-300 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Prev
                </button>
                <button
                  onClick={() => onPageChange(page + 1)}
                  disabled={page >= totalPages - 1}
                  className="px-2 py-1 text-[11px] rounded border border-neutral-800 text-neutral-500 hover:text-neutral-300 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function UsagePage() {
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [timeseries, setTimeseries] = useState<UsageTimeBucket[]>([]);
  const [byModel, setByModel] = useState<UsageByModel[]>([]);
  const [bySession, setBySession] = useState<UsageBySession[]>([]);
  const [records, setRecords] = useState<UsageListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [timeRange, setTimeRange] = useState<keyof typeof TIME_RANGES>("7d");
  const [page, setPage] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const range = TIME_RANGES[timeRange];
      const since =
        range.seconds > 0 ? Date.now() / 1000 - range.seconds : undefined;

      const [s, ts, bm, bs, r] = await Promise.all([
        api.usage.summary({ since }),
        api.usage.timeseries({ since, bucket: range.bucket }),
        api.usage.byModel({ since }),
        api.usage.bySession({ since }),
        api.usage.list({ since, limit: 50, offset: page * 50 }),
      ]);

      setSummary(s);
      setTimeseries(ts);
      setByModel(bm);
      setBySession(bs);
      setRecords(r);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch usage data");
    } finally {
      setLoading(false);
    }
  }, [timeRange, page]);

  useEffect(() => {
    setLoading(true);
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchData, 15_000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, fetchData]);

  // ------- Loading -------
  if (loading && !summary) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-screen bg-neutral-950">
        <div className="flex items-center gap-3 text-neutral-500">
          <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
          <span className="text-sm">Loading usage data...</span>
        </div>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-screen bg-neutral-950">
        <div className="text-center space-y-3">
          <p className="text-sm text-red-400">{error}</p>
          <button
            onClick={fetchData}
            className="text-xs text-amber-500 hover:text-amber-400 underline underline-offset-2"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const avgCost =
    summary && summary.total_records > 0
      ? summary.total_cost_usd / summary.total_records
      : 0;

  return (
    <div className="flex-1 min-h-screen bg-neutral-950">
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-xl font-semibold text-neutral-100">Usage</h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              Token consumption, costs, and interaction history.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Time range */}
            <div className="flex rounded-lg border border-neutral-800 overflow-hidden">
              {Object.entries(TIME_RANGES).map(([key, { label }]) => (
                <button
                  key={key}
                  onClick={() => {
                    setTimeRange(key as keyof typeof TIME_RANGES);
                    setPage(0);
                  }}
                  className={classNames(
                    "px-3 py-1.5 text-xs font-medium transition-colors",
                    timeRange === key
                      ? "bg-amber-500/15 text-amber-400"
                      : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50"
                  )}
                >
                  {label}
                </button>
              ))}
            </div>

            {lastUpdated && (
              <span className="text-[11px] text-neutral-600 tabular-nums hidden sm:inline">
                Updated{" "}
                {lastUpdated.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </span>
            )}

            {/* Auto-refresh */}
            <button
              onClick={() => setAutoRefresh((v) => !v)}
              className={classNames(
                "flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors",
                autoRefresh
                  ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                  : "bg-neutral-900 border-neutral-800 text-neutral-500 hover:text-neutral-400"
              )}
            >
              <svg
                className={classNames("w-3.5 h-3.5", autoRefresh && "animate-spin")}
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182"
                />
              </svg>
              {autoRefresh ? "On" : "Auto"}
            </button>

            {/* Manual refresh */}
            <button
              onClick={fetchData}
              className="p-1.5 rounded-lg border border-neutral-800 text-neutral-500 hover:text-neutral-300 hover:border-neutral-700 transition-colors"
              title="Refresh now"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-2 text-xs text-red-400">
            {error}
          </div>
        )}

        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <SummaryCard
              label="Total Tokens"
              value={formatTokens(summary.total_tokens)}
              sub={`${summary.total_records} interactions`}
            />
            <SummaryCard
              label="Total Cost"
              value={formatCost(summary.total_cost_usd)}
              sub={`${summary.total_turns} turns`}
              color="text-amber-400"
            />
            <SummaryCard
              label="Interactions"
              value={summary.total_records.toLocaleString()}
              sub={
                summary.earliest
                  ? `Since ${formatTimestamp(summary.earliest)}`
                  : undefined
              }
            />
            <SummaryCard
              label="Avg Cost / Interaction"
              value={formatCost(avgCost)}
              sub={`~${formatTokens(
                summary.total_records > 0
                  ? Math.round(summary.total_tokens / summary.total_records)
                  : 0
              )} tokens avg`}
            />
          </div>
        )}

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <TokenBars data={timeseries} />
          <ModelDonut models={byModel} />
        </div>

        {/* Token Breakdown */}
        {summary && <TokenBreakdown summary={summary} />}

        {/* Sessions */}
        <SessionsTable sessions={bySession} />

        {/* Records */}
        {records && (
          <RecordsTable data={records} page={page} onPageChange={setPage} />
        )}
      </div>
    </div>
  );
}
