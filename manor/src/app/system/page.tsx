"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type {
  HealthDetailed,
  AggregatedMetrics,
  DatabaseHealth,
  DirectoryHealth,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatBytes(sizeStr: string): string {
  // The API may return human-readable strings already; pass through.
  return sizeStr || "--";
}

function classNames(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}

const LOG_LEVEL_COLORS: Record<string, string> = {
  ERROR: "bg-red-500",
  CRITICAL: "bg-red-600",
  WARNING: "bg-amber-500",
  INFO: "bg-emerald-500",
  DEBUG: "bg-neutral-600",
};

const LOG_LEVEL_TEXT: Record<string, string> = {
  ERROR: "text-red-400",
  CRITICAL: "text-red-400",
  WARNING: "text-amber-400",
  INFO: "text-emerald-400",
  DEBUG: "text-neutral-500",
};

const TASK_STATUS_COLORS: Record<string, string> = {
  pending: "#a3a3a3",       // neutral-400
  in_progress: "#f59e0b",   // amber-500
  blocked: "#ef4444",       // red-500
  completed: "#22c55e",     // green-500
  cancelled: "#737373",     // neutral-500
};

const TASK_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  in_progress: "In Progress",
  blocked: "Blocked",
  completed: "Completed",
  cancelled: "Cancelled",
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusDot({ healthy }: { healthy: boolean }) {
  return (
    <span
      className={classNames(
        "inline-block w-2.5 h-2.5 rounded-full flex-shrink-0",
        healthy ? "bg-emerald-500" : "bg-red-500"
      )}
    />
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-sm font-semibold uppercase tracking-wider text-neutral-500 mb-3">
      {children}
    </h2>
  );
}

function Card({ children, className }: { children: React.ReactNode; className?: string }) {
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

// ---------------------------------------------------------------------------
// Health Banner
// ---------------------------------------------------------------------------

function HealthBanner({ status }: { status: string }) {
  const isHealthy = status === "healthy";
  return (
    <div
      className={classNames(
        "rounded-xl px-5 py-3 flex items-center gap-3 text-sm font-medium border",
        isHealthy
          ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
          : "bg-amber-500/10 border-amber-500/20 text-amber-400"
      )}
    >
      <span className="relative flex h-3 w-3">
        <span
          className={classNames(
            "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
            isHealthy ? "bg-emerald-400" : "bg-amber-400"
          )}
        />
        <span
          className={classNames(
            "relative inline-flex rounded-full h-3 w-3",
            isHealthy ? "bg-emerald-500" : "bg-amber-500"
          )}
        />
      </span>
      {isHealthy ? "All Systems Operational" : "System Degraded"}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Database Health Grid
// ---------------------------------------------------------------------------

function DatabaseGrid({ databases }: { databases: DatabaseHealth[] }) {
  return (
    <div>
      <SectionHeading>Databases</SectionHeading>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
        {databases.map((db) => (
          <Card key={db.name} className="flex items-start gap-3">
            <StatusDot healthy={db.status === "healthy"} />
            <div className="min-w-0">
              <p className="text-sm font-medium text-neutral-200 truncate">
                {db.name}
              </p>
              <p className="text-xs text-neutral-500 mt-0.5">
                {formatBytes(db.size)}
              </p>
              <p
                className={classNames(
                  "text-[11px] mt-1 font-medium",
                  db.status === "healthy"
                    ? "text-emerald-400"
                    : "text-red-400"
                )}
              >
                {db.status === "healthy" ? "Healthy" : "Unhealthy"}
              </p>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Directory Status
// ---------------------------------------------------------------------------

function DirectoryGrid({ directories }: { directories: DirectoryHealth[] }) {
  return (
    <div>
      <SectionHeading>Directories</SectionHeading>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {directories.map((dir) => (
          <Card key={dir.name} className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-amber-500/10 flex items-center justify-center flex-shrink-0">
              <svg
                className="w-4.5 h-4.5 text-amber-500"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z"
                />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium text-neutral-200 capitalize">
                {dir.name}
              </p>
              <p className="text-xs text-neutral-500">
                {dir.file_count} {dir.file_count === 1 ? "file" : "files"}
              </p>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Logs Bar Chart
// ---------------------------------------------------------------------------

function LogsBars({ logs }: { logs: AggregatedMetrics["logs"] }) {
  const levels = ["ERROR", "WARNING", "INFO", "DEBUG"];

  const renderPeriod = (label: string, data: Record<string, number>) => {
    const max = Math.max(...levels.map((l) => data[l] || 0), 1);
    return (
      <div>
        <p className="text-xs text-neutral-500 mb-2 font-medium">{label}</p>
        <div className="space-y-1.5">
          {levels.map((level) => {
            const count = data[level] || 0;
            const pct = Math.max((count / max) * 100, count > 0 ? 4 : 0);
            return (
              <div key={level} className="flex items-center gap-2">
                <span
                  className={classNames(
                    "text-[11px] w-16 text-right font-mono",
                    LOG_LEVEL_TEXT[level] || "text-neutral-500"
                  )}
                >
                  {level}
                </span>
                <div className="flex-1 h-4 bg-neutral-800 rounded overflow-hidden">
                  <div
                    className={classNames(
                      "h-full rounded transition-all duration-500",
                      LOG_LEVEL_COLORS[level] || "bg-neutral-600"
                    )}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-xs text-neutral-400 w-10 text-right font-mono tabular-nums">
                  {count.toLocaleString()}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <Card>
      <h3 className="text-sm font-semibold text-neutral-300 mb-4">Logs</h3>
      <div className="space-y-5">
        {renderPeriod("Last 1 hour", logs.last_1h)}
        {renderPeriod("Last 24 hours", logs.last_24h)}
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Task Donut
// ---------------------------------------------------------------------------

function TaskDonut({ tasks }: { tasks: AggregatedMetrics["tasks"] }) {
  const statuses = Object.keys(TASK_STATUS_COLORS);
  const byStatus = tasks?.by_status ?? {};
  const total = tasks?.total || 1;

  // Build conic-gradient segments
  let accumulated = 0;
  const segments: string[] = [];
  statuses.forEach((status) => {
    const count = byStatus[status] || 0;
    const pct = (count / total) * 100;
    const color = TASK_STATUS_COLORS[status];
    segments.push(`${color} ${accumulated}% ${accumulated + pct}%`);
    accumulated += pct;
  });

  // If no tasks, show neutral ring
  const gradient =
    tasks.total === 0
      ? "conic-gradient(#404040 0% 100%)"
      : `conic-gradient(${segments.join(", ")})`;

  return (
    <Card>
      <h3 className="text-sm font-semibold text-neutral-300 mb-4">Tasks</h3>
      <div className="flex items-center gap-6">
        {/* Donut */}
        <div className="relative w-28 h-28 flex-shrink-0">
          <div
            className="w-full h-full rounded-full"
            style={{ background: gradient }}
          />
          <div className="absolute inset-3 bg-neutral-900 rounded-full flex items-center justify-center">
            <span className="text-xl font-bold text-neutral-100 tabular-nums">
              {tasks.total}
            </span>
          </div>
        </div>
        {/* Legend */}
        <div className="space-y-1.5 min-w-0">
          {statuses.map((status) => {
            const count = tasks.by_status[status] || 0;
            if (count === 0 && tasks.total > 0) return null;
            return (
              <div key={status} className="flex items-center gap-2 text-xs">
                <span
                  className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                  style={{ backgroundColor: TASK_STATUS_COLORS[status] }}
                />
                <span className="text-neutral-400">
                  {TASK_STATUS_LABELS[status] || status}
                </span>
                <span className="text-neutral-500 ml-auto font-mono tabular-nums">
                  {count}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Stat Card
// ---------------------------------------------------------------------------

function StatCard({
  title,
  stats,
}: {
  title: string;
  stats: { label: string; value: number | string; color?: string }[];
}) {
  return (
    <Card>
      <h3 className="text-sm font-semibold text-neutral-300 mb-4">{title}</h3>
      <div className="space-y-3">
        {stats.map((s) => (
          <div key={s.label} className="flex items-center justify-between">
            <span className="text-xs text-neutral-500">{s.label}</span>
            <span
              className={classNames(
                "text-sm font-semibold tabular-nums font-mono",
                s.color || "text-neutral-200"
              )}
            >
              {typeof s.value === "number" ? s.value.toLocaleString() : s.value}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// System Info
// ---------------------------------------------------------------------------

function SystemInfo({
  system,
}: {
  system: HealthDetailed["system"];
}) {
  const items = [
    { label: "Python", value: system.python_version },
    { label: "Platform", value: system.platform },
    { label: "Hostname", value: system.hostname },
  ];

  return (
    <div>
      <SectionHeading>System Info</SectionHeading>
      <Card>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {items.map((item) => (
            <div key={item.label}>
              <p className="text-[11px] uppercase tracking-wider text-neutral-600 mb-1">
                {item.label}
              </p>
              <p className="text-sm text-neutral-300 font-mono truncate">
                {item.value}
              </p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SystemPage() {
  const [health, setHealth] = useState<HealthDetailed | null>(null);
  const [metrics, setMetrics] = useState<AggregatedMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [h, m] = await Promise.all([
        api.health.detailed(),
        api.metrics.get(),
      ]);
      setHealth(h);
      setMetrics(m);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchData, 10_000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, fetchData]);

  // ------- Loading / Error states -------

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-screen bg-neutral-950">
        <div className="flex items-center gap-3 text-neutral-500">
          <svg
            className="w-5 h-5 animate-spin"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          <span className="text-sm">Loading system status...</span>
        </div>
      </div>
    );
  }

  if (error && !health) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-screen bg-neutral-950">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 mx-auto rounded-full bg-red-500/10 flex items-center justify-center">
            <svg
              className="w-6 h-6 text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
              />
            </svg>
          </div>
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

  // ------- Main render -------

  return (
    <div className="flex-1 min-h-screen bg-neutral-950">
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-neutral-100">
              System Overview
            </h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              Health, metrics, and diagnostics for your Homestead.
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* Last updated */}
            {lastUpdated && (
              <span className="text-[11px] text-neutral-600 tabular-nums">
                Updated{" "}
                {lastUpdated.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </span>
            )}
            {/* Auto-refresh toggle */}
            <button
              onClick={() => setAutoRefresh((v) => !v)}
              className={classNames(
                "flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors",
                autoRefresh
                  ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                  : "bg-neutral-900 border-neutral-800 text-neutral-500 hover:text-neutral-400 hover:border-neutral-700"
              )}
            >
              <svg
                className={classNames(
                  "w-3.5 h-3.5",
                  autoRefresh && "animate-spin"
                )}
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
              {autoRefresh ? "Auto-refresh on" : "Auto-refresh"}
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

        {/* Error banner (non-blocking) */}
        {error && (
          <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-2 text-xs text-red-400">
            {error}
          </div>
        )}

        {/* Health Banner */}
        {health && <HealthBanner status={health.status} />}

        {/* Database Health */}
        {health && health.databases.length > 0 && (
          <DatabaseGrid databases={health.databases} />
        )}

        {/* Directories */}
        {health && health.directories.length > 0 && (
          <DirectoryGrid directories={health.directories} />
        )}

        {/* Metrics Grid */}
        {metrics && (
          <div>
            <SectionHeading>Metrics</SectionHeading>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Logs */}
              <LogsBars logs={metrics.logs} />

              {/* Tasks Donut */}
              <TaskDonut tasks={metrics.tasks} />

              {/* Sessions */}
              <StatCard
                title="Sessions"
                stats={[
                  { label: "Total Sessions", value: metrics.sessions.total },
                  {
                    label: "Active",
                    value: metrics.sessions.active,
                    color: "text-emerald-400",
                  },
                  {
                    label: "Total Messages",
                    value: metrics.sessions.total_messages,
                  },
                ]}
              />

              {/* Jobs */}
              <StatCard
                title="Jobs"
                stats={[
                  { label: "Total Jobs", value: metrics.jobs.total },
                  {
                    label: "Enabled",
                    value: metrics.jobs.enabled,
                    color: "text-emerald-400",
                  },
                  { label: "Total Runs", value: metrics.jobs.total_runs },
                ]}
              />

              {/* Outbox */}
              <StatCard
                title="Outbox"
                stats={[
                  {
                    label: "Pending",
                    value: metrics.outbox.pending,
                    color: "text-amber-400",
                  },
                  {
                    label: "Sent",
                    value: metrics.outbox.sent,
                    color: "text-emerald-400",
                  },
                  {
                    label: "Failed",
                    value: metrics.outbox.failed,
                    color: metrics.outbox.failed > 0
                      ? "text-red-400"
                      : "text-neutral-200",
                  },
                ]}
              />
            </div>
          </div>
        )}

        {/* System Info */}
        {health && <SystemInfo system={health.system} />}
      </div>
    </div>
  );
}
