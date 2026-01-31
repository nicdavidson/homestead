"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Task } from "@/lib/types";

const STATUS_OPTIONS = ["pending", "in_progress", "blocked", "completed", "cancelled"] as const;
const PRIORITY_OPTIONS = ["low", "normal", "high", "urgent"] as const;

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-neutral-700/60 text-neutral-300",
  in_progress: "bg-amber-500/15 text-amber-400",
  blocked: "bg-red-500/15 text-red-400",
  completed: "bg-emerald-500/15 text-emerald-400",
  cancelled: "bg-neutral-600/40 text-neutral-500",
};

const STATUS_DOT: Record<string, string> = {
  pending: "bg-neutral-400",
  in_progress: "bg-amber-500",
  blocked: "bg-red-500",
  completed: "bg-emerald-500",
  cancelled: "bg-neutral-600",
};

const PRIORITY_STYLES: Record<string, string> = {
  urgent: "bg-red-500/15 text-red-400 ring-1 ring-red-500/20",
  high: "bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/20",
  normal: "bg-neutral-700/60 text-neutral-300",
  low: "bg-neutral-700/40 text-neutral-500",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Pending",
  in_progress: "In Progress",
  blocked: "Blocked",
  completed: "Completed",
  cancelled: "Cancelled",
};

const PRIORITY_LABEL: Record<string, string> = {
  urgent: "Urgent",
  high: "High",
  normal: "Normal",
  low: "Low",
};

function formatDate(d: string) {
  return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [summary, setSummary] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterStatus, setFilterStatus] = useState("");
  const [filterPriority, setFilterPriority] = useState("");
  const [filterAssignee, setFilterAssignee] = useState("");
  const [searchText, setSearchText] = useState("");

  // Expanded task
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Create panel
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ title: "", description: "", priority: "normal", assignee: "", tags: "" });
  const [creating, setCreating] = useState(false);

  // Add note
  const [noteTaskId, setNoteTaskId] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params: { status?: string; assignee?: string } = {};
      if (filterStatus) params.status = filterStatus;
      if (filterAssignee) params.assignee = filterAssignee;
      const [taskData, summaryData] = await Promise.all([api.tasks.list(params), api.tasks.summary()]);
      setTasks(taskData);
      setSummary(summaryData);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tasks");
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterAssignee]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filtered = tasks.filter((t) => {
    if (filterPriority && t.priority !== filterPriority) return false;
    if (searchText) {
      const q = searchText.toLowerCase();
      return t.title.toLowerCase().includes(q) || t.description.toLowerCase().includes(q) || t.tags.some((tg) => tg.toLowerCase().includes(q));
    }
    return true;
  });

  const assignees = Array.from(new Set(tasks.map((t) => t.assignee).filter(Boolean)));

  async function handleCreate() {
    if (!createForm.title.trim()) return;
    setCreating(true);
    try {
      await api.tasks.create({
        title: createForm.title,
        description: createForm.description,
        priority: createForm.priority as Task["priority"],
        assignee: createForm.assignee,
        tags: createForm.tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      setCreateForm({ title: "", description: "", priority: "normal", assignee: "", tags: "" });
      setShowCreate(false);
      fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create task");
    } finally {
      setCreating(false);
    }
  }

  async function handleStatusChange(id: string, status: string) {
    try {
      await api.tasks.updateStatus(id, status);
      fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update status");
    }
  }

  async function handleAddNote(id: string) {
    if (!noteText.trim()) return;
    try {
      await api.tasks.addNote(id, noteText);
      setNoteText("");
      setNoteTaskId(null);
      fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add note");
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.tasks.delete(id);
      if (expandedId === id) setExpandedId(null);
      fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete task");
    }
  }

  return (
    <div className="min-h-screen p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-100">Tasks</h1>
          <p className="text-sm text-neutral-500 mt-0.5">Manage and track work items</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-neutral-950 font-medium text-sm rounded-lg transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Task
        </button>
      </div>

      {/* Summary Bar */}
      <div className="grid grid-cols-5 gap-3">
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setFilterStatus(filterStatus === s ? "" : s)}
            className={`rounded-lg border p-3 text-left transition-all ${
              filterStatus === s ? "border-amber-500/50 bg-neutral-900 ring-1 ring-amber-500/20" : "border-neutral-800 bg-neutral-900/60 hover:border-neutral-700"
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className={`w-2 h-2 rounded-full ${STATUS_DOT[s]}`} />
              <span className="text-xs font-medium text-neutral-400 uppercase tracking-wide">{STATUS_LABEL[s]}</span>
            </div>
            <span className={`text-2xl font-bold tabular-nums ${filterStatus === s ? "text-amber-400" : "text-neutral-200"}`}>
              {summary[s] ?? 0}
            </span>
          </button>
        ))}
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="bg-neutral-800 border border-neutral-700 text-neutral-200 text-sm rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
        >
          <option value="">All Statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{STATUS_LABEL[s]}</option>
          ))}
        </select>
        <select
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value)}
          className="bg-neutral-800 border border-neutral-700 text-neutral-200 text-sm rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
        >
          <option value="">All Priorities</option>
          {PRIORITY_OPTIONS.map((p) => (
            <option key={p} value={p}>{PRIORITY_LABEL[p]}</option>
          ))}
        </select>
        <select
          value={filterAssignee}
          onChange={(e) => setFilterAssignee(e.target.value)}
          className="bg-neutral-800 border border-neutral-700 text-neutral-200 text-sm rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
        >
          <option value="">All Assignees</option>
          {assignees.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search tasks..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="w-full bg-neutral-800 border border-neutral-700 text-neutral-200 text-sm rounded-md px-3 py-1.5 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
          />
        </div>
        {(filterStatus || filterPriority || filterAssignee || searchText) && (
          <button
            onClick={() => { setFilterStatus(""); setFilterPriority(""); setFilterAssignee(""); setSearchText(""); }}
            className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors"
          >
            Clear filters
          </button>
        )}
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

      {/* Task List */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-neutral-700 border-t-amber-500" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20">
          <svg className="w-12 h-12 mx-auto text-neutral-700 mb-3" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <p className="text-neutral-500 text-sm">No tasks found</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((task) => {
            const isExpanded = expandedId === task.id;
            return (
              <div key={task.id} className={`rounded-lg border transition-all ${isExpanded ? "border-neutral-700 bg-neutral-900" : "border-neutral-800 bg-neutral-900/60 hover:border-neutral-700"}`}>
                {/* Task Row */}
                <button
                  onClick={() => setExpandedId(isExpanded ? null : task.id)}
                  className="w-full flex items-center gap-4 p-4 text-left"
                >
                  <svg className={`w-4 h-4 text-neutral-600 transition-transform flex-shrink-0 ${isExpanded ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                  </svg>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="text-sm font-medium text-neutral-100 truncate">{task.title}</span>
                      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[task.status]}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[task.status]}`} />
                        {STATUS_LABEL[task.status]}
                      </span>
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${PRIORITY_STYLES[task.priority]}`}>
                        {PRIORITY_LABEL[task.priority]}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                      {task.assignee && (
                        <span className="text-xs text-neutral-500">{task.assignee}</span>
                      )}
                      {task.tags.length > 0 && (
                        <div className="flex items-center gap-1">
                          {task.tags.slice(0, 3).map((tag) => (
                            <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-400">{tag}</span>
                          ))}
                          {task.tags.length > 3 && <span className="text-[10px] text-neutral-600">+{task.tags.length - 3}</span>}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4 flex-shrink-0">
                    {task.notes.length > 0 && (
                      <span className="text-xs text-neutral-500 flex items-center gap-1">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 0 1 1.037-.443 48.2 48.2 0 0 0 5.017-.528c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.009Z" />
                        </svg>
                        {task.notes.length}
                      </span>
                    )}
                    <span className="text-xs text-neutral-600 tabular-nums">{formatDate(task.created_at)}</span>
                  </div>
                </button>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="border-t border-neutral-800 p-4 space-y-4">
                    {/* Description */}
                    {task.description && (
                      <div>
                        <h4 className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1">Description</h4>
                        <p className="text-sm text-neutral-300 whitespace-pre-wrap">{task.description}</p>
                      </div>
                    )}

                    {/* Blockers */}
                    {task.blockers.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-2">Blockers</h4>
                        <div className="space-y-1.5">
                          {task.blockers.map((b, i) => (
                            <div key={i} className={`flex items-start gap-2 text-sm rounded-md px-3 py-2 ${b.resolved_at ? "bg-emerald-500/5 border border-emerald-500/10" : "bg-red-500/5 border border-red-500/10"}`}>
                              <span className={`mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${b.resolved_at ? "bg-emerald-500" : "bg-red-500"}`} />
                              <div>
                                <span className={b.resolved_at ? "text-neutral-500 line-through" : "text-neutral-300"}>{b.description}</span>
                                <span className="text-xs text-neutral-600 ml-2">{b.type.replace(/_/g, " ")}</span>
                                {b.resolution && <p className="text-xs text-emerald-400/70 mt-0.5">Resolved: {b.resolution}</p>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Dependencies */}
                    {task.depends_on.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1">Dependencies</h4>
                        <div className="flex flex-wrap gap-1.5">
                          {task.depends_on.map((dep) => (
                            <span key={dep} className="text-xs px-2 py-1 rounded bg-neutral-800 text-neutral-400 font-mono">{dep}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Notes */}
                    {task.notes.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-2">Notes</h4>
                        <div className="space-y-1.5">
                          {task.notes.map((note, i) => (
                            <div key={i} className="text-sm text-neutral-400 bg-neutral-800/50 rounded-md px-3 py-2 border border-neutral-800">{note}</div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Add Note */}
                    {noteTaskId === task.id ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          placeholder="Add a note..."
                          value={noteText}
                          onChange={(e) => setNoteText(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && handleAddNote(task.id)}
                          autoFocus
                          className="flex-1 bg-neutral-800 border border-neutral-700 text-neutral-200 text-sm rounded-md px-3 py-1.5 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                        />
                        <button onClick={() => handleAddNote(task.id)} className="px-3 py-1.5 bg-amber-500/15 text-amber-400 text-sm rounded-md hover:bg-amber-500/25 transition-colors">Add</button>
                        <button onClick={() => { setNoteTaskId(null); setNoteText(""); }} className="px-3 py-1.5 text-neutral-500 text-sm hover:text-neutral-300 transition-colors">Cancel</button>
                      </div>
                    ) : null}

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-2 border-t border-neutral-800/60">
                      <select
                        value={task.status}
                        onChange={(e) => handleStatusChange(task.id, e.target.value)}
                        className="bg-neutral-800 border border-neutral-700 text-neutral-300 text-xs rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                      >
                        {STATUS_OPTIONS.map((s) => (
                          <option key={s} value={s}>{STATUS_LABEL[s]}</option>
                        ))}
                      </select>
                      <button
                        onClick={() => setNoteTaskId(task.id)}
                        className="flex items-center gap-1 px-2.5 py-1 text-xs text-neutral-400 hover:text-neutral-200 bg-neutral-800 rounded-md border border-neutral-700 hover:border-neutral-600 transition-colors"
                      >
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                        </svg>
                        Note
                      </button>
                      <div className="flex-1" />
                      <button
                        onClick={() => handleDelete(task.id)}
                        className="flex items-center gap-1 px-2.5 py-1 text-xs text-red-400/70 hover:text-red-400 bg-neutral-800 rounded-md border border-neutral-700 hover:border-red-500/30 transition-colors"
                      >
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                        </svg>
                        Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Create Task Slide-out Panel */}
      {showCreate && (
        <>
          <div className="fixed inset-0 bg-black/60 z-40" onClick={() => setShowCreate(false)} />
          <div className="fixed right-0 top-0 h-full w-full max-w-lg bg-neutral-950 border-l border-neutral-800 z-50 flex flex-col shadow-2xl">
            <div className="flex items-center justify-between p-5 border-b border-neutral-800">
              <h2 className="text-lg font-semibold text-neutral-100">Create Task</h2>
              <button onClick={() => setShowCreate(false)} className="text-neutral-500 hover:text-neutral-300 transition-colors">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {/* Title */}
              <div>
                <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Title</label>
                <input
                  type="text"
                  value={createForm.title}
                  onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                  placeholder="Task title"
                  className="w-full bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50"
                />
              </div>
              {/* Description */}
              <div>
                <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Description</label>
                <textarea
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  placeholder="Describe the task..."
                  rows={5}
                  className="w-full bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50 resize-none"
                />
              </div>
              {/* Priority */}
              <div>
                <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Priority</label>
                <select
                  value={createForm.priority}
                  onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
                  className="w-full bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50"
                >
                  {PRIORITY_OPTIONS.map((p) => (
                    <option key={p} value={p}>{PRIORITY_LABEL[p]}</option>
                  ))}
                </select>
              </div>
              {/* Assignee */}
              <div>
                <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Assignee</label>
                <input
                  type="text"
                  value={createForm.assignee}
                  onChange={(e) => setCreateForm({ ...createForm, assignee: e.target.value })}
                  placeholder="Assignee name"
                  className="w-full bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50"
                />
              </div>
              {/* Tags */}
              <div>
                <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Tags</label>
                <input
                  type="text"
                  value={createForm.tags}
                  onChange={(e) => setCreateForm({ ...createForm, tags: e.target.value })}
                  placeholder="tag1, tag2, tag3"
                  className="w-full bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50"
                />
                <p className="text-xs text-neutral-600 mt-1">Separate tags with commas</p>
              </div>
            </div>
            <div className="p-5 border-t border-neutral-800 flex items-center gap-3">
              <button
                onClick={handleCreate}
                disabled={creating || !createForm.title.trim()}
                className="flex-1 px-4 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:bg-neutral-800 disabled:text-neutral-600 text-neutral-950 font-medium text-sm rounded-lg transition-colors"
              >
                {creating ? "Creating..." : "Create Task"}
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2.5 text-neutral-400 hover:text-neutral-200 text-sm font-medium rounded-lg border border-neutral-800 hover:border-neutral-700 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
