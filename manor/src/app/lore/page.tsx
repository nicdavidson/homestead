"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface LoreFile {
  name: string;
  size: number;
  modified: number;
  layer: string;
  has_base: boolean;
}

export default function LorePage() {
  const [files, setFiles] = useState<LoreFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [selectedLayer, setSelectedLayer] = useState<string>("");
  const [content, setContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  async function loadFiles() {
    try {
      setLoading(true);
      const data = await api.lore.list();
      setFiles(data);
      if (data.length > 0 && !selectedFile && data[0]?.name) {
        loadFileContent(data[0].name);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load lore files");
    } finally {
      setLoading(false);
    }
  }

  async function loadFileContent(name: string) {
    try {
      const data = await api.lore.get(name);
      setContent(data.content);
      setOriginalContent(data.content);
      setSelectedFile(name);
      setSelectedLayer(data.layer);
      setSuccessMsg(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load file");
    }
  }

  useEffect(() => {
    loadFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSave() {
    if (!selectedFile) return;
    try {
      setSaving(true);
      await api.lore.save(selectedFile, content);
      setOriginalContent(content);
      setSelectedLayer("user");
      setSuccessMsg("Saved successfully");
      setTimeout(() => setSuccessMsg(null), 2000);
      await loadFiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  const hasChanges = content !== originalContent;

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* File List Sidebar */}
      <div className="w-64 shrink-0 border-r border-neutral-800 bg-neutral-900/30 flex flex-col">
        <div className="px-4 py-4 border-b border-neutral-800">
          <h1 className="text-lg font-semibold text-neutral-100">Lore</h1>
          <p className="text-xs text-neutral-500 mt-0.5">
            Identity and context files
          </p>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {loading ? (
            <div className="flex items-center justify-center py-10">
              <div className="w-4 h-4 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
            </div>
          ) : files.length === 0 ? (
            <p className="px-4 py-4 text-sm text-neutral-500">No lore files</p>
          ) : (
            <ul className="space-y-0.5 px-2">
              {files.map((file) => (
                <li key={file.name}>
                  <button
                    onClick={() => loadFileContent(file.name)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center justify-between gap-2 ${
                      selectedFile === file.name
                        ? "bg-amber-500/10 text-amber-500 font-medium"
                        : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800"
                    }`}
                  >
                    <span className="truncate">{file.name}</span>
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded-full shrink-0 ${
                        file.layer === "user"
                          ? "bg-emerald-500/15 text-emerald-400"
                          : "bg-neutral-700/50 text-neutral-500"
                      }`}
                    >
                      {file.layer}
                    </span>
                  </button>
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
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 text-xs">
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
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full ${
                    selectedLayer === "user"
                      ? "bg-emerald-500/15 text-emerald-400"
                      : "bg-neutral-700/50 text-neutral-500"
                  }`}
                >
                  {selectedLayer === "base" ? "base default" : "user override"}
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
                {saving ? "Saving..." : selectedLayer === "base" ? "Save as Override" : "Save"}
              </button>
            </div>

            {/* Base file hint */}
            {selectedLayer === "base" && (
              <div className="px-4 py-2 bg-neutral-800/50 border-b border-neutral-800 text-xs text-neutral-500">
                Viewing base default. Saving will create a user override — the base template stays unchanged.
              </div>
            )}

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
                {loading ? "Loading..." : "Select a lore file"}
              </p>
              <p className="text-neutral-600 text-sm mt-1">
                Choose a file from the sidebar to edit
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
