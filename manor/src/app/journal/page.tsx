"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface JournalEntry {
  date: string;
  size: number;
  modified: number;
}

function formatDate(date: string): string {
  try {
    const [y, m, d] = date.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString([], {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return date;
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function JournalPage() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  async function loadEntries() {
    try {
      setLoading(true);
      const data = await api.journal.list();
      setEntries(data);
      if (data.length > 0 && !selectedDate) {
        await loadEntry(data[0].date);
      }
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load journal"
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadEntry(date: string) {
    try {
      const data = await api.journal.get(date);
      setContent(data.content);
      setOriginalContent(data.content);
      setSelectedDate(date);
      setSuccessMsg(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load entry");
    }
  }

  useEffect(() => {
    loadEntries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSave() {
    if (!selectedDate) return;
    try {
      setSaving(true);
      await api.journal.save(selectedDate, content);
      setOriginalContent(content);
      setSuccessMsg("Saved");
      setTimeout(() => setSuccessMsg(null), 2000);
      await loadEntries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  const hasChanges = content !== originalContent;

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Entry List Sidebar */}
      <div className="w-64 shrink-0 border-r border-neutral-800 bg-neutral-900/30 flex flex-col">
        <div className="px-4 py-4 border-b border-neutral-800">
          <h1 className="text-lg font-semibold text-neutral-100">Journal</h1>
          <p className="text-xs text-neutral-500 mt-0.5">
            AI reflections and notes
          </p>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {loading ? (
            <div className="flex items-center justify-center py-10">
              <div className="w-4 h-4 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
            </div>
          ) : entries.length === 0 ? (
            <p className="px-4 py-4 text-sm text-neutral-500">
              No journal entries yet
            </p>
          ) : (
            <ul className="space-y-0.5 px-2">
              {entries.map((entry) => (
                <li key={entry.date}>
                  <button
                    onClick={() => loadEntry(entry.date)}
                    className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                      selectedDate === entry.date
                        ? "bg-amber-500/10"
                        : "hover:bg-neutral-800"
                    }`}
                  >
                    <div
                      className={`text-sm ${
                        selectedDate === entry.date
                          ? "text-amber-500 font-medium"
                          : "text-neutral-400 hover:text-neutral-200"
                      }`}
                    >
                      {entry.date}
                    </div>
                    <div className="text-[10px] text-neutral-600 mt-0.5">
                      {formatDate(entry.date)} &middot;{" "}
                      {formatSize(entry.size)}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Viewer / Editor */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {error && (
          <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/20 text-red-400 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="text-red-400 hover:text-red-300 text-xs"
            >
              Dismiss
            </button>
          </div>
        )}

        {selectedDate ? (
          <>
            <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-800">
              <div className="flex items-center gap-3">
                <h2 className="text-sm font-semibold text-neutral-200">
                  {selectedDate}
                </h2>
                <span className="text-xs text-neutral-500">
                  {formatDate(selectedDate)}
                </span>
                {hasChanges && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400">
                    Modified
                  </span>
                )}
                {successMsg && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400">
                    {successMsg}
                  </span>
                )}
              </div>
              <button
                onClick={handleSave}
                disabled={saving || !hasChanges}
                className="px-4 py-1.5 rounded-lg bg-amber-500 text-neutral-950 font-medium text-sm hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {saving ? "Saving..." : "Save"}
              </button>
            </div>

            <div className="flex-1 p-4 overflow-hidden">
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="w-full h-full bg-neutral-900 border border-neutral-800 rounded-xl p-4 text-sm text-neutral-200 font-mono leading-relaxed resize-none focus:outline-none focus:border-amber-500/30"
                spellCheck={false}
              />
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <p className="text-neutral-500 text-lg">
                {loading ? "Loading..." : "No entries yet"}
              </p>
              <p className="text-neutral-600 text-sm mt-1">
                Journal entries are created by the AI during conversations
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
