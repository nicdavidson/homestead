"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";

const SCHEDULE_TYPES = ["cron", "interval", "once"] as const;
const ACTION_TYPES = ["outbox", "command", "webhook"] as const;

const ACTION_STYLES: Record<string, string> = {
  outbox: "bg-amber-500/15 text-amber-400",
  command: "bg-blue-500/15 text-blue-400",
  webhook: "bg-purple-500/15 text-purple-400",
};

function formatSchedule(type: string, value: string): string {
  switch (type) {
    case "interval": {
      const seconds = parseInt(value, 10);
      if (isNaN(seconds)) return value;
      if (seconds < 60) return `Every ${seconds}s`;
      if (seconds < 3600) return `Every ${Math.round(seconds / 60)}m`;
      if (seconds < 86400) return `Every ${Math.round(seconds / 3600)}h`;
      return `Every ${Math.round(seconds / 86400)}d`;
    }
    case "cron":
      return `Cron: ${value}`;
    case "once":
      return `Once: ${value}`;
    default:
      return value;
  }
}

function formatDate(d: string | null): string {
  if (!d) return "--";
  return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [summary, setSummary] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create / Edit
  const [showCreate, setShowCreate] = useState(false);
  const [editingJob, setEditingJob] = useState<Job | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    schedule_type: "interval" as Job["schedule_type"],
    schedule_value: "",
    action_type: "command" as Job["action_type"],
    action_config: "{}",
    tags: "",
  });
  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [jobData, summaryData] = await Promise.all([api.jobs.list(), api.jobs.summary()]);
      setJobs(jobData);
      setSummary(summaryData);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  function openCreate() {
    setEditingJob(null);
    setForm({ name: "", description: "", schedule_type: "interval", schedule_value: "", action_type: "command", action_config: "{}", tags: "" });
    setShowCreate(true);
  }

  function openEdit(job: Job) {
    setEditingJob(job);
    setForm({
      name: job.name,
      description: job.description,
      schedule_type: job.schedule_type,
      schedule_value: job.schedule_value,
      action_type: job.action_type,
      action_config: JSON.stringify(job.action_config, null, 2),
      tags: job.tags.join(", "),
    });
    setShowCreate(true);
  }

  async function handleSave() {
    if (!form.name.trim()) return;
    let config: Record<string, unknown>;
    try {
      config = JSON.parse(form.action_config);
    } catch {
      setError("Invalid JSON in action config");
      return;
    }
    setSaving(true);
    try {
      const data = {
        name: form.name,
        description: form.description,
        schedule_type: form.schedule_type,
        schedule_value: form.schedule_value,
        action_type: form.action_type,
        action_config: config,
        tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
      };
      if (editingJob) {
        await api.jobs.update(editingJob.id, data);
      } else {
        await api.jobs.create(data);
      }
      setShowCreate(false);
      setEditingJob(null);
      fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save job");
    } finally {
      setSaving(false);
    }
  }

  async function handleToggle(id: string) {
    try {
      await api.jobs.toggle(id);
      fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to toggle job");
    }
  }

  async function handleRun(id: string) {
    try {
      await api.jobs.run(id);
      fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run job");
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.jobs.delete(id);
      fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete job");
    }
  }

  const enabledCount = jobs.filter((j) => j.enabled).length;
  const disabledCount = jobs.filter((j) => !j.enabled).length;

  return (
    <div className="min-h-screen p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-100">Jobs</h1>
          <p className="text-sm text-neutral-500 mt-0.5">Scheduled tasks and automations</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-neutral-950 font-medium text-sm rounded-lg transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Job
        </button>
      </div>

      {/* Summary Bar */}
      <div className="grid grid-cols-4 gap-3">
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <span className="text-xs font-medium text-neutral-400 uppercase tracking-wide">Total Jobs</span>
          <p className="text-2xl font-bold text-neutral-200 tabular-nums mt-1">{jobs.length}</p>
        </div>
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <span className="text-xs font-medium text-emerald-400/70 uppercase tracking-wide flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Enabled
          </span>
          <p className="text-2xl font-bold text-emerald-400 tabular-nums mt-1">{enabledCount}</p>
        </div>
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <span className="text-xs font-medium text-neutral-500 uppercase tracking-wide flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-neutral-600" />
            Disabled
          </span>
          <p className="text-2xl font-bold text-neutral-500 tabular-nums mt-1">{disabledCount}</p>
        </div>
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <span className="text-xs font-medium text-neutral-400 uppercase tracking-wide">By Schedule</span>
          <div className="flex items-center gap-3 mt-1.5">
            {SCHEDULE_TYPES.map((t) => (
              <span key={t} className="text-xs text-neutral-400">
                <span className="font-bold text-neutral-300 tabular-nums">{summary[t] ?? jobs.filter((j) => j.schedule_type === t).length}</span>
                <span className="ml-1 text-neutral-600">{t}</span>
              </span>
            ))}
          </div>
        </div>
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

      {/* Jobs Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-neutral-700 border-t-amber-500" />
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-20">
          <svg className="w-12 h-12 mx-auto text-neutral-700 mb-3" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <p className="text-neutral-500 text-sm">No jobs configured</p>
        </div>
      ) : (
        <div className="rounded-lg border border-neutral-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-900/80 border-b border-neutral-800">
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide">Name</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide">Schedule</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide">Action</th>
                <th className="text-center px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide">Enabled</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide">Last Run</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide">Next Run</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide">Runs</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/60">
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-neutral-900/40 transition-colors group">
                  {/* Name */}
                  <td className="px-4 py-3">
                    <div>
                      <span className="text-neutral-200 font-medium">{job.name}</span>
                      {job.description && (
                        <p className="text-xs text-neutral-600 mt-0.5 truncate max-w-xs">{job.description}</p>
                      )}
                      {job.tags.length > 0 && (
                        <div className="flex items-center gap-1 mt-1">
                          {job.tags.map((tag) => (
                            <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-500">{tag}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </td>
                  {/* Schedule */}
                  <td className="px-4 py-3">
                    <span className="text-neutral-300 font-mono text-xs bg-neutral-800/80 px-2 py-1 rounded">
                      {formatSchedule(job.schedule_type, job.schedule_value)}
                    </span>
                  </td>
                  {/* Action */}
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${ACTION_STYLES[job.action_type]}`}>
                      {job.action_type}
                    </span>
                  </td>
                  {/* Toggle */}
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleToggle(job.id)}
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                        job.enabled ? "bg-emerald-500/30" : "bg-neutral-700"
                      }`}
                    >
                      <span
                        className={`inline-block h-3.5 w-3.5 rounded-full transition-all ${
                          job.enabled ? "translate-x-[18px] bg-emerald-400" : "translate-x-[3px] bg-neutral-500"
                        }`}
                      />
                    </button>
                  </td>
                  {/* Last Run */}
                  <td className="px-4 py-3 text-xs text-neutral-500 tabular-nums">{formatDate(job.last_run_at)}</td>
                  {/* Next Run */}
                  <td className="px-4 py-3 text-xs text-neutral-500 tabular-nums">{formatDate(job.next_run_at)}</td>
                  {/* Run Count */}
                  <td className="px-4 py-3 text-right text-xs text-neutral-400 tabular-nums font-mono">{job.run_count}</td>
                  {/* Actions */}
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => handleRun(job.id)}
                        title="Run now"
                        className="p-1.5 text-neutral-500 hover:text-amber-400 hover:bg-amber-500/10 rounded-md transition-colors"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => openEdit(job)}
                        title="Edit"
                        className="p-1.5 text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800 rounded-md transition-colors"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDelete(job.id)}
                        title="Delete"
                        className="p-1.5 text-neutral-500 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-colors"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit Job Panel */}
      {showCreate && (
        <>
          <div className="fixed inset-0 bg-black/60 z-40" onClick={() => { setShowCreate(false); setEditingJob(null); }} />
          <div className="fixed right-0 top-0 h-full w-full max-w-lg bg-neutral-950 border-l border-neutral-800 z-50 flex flex-col shadow-2xl">
            <div className="flex items-center justify-between p-5 border-b border-neutral-800">
              <h2 className="text-lg font-semibold text-neutral-100">{editingJob ? "Edit Job" : "Create Job"}</h2>
              <button onClick={() => { setShowCreate(false); setEditingJob(null); }} className="text-neutral-500 hover:text-neutral-300 transition-colors">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {/* Name */}
              <div>
                <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Job name"
                  className="w-full bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50"
                />
              </div>
              {/* Description */}
              <div>
                <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Description</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="What does this job do?"
                  rows={3}
                  className="w-full bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50 resize-none"
                />
              </div>
              {/* Schedule */}
              <div>
                <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Schedule</label>
                <div className="flex gap-2">
                  <select
                    value={form.schedule_type}
                    onChange={(e) => setForm({ ...form, schedule_type: e.target.value as Job["schedule_type"] })}
                    className="bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50"
                  >
                    {SCHEDULE_TYPES.map((s) => (
                      <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                    ))}
                  </select>
                  <input
                    type="text"
                    value={form.schedule_value}
                    onChange={(e) => setForm({ ...form, schedule_value: e.target.value })}
                    placeholder={form.schedule_type === "cron" ? "0 6 * * *" : form.schedule_type === "interval" ? "300" : "2024-01-15T06:00:00Z"}
                    className="flex-1 bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50 font-mono"
                  />
                </div>
                <p className="text-xs text-neutral-600 mt-1">
                  {form.schedule_type === "cron" && "Standard cron expression"}
                  {form.schedule_type === "interval" && "Interval in seconds"}
                  {form.schedule_type === "once" && "ISO 8601 datetime"}
                </p>
              </div>
              {/* Action */}
              <div>
                <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Action</label>
                <select
                  value={form.action_type}
                  onChange={(e) => setForm({ ...form, action_type: e.target.value as Job["action_type"] })}
                  className="w-full bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50 mb-2"
                >
                  {ACTION_TYPES.map((a) => (
                    <option key={a} value={a}>{a.charAt(0).toUpperCase() + a.slice(1)}</option>
                  ))}
                </select>
                <label className="block text-xs font-medium text-neutral-500 mb-1.5">Action Config (JSON)</label>
                <textarea
                  value={form.action_config}
                  onChange={(e) => setForm({ ...form, action_config: e.target.value })}
                  rows={6}
                  className="w-full bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50 font-mono resize-none"
                />
              </div>
              {/* Tags */}
              <div>
                <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Tags</label>
                <input
                  type="text"
                  value={form.tags}
                  onChange={(e) => setForm({ ...form, tags: e.target.value })}
                  placeholder="tag1, tag2, tag3"
                  className="w-full bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50"
                />
                <p className="text-xs text-neutral-600 mt-1">Separate tags with commas</p>
              </div>
            </div>
            <div className="p-5 border-t border-neutral-800 flex items-center gap-3">
              <button
                onClick={handleSave}
                disabled={saving || !form.name.trim()}
                className="flex-1 px-4 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:bg-neutral-800 disabled:text-neutral-600 text-neutral-950 font-medium text-sm rounded-lg transition-colors"
              >
                {saving ? "Saving..." : editingJob ? "Save Changes" : "Create Job"}
              </button>
              <button
                onClick={() => { setShowCreate(false); setEditingJob(null); }}
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
