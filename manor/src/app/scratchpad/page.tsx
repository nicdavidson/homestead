"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface ScratchpadFile {
  name: string;
  size: number;
  modified: string;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

export default function ScratchpadPage() {
  const [files, setFiles] = useState<ScratchpadFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newFileName, setNewFileName] = useState("");

  async function loadFiles() {
    try {
      setLoading(true);
      const data = await api.scratchpad.list();
      setFiles(data);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load scratchpad"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFiles();
  }, []);

  async function loadFileContent(name: string) {
    try {
      const data = await api.scratchpad.get(name);
      setContent(data.content);
      setOriginalContent(data.content);
      setSelectedFile(name);
      setSuccessMsg(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load file");
    }
  }

  async function handleSave() {
    if (!selectedFile) return;
    try {
      setSaving(true);
      await api.scratchpad.save(selectedFile, content);
      setOriginalContent(content);
      setSuccessMsg("Saved");
      setTimeout(() => setSuccessMsg(null), 2000);
      await loadFiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreate() {
    if (!newFileName.trim()) return;
    try {
      await api.scratchpad.save(newFileName.trim(), "");
      setShowCreate(false);
      setNewFileName("");
      await loadFiles();
      await loadFileContent(newFileName.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create file");
    }
  }

  async function handleDelete(name: string) {
    if (!confirm(`Delete "${name}"?`)) return;
    try {
      await api.scratchpad.delete(name);
      if (selectedFile === name) {
        setSelectedFile(null);
        setContent("");
        setOriginalContent("");
      }
      await loadFiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete file");
    }
  }

  const hasChanges = content !== originalContent;

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* File List Sidebar */}
      <div className="w-64 shrink-0 border-r border-neutral-800 bg-neutral-900/30 flex flex-col">
        <div className="px-4 py-4 border-b border-neutral-800">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold text-neutral-100">
                Scratchpad
              </h1>
              <p className="text-xs text-neutral-500 mt-0.5">
                Quick notes and drafts
              </p>
            </div>
            <button
              onClick={() => setShowCreate(!showCreate)}
              className="w-7 h-7 rounded-lg bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 flex items-center justify-center text-lg transition-colors"
            >
              +
            </button>
          </div>

          {showCreate && (
            <div className="mt-3 flex gap-2">
              <input
                type="text"
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                placeholder="filename"
                className="flex-1 bg-neutral-800 border border-neutral-700 rounded-lg px-2 py-1.5 text-xs text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:border-amber-500/50"
                autoFocus
              />
              <button
                onClick={handleCreate}
                disabled={!newFileName.trim()}
                className="px-2 py-1.5 rounded-lg bg-amber-500 text-neutral-950 text-xs font-medium hover:bg-amber-400 disabled:opacity-40 transition-colors"
              >
                Add
              </button>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {loading ? (
            <div className="flex items-center justify-center py-10">
              <div className="w-4 h-4 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
            </div>
          ) : files.length === 0 ? (
            <p className="px-4 py-4 text-sm text-neutral-500">
              No scratchpad files
            </p>
          ) : (
            <ul className="space-y-0.5 px-2">
              {files.map((file) => (
                <li key={file.name} className="group">
                  <div
                    className={`flex items-center justify-between px-3 py-2 rounded-lg transition-colors cursor-pointer ${
                      selectedFile === file.name
                        ? "bg-amber-500/10"
                        : "hover:bg-neutral-800"
                    }`}
                  >
                    <button
                      onClick={() => loadFileContent(file.name)}
                      className={`flex-1 text-left ${
                        selectedFile === file.name
                          ? "text-amber-500 font-medium"
                          : "text-neutral-400 hover:text-neutral-200"
                      }`}
                    >
                      <div className="text-sm">{file.name}</div>
                      <div className="text-[10px] text-neutral-600 mt-0.5">
                        {formatSize(file.size)} &middot;{" "}
                        {formatDate(file.modified)}
                      </div>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(file.name);
                      }}
                      className="opacity-0 group-hover:opacity-100 text-neutral-600 hover:text-red-400 text-xs transition-opacity ml-2"
                    >
                      &times;
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Error */}
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

        {selectedFile ? (
          <>
            {/* Editor Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-800">
              <div className="flex items-center gap-3">
                <h2 className="text-sm font-semibold text-neutral-200">
                  {selectedFile}
                </h2>
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
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSave}
                  disabled={saving || !hasChanges}
                  className="px-4 py-1.5 rounded-lg bg-amber-500 text-neutral-950 font-medium text-sm hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
                <button
                  onClick={() => handleDelete(selectedFile)}
                  className="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 text-xs hover:bg-red-500/20 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>

            {/* Textarea */}
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
                {loading ? "Loading..." : "Select or create a note"}
              </p>
              <p className="text-neutral-600 text-sm mt-1">
                Choose a file from the sidebar
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
