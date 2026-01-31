"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface SearchResult {
  id: string;
  source: string;
  path: string;
  title: string;
  snippet: string;
  rank: number;
  updated_at: number;
}

interface MemoryStats {
  total_documents: number;
  by_source: Record<string, number>;
  last_reindex_at: number | null;
}

const SOURCE_COLORS: Record<string, string> = {
  lore: "bg-purple-500/15 text-purple-400",
  scratchpad: "bg-blue-500/15 text-blue-400",
  journal: "bg-amber-500/15 text-amber-400",
};

function formatDate(ts: number): string {
  if (!ts) return "";
  return new Date(ts * 1000).toLocaleDateString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MemoryPage() {
  const [query, setQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState<string>("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function handleSearch(e?: React.FormEvent) {
    e?.preventDefault();
    if (!query.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.memory.search({
        q: query.trim(),
        source: sourceFilter || undefined,
        limit: 20,
      });
      setResults(data);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  async function loadStats() {
    try {
      const data = await api.memory.stats();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load stats");
    }
  }

  async function handleReindex() {
    try {
      setReindexing(true);
      setError(null);
      const result = await api.memory.reindex();
      await loadStats();
      setError(null);
      alert(
        `Reindex complete: ${result.scanned} scanned, ${result.added} added, ${result.updated} updated, ${result.removed} removed`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reindex failed");
    } finally {
      setReindexing(false);
    }
  }

  // Load stats on first render
  useState(() => {
    loadStats();
  });

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-neutral-800">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-lg font-semibold text-neutral-100">
              Cronicle Memory
            </h1>
            <p className="text-xs text-neutral-500 mt-0.5">
              Search across lore, scratchpad, and journal
            </p>
          </div>
          <button
            onClick={handleReindex}
            disabled={reindexing}
            className="px-4 py-1.5 rounded-lg bg-neutral-800 text-neutral-300 text-sm hover:bg-neutral-700 disabled:opacity-40 transition-colors"
          >
            {reindexing ? "Reindexing..." : "Reindex"}
          </button>
        </div>

        {/* Search bar */}
        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="flex-1 relative">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
              />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search memory..."
              className="w-full bg-neutral-900 border border-neutral-800 rounded-lg pl-10 pr-4 py-2 text-sm text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-amber-500/40"
              autoFocus
            />
          </div>

          {/* Source filter */}
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-sm text-neutral-300 focus:outline-none focus:border-amber-500/40"
          >
            <option value="">All sources</option>
            <option value="lore">Lore</option>
            <option value="scratchpad">Scratchpad</option>
            <option value="journal">Journal</option>
          </select>

          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-5 py-2 rounded-lg bg-amber-500 text-neutral-950 font-medium text-sm hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="px-6 py-2 bg-red-500/10 border-b border-red-500/20 text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-300 text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {!searched ? (
          /* Stats view when no search yet */
          <div className="p-6">
            {stats && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                <div className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-4">
                  <div className="text-2xl font-semibold text-neutral-100">
                    {stats.total_documents}
                  </div>
                  <div className="text-xs text-neutral-500 mt-1">
                    Total documents
                  </div>
                </div>
                {Object.entries(stats.by_source).map(([source, count]) => (
                  <div
                    key={source}
                    className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-4"
                  >
                    <div className="text-2xl font-semibold text-neutral-100">
                      {count}
                    </div>
                    <div className="text-xs text-neutral-500 mt-1 capitalize">
                      {source}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {stats?.last_reindex_at && (
              <p className="text-xs text-neutral-600">
                Last reindex: {formatDate(stats.last_reindex_at)}
              </p>
            )}
          </div>
        ) : results.length === 0 ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <p className="text-neutral-500 text-lg">No results</p>
              <p className="text-neutral-600 text-sm mt-1">
                Try a different query or broader terms
              </p>
            </div>
          </div>
        ) : (
          <div className="p-6 space-y-3">
            <p className="text-xs text-neutral-500 mb-4">
              {results.length} result{results.length !== 1 ? "s" : ""} for
              &ldquo;{query}&rdquo;
            </p>
            {results.map((result) => (
              <div
                key={result.id}
                className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-4 hover:border-neutral-700 transition-colors"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                      SOURCE_COLORS[result.source] ||
                      "bg-neutral-700 text-neutral-300"
                    }`}
                  >
                    {result.source}
                  </span>
                  <span className="text-xs text-neutral-500 font-mono">
                    {result.path}
                  </span>
                  {result.updated_at > 0 && (
                    <span className="text-[10px] text-neutral-600 ml-auto">
                      {formatDate(result.updated_at)}
                    </span>
                  )}
                </div>
                {result.title && (
                  <h3 className="text-sm font-medium text-neutral-200 mb-1">
                    {result.title}
                  </h3>
                )}
                <p
                  className="text-xs text-neutral-400 leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: result.snippet }}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
