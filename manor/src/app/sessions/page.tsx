"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { SessionCard } from "@/components/sessions/session-card";
import type { Session } from "@/lib/types";

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newChatId, setNewChatId] = useState("1");
  const [newModel, setNewModel] = useState("sonnet");
  const [creating, setCreating] = useState(false);

  async function loadSessions() {
    try {
      setLoading(true);
      const data = await api.sessions.list();
      setSessions(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSessions();
  }, []);

  async function handleCreate() {
    if (!newName.trim()) return;
    try {
      setCreating(true);
      await api.sessions.create({
        chat_id: parseInt(newChatId, 10),
        name: newName.trim(),
        model: newModel,
      });
      setNewName("");
      setShowCreate(false);
      await loadSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
    } finally {
      setCreating(false);
    }
  }

  async function handleActivate(session: Session) {
    try {
      await api.sessions.activate(session.chat_id, session.name);
      await loadSessions();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to activate session"
      );
    }
  }

  async function handleChangeModel(session: Session, model: string) {
    try {
      await api.sessions.setModel(session.chat_id, session.name, model);
      await loadSessions();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to change model"
      );
    }
  }

  async function handleDelete(session: Session) {
    if (!confirm(`Delete session "${session.name}"?`)) return;
    try {
      await api.sessions.delete(session.chat_id, session.name);
      await loadSessions();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to delete session"
      );
    }
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-6 max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-neutral-100">Sessions</h1>
            <p className="text-sm text-neutral-500 mt-1">
              Manage chat sessions across your agents
            </p>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="px-4 py-2 rounded-lg bg-amber-500 text-neutral-950 font-medium text-sm hover:bg-amber-400 transition-colors"
          >
            New Session
          </button>
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

        {/* Create Form */}
        {showCreate && (
          <div className="mb-6 p-4 rounded-xl border border-neutral-800 bg-neutral-900">
            <h2 className="text-sm font-semibold text-neutral-200 mb-3">
              Create New Session
            </h2>
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <label className="block text-xs text-neutral-500 mb-1">
                  Session Name
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="my-session"
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:border-amber-500/50"
                />
              </div>
              <div className="w-24">
                <label className="block text-xs text-neutral-500 mb-1">
                  Chat ID
                </label>
                <input
                  type="number"
                  value={newChatId}
                  onChange={(e) => setNewChatId(e.target.value)}
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 focus:outline-none focus:border-amber-500/50"
                />
              </div>
              <div className="w-32">
                <label className="block text-xs text-neutral-500 mb-1">
                  Model
                </label>
                <select
                  value={newModel}
                  onChange={(e) => setNewModel(e.target.value)}
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-300 focus:outline-none focus:border-amber-500/50"
                >
                  <option value="opus">opus</option>
                  <option value="sonnet">sonnet</option>
                  <option value="haiku">haiku</option>
                </select>
              </div>
              <button
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
                className="px-4 py-2 rounded-lg bg-amber-500 text-neutral-950 font-medium text-sm hover:bg-amber-400 disabled:opacity-40 transition-colors"
              >
                {creating ? "Creating..." : "Create"}
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 rounded-lg bg-neutral-800 text-neutral-400 text-sm hover:text-neutral-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3 text-neutral-400">
              <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
              Loading sessions...
            </div>
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-neutral-500 text-lg">No sessions found</p>
            <p className="text-neutral-600 text-sm mt-1">
              Create a new session to get started
            </p>
          </div>
        ) : (
          /* Session Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sessions.map((session) => (
              <SessionCard
                key={`${session.chat_id}-${session.name}`}
                session={session}
                onActivate={() => handleActivate(session)}
                onDelete={() => handleDelete(session)}
                onChangeModel={(model) => handleChangeModel(session, model)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
