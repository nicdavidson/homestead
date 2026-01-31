"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { Proposal } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-amber-500/15 text-amber-400",
  approved: "bg-emerald-500/15 text-emerald-400",
  rejected: "bg-red-500/15 text-red-400",
  applied: "bg-blue-500/15 text-blue-400",
  failed: "bg-red-500/15 text-red-300",
};

function timeAgo(ts: number): string {
  const s = Math.floor(Date.now() / 1000 - ts);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function DiffView({ diff }: { diff: string }) {
  const lines = diff.split("\n");
  return (
    <pre className="text-xs font-mono overflow-x-auto bg-neutral-950 rounded-lg p-4 border border-neutral-800">
      {lines.map((line, i) => {
        let cls = "text-neutral-400";
        if (line.startsWith("+") && !line.startsWith("+++"))
          cls = "text-emerald-400 bg-emerald-500/5";
        else if (line.startsWith("-") && !line.startsWith("---"))
          cls = "text-red-400 bg-red-500/5";
        else if (line.startsWith("@@")) cls = "text-blue-400";
        else if (line.startsWith("---") || line.startsWith("+++"))
          cls = "text-neutral-500 font-semibold";
        return (
          <div key={i} className={`${cls} px-1 leading-relaxed`}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadProposals = useCallback(async () => {
    try {
      setLoading(true);
      const params: { status?: string } = {};
      if (statusFilter) params.status = statusFilter;
      const data = await api.proposals.list(params);
      setProposals(data.proposals);
      setTotal(data.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load proposals");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadProposals();
  }, [loadProposals]);

  async function handleReview(id: string, status: "approved" | "rejected") {
    setActionLoading(id);
    try {
      await api.proposals.review(id, {
        status,
        review_notes: reviewNotes[id] || "",
      });
      await loadProposals();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to review proposal");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleApply(id: string) {
    if (!confirm("Apply this proposal? This will modify files and create a git commit.")) return;
    setActionLoading(id);
    try {
      await api.proposals.apply(id);
      await loadProposals();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply proposal");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this proposal?")) return;
    setActionLoading(id);
    try {
      await api.proposals.delete(id);
      await loadProposals();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete proposal");
    } finally {
      setActionLoading(null);
    }
  }

  const statuses = ["", "pending", "approved", "rejected", "applied", "failed"];

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-neutral-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-neutral-100">Proposals</h1>
          <p className="text-xs text-neutral-500 mt-0.5">
            Code change proposals from AI agents — review and approve before applying
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-sm bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-1.5 text-neutral-300 focus:outline-none focus:border-amber-500/50"
          >
            {statuses.map((s) => (
              <option key={s} value={s}>
                {s || "All statuses"}
              </option>
            ))}
          </select>
          <button
            onClick={loadProposals}
            className="px-3 py-1.5 rounded-lg bg-neutral-800 text-neutral-300 text-sm hover:bg-neutral-700 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="px-6 py-2 bg-red-500/10 border-b border-red-500/20 text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
          </div>
        ) : proposals.length === 0 ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <p className="text-neutral-500 text-lg">No proposals</p>
              <p className="text-neutral-600 text-sm mt-1">
                {statusFilter
                  ? `No ${statusFilter} proposals found`
                  : "AI agents can propose code changes via the propose_code_change MCP tool"}
              </p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-neutral-800/50">
            {proposals.map((p) => {
              const isExpanded = expandedId === p.id;
              const isLoading = actionLoading === p.id;

              return (
                <div key={p.id} className="px-6 py-4">
                  {/* Proposal header */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${STATUS_COLORS[p.status] || ""}`}>
                          {p.status}
                        </span>
                        <span className="text-[10px] text-neutral-600">
                          {timeAgo(p.created_at)}
                        </span>
                        {p.file_paths.length > 0 && (
                          <span className="text-[10px] text-neutral-600">
                            {p.file_paths.length} file{p.file_paths.length !== 1 ? "s" : ""}
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => setExpandedId(isExpanded ? null : p.id)}
                        className="text-left"
                      >
                        <h3 className="text-sm font-medium text-neutral-200 hover:text-amber-400 transition-colors">
                          {p.title}
                        </h3>
                        {p.description && (
                          <p className="text-xs text-neutral-500 mt-0.5 line-clamp-2">
                            {p.description}
                          </p>
                        )}
                      </button>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {p.status === "pending" && (
                        <>
                          <button
                            onClick={() => handleReview(p.id, "approved")}
                            disabled={isLoading}
                            className="px-3 py-1 rounded-md bg-emerald-500/15 text-emerald-400 text-xs font-medium hover:bg-emerald-500/25 disabled:opacity-40 transition-colors"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleReview(p.id, "rejected")}
                            disabled={isLoading}
                            className="px-3 py-1 rounded-md bg-red-500/15 text-red-400 text-xs font-medium hover:bg-red-500/25 disabled:opacity-40 transition-colors"
                          >
                            Reject
                          </button>
                        </>
                      )}
                      {p.status === "approved" && (
                        <button
                          onClick={() => handleApply(p.id)}
                          disabled={isLoading}
                          className="px-3 py-1 rounded-md bg-blue-500/15 text-blue-400 text-xs font-medium hover:bg-blue-500/25 disabled:opacity-40 transition-colors"
                        >
                          Apply
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(p.id)}
                        disabled={isLoading}
                        className="px-2 py-1 rounded-md text-neutral-600 text-xs hover:text-red-400 hover:bg-red-500/10 disabled:opacity-40 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  {/* Expanded content */}
                  {isExpanded && (
                    <div className="mt-4 space-y-3">
                      {/* File paths */}
                      {p.file_paths.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {p.file_paths.map((fp) => (
                            <span
                              key={fp}
                              className="text-[10px] px-2 py-0.5 rounded bg-neutral-800 text-neutral-400 font-mono"
                            >
                              {fp}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Review notes input (for pending) */}
                      {p.status === "pending" && (
                        <div>
                          <textarea
                            value={reviewNotes[p.id] || ""}
                            onChange={(e) =>
                              setReviewNotes((prev) => ({ ...prev, [p.id]: e.target.value }))
                            }
                            placeholder="Review notes (optional)..."
                            className="w-full bg-neutral-900 border border-neutral-800 rounded-lg p-3 text-sm text-neutral-200 font-mono resize-none h-16 focus:outline-none focus:border-amber-500/30"
                          />
                        </div>
                      )}

                      {/* Existing review notes */}
                      {p.review_notes && (
                        <div className="text-xs text-neutral-500 bg-neutral-900/50 rounded-lg p-3 border border-neutral-800/50">
                          <span className="font-medium text-neutral-400">Review notes:</span>{" "}
                          {p.review_notes}
                        </div>
                      )}

                      {/* Diff */}
                      <DiffView diff={p.diff} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Footer */}
        {total > 0 && (
          <div className="px-6 py-3 border-t border-neutral-800 text-xs text-neutral-600">
            {total} proposal{total !== 1 ? "s" : ""} total
          </div>
        )}
      </div>
    </div>
  );
}
