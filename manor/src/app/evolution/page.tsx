"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface TimelineEntry {
  id: string;
  title: string;
  description: string;
  file_paths: string[];
  commit_sha: string;
  applied_at: number;
  created_at: number;
  files: { file_path: string; diff: string }[];
}

export default function EvolutionPage() {
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterPrefix, setFilterPrefix] = useState<string>("");

  async function loadTimeline() {
    try {
      setLoading(true);
      const params: { file_path?: string; limit?: number } = { limit: 100 };
      if (filterPrefix) params.file_path = filterPrefix;
      const data = await api.proposals.timeline(params);
      setEntries(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load timeline");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTimeline();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterPrefix]);

  const filters = [
    { label: "All", value: "" },
    { label: "Lore", value: "lore/" },
    { label: "Herald", value: "packages/herald" },
    { label: "Manor", value: "manor/" },
    { label: "MCP", value: "packages/mcp" },
  ];

  // Stats
  const totalChanges = entries.length;
  const lastChange = entries[0]?.applied_at
    ? new Date(entries[0].applied_at * 1000)
    : null;
  const fileCounts: Record<string, number> = {};
  for (const e of entries) {
    for (const fp of e.file_paths) {
      fileCounts[fp] = (fileCounts[fp] || 0) + 1;
    }
  }
  const topFiles = Object.entries(fileCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  function formatDate(ts: number) {
    return new Date(ts * 1000).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-neutral-100">Evolution</h1>
          <p className="text-sm text-neutral-500 mt-1">
            A trail of every change applied to the system
          </p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-4">
            <p className="text-xs text-neutral-500 uppercase tracking-wider">
              Total Changes
            </p>
            <p className="text-2xl font-bold text-neutral-100 mt-1">
              {totalChanges}
            </p>
          </div>
          <div className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-4">
            <p className="text-xs text-neutral-500 uppercase tracking-wider">
              Last Change
            </p>
            <p className="text-sm font-medium text-neutral-200 mt-2">
              {lastChange
                ? lastChange.toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })
                : "None"}
            </p>
          </div>
          <div className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-4">
            <p className="text-xs text-neutral-500 uppercase tracking-wider">
              Most Changed
            </p>
            <p className="text-sm font-medium text-neutral-200 mt-2 truncate">
              {topFiles[0]?.[0] || "—"}
            </p>
          </div>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2 mb-6">
          {filters.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilterPrefix(f.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filterPrefix === f.value
                  ? "bg-amber-500/15 text-amber-500"
                  : "bg-neutral-800/50 text-neutral-400 hover:text-neutral-200"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 px-4 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Timeline */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-20 text-neutral-500">
            <p className="text-lg">No applied changes yet</p>
            <p className="text-sm mt-1">
              Proposals will appear here once approved and applied
            </p>
          </div>
        ) : (
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-4 top-2 bottom-2 w-px bg-neutral-800" />

            <div className="space-y-4">
              {entries.map((entry) => {
                const isExpanded = expandedId === entry.id;
                const isLore = entry.file_paths.some((fp) =>
                  fp.startsWith("lore/")
                );

                return (
                  <div key={entry.id} className="relative pl-10">
                    {/* Dot */}
                    <div
                      className={`absolute left-3 top-4 w-3 h-3 rounded-full border-2 ${
                        isLore
                          ? "bg-purple-500/30 border-purple-500"
                          : "bg-amber-500/30 border-amber-500"
                      }`}
                    />

                    <button
                      onClick={() =>
                        setExpandedId(isExpanded ? null : entry.id)
                      }
                      className="w-full text-left bg-neutral-900/50 border border-neutral-800 rounded-xl p-4 hover:border-neutral-700 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span
                              className={`text-[9px] px-1.5 py-0.5 rounded-full ${
                                isLore
                                  ? "bg-purple-500/15 text-purple-400"
                                  : "bg-amber-500/15 text-amber-400"
                              }`}
                            >
                              {isLore ? "lore" : "code"}
                            </span>
                            <span className="text-xs text-neutral-500">
                              {formatDate(entry.applied_at)}
                            </span>
                          </div>
                          <h3 className="text-sm font-medium text-neutral-200 truncate">
                            {entry.title}
                          </h3>
                          {entry.description && (
                            <p className="text-xs text-neutral-500 mt-1 line-clamp-2">
                              {entry.description}
                            </p>
                          )}
                          <div className="flex flex-wrap gap-1 mt-2">
                            {entry.file_paths.map((fp) => (
                              <span
                                key={fp}
                                className="text-[10px] px-1.5 py-0.5 bg-neutral-800 text-neutral-400 rounded"
                              >
                                {fp}
                              </span>
                            ))}
                          </div>
                        </div>
                        <div className="shrink-0 text-neutral-600">
                          <svg
                            className={`w-4 h-4 transition-transform ${
                              isExpanded ? "rotate-180" : ""
                            }`}
                            fill="none"
                            viewBox="0 0 24 24"
                            strokeWidth={2}
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="m19.5 8.25-7.5 7.5-7.5-7.5"
                            />
                          </svg>
                        </div>
                      </div>

                      {/* Expanded diff */}
                      {isExpanded && entry.files.length > 0 && (
                        <div className="mt-4 space-y-3">
                          {entry.files.map((f) => (
                            <div
                              key={f.file_path}
                              className="bg-neutral-950 border border-neutral-800 rounded-lg overflow-hidden"
                            >
                              <div className="px-3 py-1.5 bg-neutral-900 border-b border-neutral-800 text-xs text-neutral-400 font-mono">
                                {f.file_path}
                              </div>
                              <pre className="p-3 text-[11px] font-mono leading-relaxed overflow-x-auto max-h-80 text-neutral-300">
                                {f.diff || "(no diff available)"}
                              </pre>
                            </div>
                          ))}
                          {entry.commit_sha && (
                            <p className="text-[10px] text-neutral-600 font-mono">
                              commit {entry.commit_sha.slice(0, 12)}
                            </p>
                          )}
                        </div>
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
