"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

interface DashboardData {
  activeSession: { name: string; model: string; messages: number } | null;
  taskSummary: Record<string, number>;
  skillCount: number;
  usageCost24h: number;
  logSummary: Record<string, Record<string, number>>;
  jobs: { total: number; enabled: number; lastRun: string | null };
  alerts: { id: number; rule_id: string; fired_at: number; message: string; resolved: boolean }[];
  recentLogs: { timestamp: string; level: string; source: string; message: string }[];
}

const EMPTY: DashboardData = {
  activeSession: null,
  taskSummary: {},
  skillCount: 0,
  usageCost24h: 0,
  logSummary: {},
  jobs: { total: 0, enabled: 0, lastRun: null },
  alerts: [],
  recentLogs: [],
};

export default function Home() {
  const [data, setData] = useState<DashboardData>(EMPTY);
  const [loading, setLoading] = useState(true);

  async function loadDashboard() {
    const [
      sessionsRes,
      taskSumRes,
      skillsRes,
      usageSumRes,
      logSumRes,
      jobsRes,
      alertsRes,
      recentLogsRes,
    ] = await Promise.allSettled([
      api.sessions.list(),
      api.tasks.summary(),
      api.skills.list(),
      api.usage.summary({ since: Math.floor(Date.now() / 1000) - 86400 }),
      api.logs.summary(1),
      api.jobs.list(),
      api.alerts.history(5),
      api.logs.query({ hours: 1, limit: 8, level: "warning" }),
    ]);

    const sessions = sessionsRes.status === "fulfilled" ? sessionsRes.value : [];
    const active = sessions.find((s) => s.is_active);

    const taskSummary = taskSumRes.status === "fulfilled" ? taskSumRes.value : {};
    const skills = skillsRes.status === "fulfilled" ? skillsRes.value : [];
    const usageSummary = usageSumRes.status === "fulfilled" ? usageSumRes.value : null;
    const logSummary = logSumRes.status === "fulfilled" ? logSumRes.value : {};
    const jobs = jobsRes.status === "fulfilled" ? jobsRes.value : [];
    const alerts = alertsRes.status === "fulfilled" ? alertsRes.value : [];
    const recentLogs = recentLogsRes.status === "fulfilled" ? recentLogsRes.value : [];

    const enabledJobs = jobs.filter((j) => j.enabled);
    const lastRunJob = jobs
      .filter((j) => j.last_run_at)
      .sort((a, b) => new Date(b.last_run_at!).getTime() - new Date(a.last_run_at!).getTime())[0];

    setData({
      activeSession: active
        ? { name: active.name, model: active.model, messages: active.message_count }
        : null,
      taskSummary,
      skillCount: skills.length,
      usageCost24h: usageSummary?.total_cost_usd ?? 0,
      logSummary,
      jobs: {
        total: jobs.length,
        enabled: enabledJobs.length,
        lastRun: lastRunJob?.last_run_at
          ? new Date(lastRunJob.last_run_at).toLocaleString()
          : null,
      },
      alerts,
      recentLogs,
    });
    setLoading(false);
  }

  useEffect(() => {
    loadDashboard();
    const interval = setInterval(loadDashboard, 30_000);
    return () => clearInterval(interval);
  }, []);

  const pending = data.taskSummary.pending ?? 0;
  const inProgress = data.taskSummary.in_progress ?? 0;
  const totalTasks = Object.values(data.taskSummary).reduce((a, b) => a + b, 0);

  // Flatten log summary: { source: { level: count } } → { level: count }
  const logCounts: Record<string, number> = {};
  for (const source of Object.values(data.logSummary)) {
    for (const [level, count] of Object.entries(source)) {
      logCounts[level] = (logCounts[level] ?? 0) + count;
    }
  }

  return (
    <>
      <Header title="Dashboard" description="Homestead overview" />
      <main className="flex-1 overflow-y-auto p-6">
        {/* Welcome */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-neutral-100">
            Welcome back.
          </h2>
          <p className="text-neutral-500 mt-1">
            Here is what is happening across the homestead.
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
            <span className="ml-2 text-sm text-neutral-500">Loading...</span>
          </div>
        ) : (
          <>
            {/* Stats grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
              <StatCard
                label="Active Session"
                value={data.activeSession?.name ?? "none"}
                sub={
                  data.activeSession
                    ? `${data.activeSession.model} — ${data.activeSession.messages} messages`
                    : "No active session"
                }
                accent
              />
              <StatCard
                label="Tasks"
                value={String(totalTasks)}
                sub={`${pending} pending, ${inProgress} in progress`}
              />
              <StatCard
                label="Skills"
                value={String(data.skillCount)}
                sub="Loaded"
              />
              <StatCard
                label="Cost (24h)"
                value={`$${data.usageCost24h.toFixed(2)}`}
                sub="API usage"
              />
            </div>

            {/* Detail cards */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Recent logs */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-neutral-200">
                      Recent Logs
                    </h3>
                    <Badge variant="outline">Last hour</Badge>
                  </div>
                </CardHeader>
                <CardBody>
                  <div className="space-y-3">
                    {(["error", "warning", "info", "debug"] as const).map(
                      (level) =>
                        (logCounts[level] ?? 0) > 0 && (
                          <LogRow
                            key={level}
                            level={level}
                            count={logCounts[level]}
                          />
                        )
                    )}
                    {Object.keys(logCounts).length === 0 && (
                      <p className="text-sm text-neutral-500 text-center py-2">
                        No logs in the last hour
                      </p>
                    )}
                  </div>
                </CardBody>
              </Card>

              {/* Jobs */}
              <Card>
                <CardHeader>
                  <h3 className="text-sm font-semibold text-neutral-200">
                    Jobs
                  </h3>
                </CardHeader>
                <CardBody>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-neutral-400">Total</span>
                      <span className="text-sm font-mono text-neutral-300">
                        {data.jobs.total}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-neutral-400">Enabled</span>
                      <Badge variant="success">{data.jobs.enabled}</Badge>
                    </div>
                    {data.jobs.lastRun && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-neutral-400">
                          Last run
                        </span>
                        <span className="text-xs text-neutral-500">
                          {data.jobs.lastRun}
                        </span>
                      </div>
                    )}
                  </div>
                </CardBody>
              </Card>

              {/* Active alerts */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-neutral-200">
                      Alerts
                    </h3>
                    <Badge variant={data.alerts.some((a) => !a.resolved) ? "error" : "outline"}>
                      {data.alerts.filter((a) => !a.resolved).length} active
                    </Badge>
                  </div>
                </CardHeader>
                <CardBody>
                  {data.alerts.length === 0 ? (
                    <p className="text-sm text-neutral-500 text-center py-2">
                      No recent alerts
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {data.alerts.map((a) => (
                        <div
                          key={a.id}
                          className="flex items-start gap-2 text-sm"
                        >
                          <span
                            className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                              a.resolved ? "bg-neutral-600" : "bg-red-500"
                            }`}
                          />
                          <div className="flex-1 min-w-0">
                            <p className="text-neutral-300 truncate">
                              {a.message}
                            </p>
                            <p className="text-xs text-neutral-600">
                              {new Date(a.fired_at * 1000).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardBody>
              </Card>

              {/* Recent activity */}
              <Card>
                <CardHeader>
                  <h3 className="text-sm font-semibold text-neutral-200">
                    Recent Activity
                  </h3>
                </CardHeader>
                <CardBody>
                  {data.recentLogs.length === 0 ? (
                    <p className="text-sm text-neutral-500 text-center py-2">
                      No warnings or errors in the last hour
                    </p>
                  ) : (
                    <div className="space-y-2.5">
                      {data.recentLogs.map((log, i) => (
                        <ActivityRow
                          key={i}
                          time={new Date(log.timestamp).toLocaleTimeString()}
                          text={`[${log.source}] ${log.message}`}
                          type={
                            log.level === "error"
                              ? "error"
                              : log.level === "warning"
                                ? "warning"
                                : "info"
                          }
                        />
                      ))}
                    </div>
                  )}
                </CardBody>
              </Card>
            </div>
          </>
        )}
      </main>
    </>
  );
}

/* ---- Sub-components ---- */

function StatCard({
  label,
  value,
  sub,
  accent = false,
}: {
  label: string;
  value: string;
  sub: string;
  accent?: boolean;
}) {
  return (
    <Card>
      <CardBody>
        <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1">
          {label}
        </p>
        <p
          className={`text-2xl font-bold ${accent ? "text-amber-500" : "text-neutral-100"}`}
        >
          {value}
        </p>
        <p className="text-xs text-neutral-500 mt-0.5">{sub}</p>
      </CardBody>
    </Card>
  );
}

function LogRow({ level, count }: { level: string; count: number }) {
  const badgeVariant = {
    info: "default" as const,
    warning: "warning" as const,
    error: "error" as const,
    debug: "outline" as const,
  }[level] ?? ("default" as const);

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Badge variant={badgeVariant}>{level.toUpperCase()}</Badge>
      </div>
      <span className="text-sm font-mono text-neutral-300">{count}</span>
    </div>
  );
}

function ActivityRow({
  time,
  text,
  type,
}: {
  time: string;
  text: string;
  type: "info" | "success" | "warning" | "error";
}) {
  const dotColor = {
    info: "bg-neutral-500",
    success: "bg-emerald-500",
    warning: "bg-amber-500",
    error: "bg-red-500",
  }[type];

  return (
    <div className="flex items-start gap-3">
      <span
        className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${dotColor}`}
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-neutral-300 truncate">{text}</p>
      </div>
      <span className="text-[11px] text-neutral-600 shrink-0 whitespace-nowrap">
        {time}
      </span>
    </div>
  );
}
