"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { EventEntry } from "@/lib/types";

const TOPIC_COLORS: Record<string, string> = {
  "task": "bg-amber-500/15 text-amber-400 border-amber-500/20",
  "session": "bg-blue-500/15 text-blue-400 border-blue-500/20",
  "job": "bg-purple-500/15 text-purple-400 border-purple-500/20",
  "outbox": "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  "agent": "bg-rose-500/15 text-rose-400 border-rose-500/20",
  "system": "bg-neutral-500/15 text-neutral-400 border-neutral-500/20",
  "skill": "bg-cyan-500/15 text-cyan-400 border-cyan-500/20",
  "lore": "bg-indigo-500/15 text-indigo-400 border-indigo-500/20",
  "config": "bg-orange-500/15 text-orange-400 border-orange-500/20",
};

const HOUR_OPTIONS = [
  { label: "1h", value: 1 },
  { label: "6h", value: 6 },
  { label: "24h", value: 24 },
  { label: "48h", value: 48 },
  { label: "7d", value: 168 },
];

function getTopicColor(topic: string): string {
  const prefix = topic.split(".")[0];
  return TOPIC_COLORS[prefix] || "bg-neutral-500/15 text-neutral-400 border-neutral-500/20";
}

function formatTimestamp(epoch: number): string {
  return new Date(epoch * 1000).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatRelative(epoch: number): string {
  const diff = Math.floor(Date.now() / 1000 - epoch);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function EventsPage() {
  const [events, setEvents] = useState<EventEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [patternFilter, setPatternFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [hoursFilter, setHoursFilter] = useState(24);

  // Expanded rows
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  // Auto-refresh
  const [autoRefresh, setAutoRefresh] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params: { pattern?: string; source?: string; hours: number } = {
        hours: hoursFilter,
      };
      if (patternFilter.trim()) params.pattern = patternFilter.trim();
      if (sourceFilter.trim()) params.source = sourceFilter.trim();
      const data = await api.events.list(params);
      setEvents(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load events");
    } finally {
      setLoading(false);
    }
  }, [patternFilter, sourceFilter, hoursFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh interval
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchData, 5000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, fetchData]);

  function toggleExpanded(id: number) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  const uniqueSources = Array.from(new Set(events.map((e) => e.source).filter(Boolean)));
  const uniqueTopicPrefixes = Array.from(
    new Set(events.map((e) => e.topic.split(".")[0]).filter(Boolean))
  );

  return (
    <div className="min-h-screen p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-100">Events</h1>
          <p className="text-sm text-neutral-500 mt-0.5">
            Event bus history &mdash; topics, sources, and payloads
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-3 py-2 text-sm rounded-lg border transition-colors ${
              autoRefresh
                ? "border-amber-500/40 bg-amber-500/10 text-amber-400"
                : "border-neutral-800 bg-neutral-900/60 text-neutral-400 hover:text-neutral-200"
            }`}
          >
            <svg
              className={`w-4 h-4 ${autoRefresh ? "animate-spin" : ""}`}
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
            {autoRefresh ? "Live" : "Auto-refresh"}
          </button>
        </div>
      </div>

      {/* Summary Bar */}
      <div className="grid grid-cols-4 gap-3">
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <span className="text-xs font-medium text-neutral-400 uppercase tracking-wide">Events</span>
          <p className="text-2xl font-bold text-neutral-200 tabular-nums mt-1">{events.length}</p>
        </div>
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <span className="text-xs font-medium text-neutral-400 uppercase tracking-wide">Topics</span>
          <p className="text-2xl font-bold text-neutral-200 tabular-nums mt-1">{uniqueTopicPrefixes.length}</p>
        </div>
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <span className="text-xs font-medium text-neutral-400 uppercase tracking-wide">Sources</span>
          <p className="text-2xl font-bold text-neutral-200 tabular-nums mt-1">{uniqueSources.length}</p>
        </div>
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <span className="text-xs font-medium text-neutral-400 uppercase tracking-wide">Time Range</span>
          <div className="flex items-center gap-1 mt-1.5">
            {HOUR_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setHoursFilter(opt.value)}
                className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                  hoursFilter === opt.value
                    ? "bg-amber-500/20 text-amber-400"
                    : "bg-neutral-800 text-neutral-500 hover:text-neutral-300"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <label className="block text-xs font-medium text-neutral-500 mb-1">Topic Pattern</label>
          <input
            type="text"
            value={patternFilter}
            onChange={(e) => setPatternFilter(e.target.value)}
            placeholder="task.*, session.created, job.*"
            className="w-full bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50 font-mono"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-500 mb-1">Source</label>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50"
          >
            <option value="">All Sources</option>
            {uniqueSources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <button
            onClick={fetchData}
            className="mt-4 px-4 py-2 text-sm text-neutral-400 hover:text-neutral-200 bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 rounded-lg transition-colors"
          >
            Apply
          </button>
        </div>
      </div>

      {/* Topic Legend */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-neutral-600 mr-1">Topics:</span>
        {uniqueTopicPrefixes.map((prefix) => (
          <button
            key={prefix}
            onClick={() => setPatternFilter(`${prefix}.*`)}
            className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium border transition-colors hover:opacity-80 ${getTopicColor(prefix)}`}
          >
            {prefix}.*
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="flex items-center gap-3 text-neutral-400">
            <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
            Loading events...
          </div>
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-20">
          <svg className="w-12 h-12 mx-auto text-neutral-700 mb-3" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z"
            />
          </svg>
          <p className="text-neutral-500 text-sm">No events found</p>
          <p className="text-neutral-600 text-xs mt-1">Try expanding the time range or changing filters</p>
        </div>
      ) : (
        <div className="rounded-lg border border-neutral-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-900/80 border-b border-neutral-800">
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide w-10" />
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide w-44">Timestamp</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide">Topic</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide w-36">Source</th>
                <th className="text-center px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide w-24">Processed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/60">
              {events.map((event) => {
                const isExpanded = expandedIds.has(event.id);
                const hasPayload =
                  event.payload && Object.keys(event.payload).length > 0;
                return (
                  <tr key={event.id} className="group">
                    <td colSpan={5} className="p-0">
                      <div
                        className={`flex items-center hover:bg-neutral-900/40 transition-colors ${
                          hasPayload ? "cursor-pointer" : ""
                        }`}
                        onClick={() => hasPayload && toggleExpanded(event.id)}
                      >
                        {/* Expand chevron */}
                        <div className="w-10 px-3 py-3 flex items-center justify-center">
                          {hasPayload && (
                            <svg
                              className={`w-3.5 h-3.5 text-neutral-600 transition-transform ${
                                isExpanded ? "rotate-90" : ""
                              }`}
                              fill="none"
                              viewBox="0 0 24 24"
                              strokeWidth={2}
                              stroke="currentColor"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                            </svg>
                          )}
                        </div>
                        {/* Timestamp */}
                        <div className="w-44 px-4 py-3">
                          <span className="text-xs text-neutral-400 tabular-nums block">
                            {formatTimestamp(event.timestamp)}
                          </span>
                          <span className="text-[10px] text-neutral-600 tabular-nums">
                            {formatRelative(event.timestamp)}
                          </span>
                        </div>
                        {/* Topic */}
                        <div className="flex-1 px-4 py-3">
                          <span
                            className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${getTopicColor(
                              event.topic
                            )}`}
                          >
                            {event.topic}
                          </span>
                        </div>
                        {/* Source */}
                        <div className="w-36 px-4 py-3">
                          <span className="text-xs text-neutral-400 font-mono">{event.source}</span>
                        </div>
                        {/* Processed */}
                        <div className="w-24 px-4 py-3 text-center">
                          {event.processed ? (
                            <span className="inline-flex w-5 h-5 items-center justify-center rounded bg-emerald-500/15">
                              <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                              </svg>
                            </span>
                          ) : (
                            <span className="inline-flex w-5 h-5 items-center justify-center rounded bg-neutral-800">
                              <span className="w-2 h-2 rounded-full bg-neutral-600" />
                            </span>
                          )}
                        </div>
                      </div>
                      {/* Expanded payload */}
                      {isExpanded && hasPayload && (
                        <div className="px-14 pb-4">
                          <div className="rounded-lg bg-neutral-950 border border-neutral-800 p-4 overflow-x-auto">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-[10px] font-medium text-neutral-500 uppercase tracking-wide">
                                Payload
                              </span>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  navigator.clipboard.writeText(
                                    JSON.stringify(event.payload, null, 2)
                                  );
                                }}
                                className="text-[10px] text-neutral-600 hover:text-neutral-400 transition-colors"
                              >
                                Copy
                              </button>
                            </div>
                            <pre className="text-xs text-neutral-300 font-mono whitespace-pre-wrap leading-relaxed">
                              {JSON.stringify(event.payload, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
