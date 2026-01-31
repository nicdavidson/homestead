"use client";

import { Header } from "@/components/layout/header";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function Home() {
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

        {/* Stats grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
          <StatCard
            label="Active Session"
            value="default"
            sub="opus-4 -- 47 messages"
            accent
          />
          <StatCard label="Tasks" value="12" sub="3 pending, 2 running" />
          <StatCard label="Skills" value="8" sub="All loaded" />
          <StatCard label="Uptime" value="4h 23m" sub="Since last restart" />
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
                <LogRow level="info" count={142} />
                <LogRow level="warning" count={7} />
                <LogRow level="error" count={2} />
                <LogRow level="debug" count={891} />
              </div>
            </CardBody>
          </Card>

          {/* Agent status */}
          <Card>
            <CardHeader>
              <h3 className="text-sm font-semibold text-neutral-200">
                Agents
              </h3>
            </CardHeader>
            <CardBody>
              <div className="space-y-3">
                <AgentRow
                  name="Herald"
                  role="Conversation & routing"
                  status="online"
                />
                <AgentRow
                  name="Scribe"
                  role="Logging & memory"
                  status="idle"
                />
                <AgentRow
                  name="Watcher"
                  role="System monitoring"
                  status="offline"
                />
                <AgentRow
                  name="Steward"
                  role="Task orchestration"
                  status="online"
                />
              </div>
            </CardBody>
          </Card>

          {/* Recent activity */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <h3 className="text-sm font-semibold text-neutral-200">
                Recent Activity
              </h3>
            </CardHeader>
            <CardBody>
              <div className="space-y-2.5">
                <ActivityRow
                  time="2 min ago"
                  text="Herald processed user message in session 'default'"
                  type="info"
                />
                <ActivityRow
                  time="5 min ago"
                  text="Scribe wrote 3 new lore entries"
                  type="info"
                />
                <ActivityRow
                  time="12 min ago"
                  text="Task 'daily-digest' completed successfully"
                  type="success"
                />
                <ActivityRow
                  time="1 hour ago"
                  text="Config reloaded: model updated to opus-4"
                  type="warning"
                />
                <ActivityRow
                  time="2 hours ago"
                  text="Watcher detected high memory usage (82%)"
                  type="error"
                />
              </div>
            </CardBody>
          </Card>
        </div>
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

function AgentRow({
  name,
  role,
  status,
}: {
  name: string;
  role: string;
  status: "online" | "idle" | "offline";
}) {
  const statusColor = {
    online: "bg-emerald-500",
    idle: "bg-amber-500",
    offline: "bg-neutral-600",
  }[status];

  const statusLabel = {
    online: "success" as const,
    idle: "warning" as const,
    offline: "outline" as const,
  }[status];

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className={`h-2 w-2 rounded-full ${statusColor}`} />
        <div>
          <p className="text-sm font-medium text-neutral-200">{name}</p>
          <p className="text-xs text-neutral-500">{role}</p>
        </div>
      </div>
      <Badge variant={statusLabel}>{status}</Badge>
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
