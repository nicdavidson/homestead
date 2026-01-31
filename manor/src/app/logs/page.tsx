"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { LogEntry } from "@/lib/types";

const LEVEL_STYLES: Record<string, string> = {
  INFO: "bg-blue-500/15 text-blue-400",
  WARNING: "bg-yellow-500/15 text-yellow-400",
  ERROR: "bg-red-500/15 text-red-400",
  DEBUG: "bg-neutral-700/50 text-neutral-400",
  CRITICAL: "bg-red-600/20 text-red-300",
};

function getLevelStyle(level: string): string {
  return LEVEL_STYLES[level.toUpperCase()] || "bg-neutral-700/50 text-neutral-400";
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [summary, setSummary] = useState<Record<string, Record<string, number>>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // Filters
  const [level, setLevel] = useState<string>("");
  const [source, setSource] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [hours, setHours] = useState<number>(24);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadLogs = useCallback(async () => {
    try {
      const params: Record<string, string | number> = { hours, limit: 200 };
      if (level) params.level = level;
      if (source) params.source = source;
      if (search) params.search = search;
      const data = await api.logs.query(params as Parameters<typeof api.logs.query>[0]);
      setLogs(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load logs");
    }
  }, [level, source, search, hours]);

  const loadSummary = useCallback(async () => {
    try {
      const data = await api.logs.summary(hours);
      setSummary(data);
    } catch {
      // Non-critical, just skip
    }
  }, [hours]);

  useEffect(() => {
    async function init() {
      setLoading(true);
      await Promise.all([loadLogs(), loadSummary()]);
      setLoading(false);
    }
    init();
  }, [loadLogs, loadSummary]);

  // Auto-refresh
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(() => {
        loadLogs();
        loadSummary();
      }, 5000);
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoRefresh, loadLogs, loadSummary]);

  // Derive unique sources from logs for filter dropdown
  const sources = Array.from(new Set(logs.map((l) => l.source))).sort();

  // Flatten summary for display
  const summaryTotals: Record<string, number> = {};
  Object.values(summary).forEach((sourceLevels) => {
    Object.entries(sourceLevels).forEach(([lvl, count]) => {
      summaryTotals[lvl] = (summaryTotals[lvl] || 0) + count;
    });
  });

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-neutral-100">Logs</h1>
            <p className="text-sm text-neutral-500 mt-1">
              System log viewer and analysis
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="w-4 h-4 rounded border-neutral-600 bg-neutral-800 text-amber-500 focus:ring-amber-500/25 focus:ring-offset-0"
              />
              Auto-refresh
            </label>
            <button
              onClick={() => { loadLogs(); loadSummary(); }}
              className="px-4 py-2 rounded-lg bg-neutral-800 text-neutral-300 text-sm hover:bg-neutral-700 transition-colors"
            >
              Refresh
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 text-xs">
              Dismiss
            </button>
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {(["INFO", "WARNING", "ERROR", "DEBUG"] as const).map((lvl) => (
            <div
              key={lvl}
              className="rounded-xl border border-neutral-800 bg-neutral-900 p-4"
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${getLevelStyle(lvl)}`}>
                  {lvl}
                </span>
              </div>
              <p className="text-2xl font-bold text-neutral-100 mt-2">
                {summaryTotals[lvl] || summaryTotals[lvl.toLowerCase()] || 0}
              </p>
              <p className="text-xs text-neutral-500">
                Last {hours}h
              </p>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="text-sm bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-neutral-300 focus:outline-none focus:border-amber-500/50"
          >
            <option value="">All Levels</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>

          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="text-sm bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-neutral-300 focus:outline-none focus:border-amber-500/50"
          >
            <option value="">All Sources</option>
            {sources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <select
            value={hours}
            onChange={(e) => setHours(parseInt(e.target.value, 10))}
            className="text-sm bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-neutral-300 focus:outline-none focus:border-amber-500/50"
          >
            <option value={1}>Last 1h</option>
            <option value={6}>Last 6h</option>
            <option value={24}>Last 24h</option>
            <option value={72}>Last 3d</option>
            <option value={168}>Last 7d</option>
          </select>

          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search logs..."
            className="flex-1 min-w-[200px] bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:border-amber-500/50"
          />
        </div>

        {/* Log Table */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3 text-neutral-400">
              <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
              Loading logs...
            </div>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-neutral-500 text-lg">No logs found</p>
            <p className="text-neutral-600 text-sm mt-1">
              Try adjusting your filters
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-neutral-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-800 bg-neutral-900/50">
                  <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wider">
                    Timestamp
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wider">
                    Level
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wider">
                    Source
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wider">
                    Message
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800/50">
                {logs.map((log) => (
                  <tr
                    key={log.id}
                    className="hover:bg-neutral-900/50 cursor-pointer transition-colors"
                    onClick={() =>
                      setExpandedId(expandedId === log.id ? null : log.id)
                    }
                  >
                    <td className="px-4 py-2.5 text-neutral-400 whitespace-nowrap font-mono text-xs">
                      {formatTimestamp(log.timestamp)}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${getLevelStyle(log.level)}`}
                      >
                        {log.level.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-neutral-400 text-xs">
                      {log.source}
                    </td>
                    <td className="px-4 py-2.5 text-neutral-200 max-w-md">
                      <div className="truncate">{log.message}</div>
                      {expandedId === log.id && log.data && (
                        <pre className="mt-2 p-3 rounded-lg bg-neutral-800 text-xs text-neutral-300 overflow-x-auto whitespace-pre-wrap">
                          {JSON.stringify(log.data, null, 2)}
                        </pre>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Count */}
        {!loading && logs.length > 0 && (
          <p className="text-xs text-neutral-600 mt-3 text-right">
            Showing {logs.length} entries
          </p>
        )}
      </div>
    </div>
  );
}
