"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { AgentIdentity } from "@/lib/types";

const EDITABLE_FIELDS = new Set([
  "allowed_models",
  "subagent_model",
  "max_turns",
  "claude_timeout_s",
  "allowed_origins",
]);

export default function ConfigPage() {
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [agents, setAgents] = useState<AgentIdentity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const [configData, agentsData] = await Promise.all([
          api.config.get(),
          api.config.agents(),
        ]);
        setConfig(configData);
        setAgents(agentsData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load config");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function renderValue(value: unknown): string {
    if (value === null || value === undefined) return "null";
    if (Array.isArray(value)) return value.join(", ");
    if (typeof value === "object") return JSON.stringify(value, null, 2);
    return String(value);
  }

  function isNested(value: unknown): boolean {
    return typeof value === "object" && value !== null && !Array.isArray(value);
  }

  function startEdit(key: string, value: unknown) {
    setEditing(key);
    setEditValue(renderValue(value));
    setSaveMsg(null);
  }

  function cancelEdit() {
    setEditing(null);
    setEditValue("");
  }

  async function saveEdit(key: string) {
    setSaving(true);
    setSaveMsg(null);
    try {
      let parsed: unknown = editValue;
      // Parse arrays (comma-separated)
      if (Array.isArray(config[key])) {
        parsed = editValue.split(",").map((s) => s.trim()).filter(Boolean);
      }
      // Parse numbers
      if (typeof config[key] === "number") {
        parsed = Number(editValue);
        if (isNaN(parsed as number)) {
          setSaveMsg("Invalid number");
          setSaving(false);
          return;
        }
      }

      await api.config.update({ [key]: parsed });
      setConfig((prev) => ({ ...prev, [key]: parsed }));
      setEditing(null);
      setEditValue("");
      setSaveMsg("Saved");
      setTimeout(() => setSaveMsg(null), 2000);
    } catch (err) {
      setSaveMsg(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex items-center gap-3 text-neutral-400">
          <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
          Loading configuration...
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-6 max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-neutral-100">Configuration</h1>
          <p className="text-sm text-neutral-500 mt-1">
            System configuration and agent registry — click editable fields to modify
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="text-red-400 hover:text-red-300 text-xs"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Save notification */}
        {saveMsg && (
          <div className={`mb-4 px-4 py-2 rounded-lg text-sm ${
            saveMsg === "Saved"
              ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
              : "bg-red-500/10 border border-red-500/20 text-red-400"
          }`}>
            {saveMsg}
          </div>
        )}

        {/* Agent Registry */}
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-neutral-300 uppercase tracking-wider mb-4">
            Agent Registry
          </h2>
          {agents.length === 0 ? (
            <p className="text-neutral-500 text-sm">No agents registered</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {agents.map((agent) => (
                <div
                  key={agent.name}
                  className="rounded-xl border border-neutral-800 bg-neutral-900 p-5 hover:border-neutral-700 transition-colors"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-2xl">{agent.emoji}</span>
                    <div>
                      <h3 className="font-semibold text-neutral-100 text-sm">
                        {agent.display_name}
                      </h3>
                      <p className="text-xs text-neutral-500">{agent.name}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* System Configuration */}
        <div>
          <h2 className="text-sm font-semibold text-neutral-300 uppercase tracking-wider mb-4">
            System Configuration
          </h2>
          <div className="rounded-xl border border-neutral-800 bg-neutral-900 overflow-hidden">
            {Object.keys(config).length === 0 ? (
              <p className="p-4 text-neutral-500 text-sm">
                No configuration data
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-800 bg-neutral-900/50">
                    <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wider w-1/3">
                      Key
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wider">
                      Value
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/50">
                  {Object.entries(config).map(([key, value]) => {
                    const editable = EDITABLE_FIELDS.has(key);
                    const isEditingThis = editing === key;

                    return (
                      <tr key={key} className={`${editable ? "hover:bg-neutral-800/30" : ""}`}>
                        <td className="px-4 py-3 align-top">
                          <span className={`font-mono text-xs ${editable ? "text-amber-400" : "text-amber-400/50"}`}>
                            {key}
                          </span>
                          {editable && (
                            <span className="ml-2 text-[9px] text-neutral-600 font-normal">
                              editable
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-neutral-300 align-top">
                          {isEditingThis ? (
                            <div className="flex items-start gap-2">
                              {Array.isArray(value) || typeof value === "string" ? (
                                <input
                                  type="text"
                                  value={editValue}
                                  onChange={(e) => setEditValue(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === "Enter") saveEdit(key);
                                    if (e.key === "Escape") cancelEdit();
                                  }}
                                  autoFocus
                                  className="flex-1 bg-neutral-950 border border-amber-500/30 rounded px-2 py-1 text-xs font-mono text-neutral-200 focus:outline-none focus:border-amber-500/60"
                                />
                              ) : (
                                <input
                                  type="number"
                                  value={editValue}
                                  onChange={(e) => setEditValue(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === "Enter") saveEdit(key);
                                    if (e.key === "Escape") cancelEdit();
                                  }}
                                  autoFocus
                                  className="w-32 bg-neutral-950 border border-amber-500/30 rounded px-2 py-1 text-xs font-mono text-neutral-200 focus:outline-none focus:border-amber-500/60"
                                />
                              )}
                              <button
                                onClick={() => saveEdit(key)}
                                disabled={saving}
                                className="px-2 py-1 rounded bg-amber-500/15 text-amber-400 text-xs font-medium hover:bg-amber-500/25 disabled:opacity-40 transition-colors"
                              >
                                Save
                              </button>
                              <button
                                onClick={cancelEdit}
                                className="px-2 py-1 rounded text-neutral-500 text-xs hover:text-neutral-300 transition-colors"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <div
                              className={`group flex items-center gap-2 ${editable ? "cursor-pointer" : ""}`}
                              onClick={() => editable && startEdit(key, value)}
                            >
                              {isNested(value) ? (
                                <pre className="text-xs font-mono text-neutral-400 whitespace-pre-wrap overflow-x-auto">
                                  {renderValue(value)}
                                </pre>
                              ) : (
                                <span className="text-xs font-mono">
                                  {renderValue(value)}
                                </span>
                              )}
                              {editable && (
                                <svg
                                  className="w-3 h-3 text-neutral-600 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                </svg>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* System Info */}
        <div className="mt-8">
          <h2 className="text-sm font-semibold text-neutral-300 uppercase tracking-wider mb-4">
            System Info
          </h2>
          <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-5">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-neutral-500 text-xs mb-1">Dashboard</p>
                <p className="text-neutral-200 font-medium">Manor v0.1.0</p>
              </div>
              <div>
                <p className="text-neutral-500 text-xs mb-1">API</p>
                <p className="text-neutral-200 font-medium">
                  {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8700"}
                </p>
              </div>
              <div>
                <p className="text-neutral-500 text-xs mb-1">Agents</p>
                <p className="text-neutral-200 font-medium">{agents.length}</p>
              </div>
              <div>
                <p className="text-neutral-500 text-xs mb-1">Config Keys</p>
                <p className="text-neutral-200 font-medium">
                  {Object.keys(config).length}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
