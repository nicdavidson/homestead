"use client";

import type { Session } from "@/lib/types";

interface SessionCardProps {
  session: Session;
  onActivate: () => void;
  onDelete: () => void;
  onChangeModel: (model: string) => void;
}

function timeAgo(dateStr: string): string {
  try {
    const seconds = Math.floor(
      (Date.now() - new Date(dateStr).getTime()) / 1000
    );
    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  } catch {
    return "unknown";
  }
}

const MODEL_COLORS: Record<string, string> = {
  opus: "bg-purple-500/15 text-purple-400",
  sonnet: "bg-blue-500/15 text-blue-400",
  haiku: "bg-emerald-500/15 text-emerald-400",
};

function getModelColor(model: string): string {
  const lower = model.toLowerCase();
  for (const [key, cls] of Object.entries(MODEL_COLORS)) {
    if (lower.includes(key)) return cls;
  }
  return "bg-neutral-700/50 text-neutral-300";
}

export function SessionCard({
  session,
  onActivate,
  onDelete,
  onChangeModel,
}: SessionCardProps) {
  return (
    <div
      className={`rounded-xl border p-4 transition-colors ${
        session.is_active
          ? "border-amber-500/50 bg-amber-500/5"
          : "border-neutral-800 bg-neutral-900 hover:border-neutral-700"
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {session.is_active && (
            <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
          )}
          <h3 className="font-semibold text-neutral-100 text-sm">
            {session.name}
          </h3>
        </div>
        <span
          className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${getModelColor(session.model)}`}
        >
          {session.model}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-neutral-500 mb-4">
        <div>
          Messages:{" "}
          <span className="text-neutral-300">{session.message_count}</span>
        </div>
        <div>
          Chat ID: <span className="text-neutral-300">{session.chat_id}</span>
        </div>
        <div>
          Created:{" "}
          <span className="text-neutral-300">{timeAgo(session.created_at)}</span>
        </div>
        <div>
          Active:{" "}
          <span className="text-neutral-300">
            {timeAgo(session.last_active_at)}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {!session.is_active && (
          <button
            onClick={onActivate}
            className="text-xs px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 transition-colors"
          >
            Activate
          </button>
        )}
        <select
          value={session.model}
          onChange={(e) => onChangeModel(e.target.value)}
          className="text-xs px-2 py-1.5 rounded-lg bg-neutral-800 border border-neutral-700 text-neutral-300 focus:outline-none focus:border-amber-500/50"
        >
          <option value="opus">opus</option>
          <option value="sonnet">sonnet</option>
          <option value="haiku">haiku</option>
        </select>
        <button
          onClick={onDelete}
          className="text-xs px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors ml-auto"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
