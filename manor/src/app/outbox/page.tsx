"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { AgentIdentity, OutboxMessage } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-500/15 text-amber-400",
  sent: "bg-emerald-500/15 text-emerald-400",
  failed: "bg-red-500/15 text-red-400",
};

const STATUSES = ["all", "pending", "sent", "failed"] as const;

function formatTimestamp(epoch: number | null): string {
  if (!epoch) return "--";
  return new Date(epoch * 1000).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function truncate(str: string, len: number): string {
  if (str.length <= len) return str;
  return str.slice(0, len) + "...";
}

export default function OutboxPage() {
  const [messages, setMessages] = useState<OutboxMessage[]>([]);
  const [agents, setAgents] = useState<AgentIdentity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [agentFilter, setAgentFilter] = useState<string>("all");

  // Auto-refresh
  const [autoRefresh, setAutoRefresh] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Send test message form
  const [showSendForm, setShowSendForm] = useState(false);
  const [sendForm, setSendForm] = useState({
    agent_name: "",
    chat_id: "",
    message: "",
  });
  const [sending, setSending] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params: { status?: string; agent?: string } = {};
      if (statusFilter !== "all") params.status = statusFilter;
      if (agentFilter !== "all") params.agent = agentFilter;
      const [msgData, agentData] = await Promise.all([
        api.outbox.list(params),
        api.config.agents(),
      ]);
      setMessages(msgData);
      setAgents(agentData);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load outbox");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, agentFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh interval
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchData, 5000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, fetchData]);

  function getAgentDisplay(name: string): string {
    const agent = agents.find((a) => a.name === name);
    return agent ? `${agent.emoji} ${agent.display_name}` : name;
  }

  async function handleSend() {
    if (!sendForm.agent_name || !sendForm.chat_id || !sendForm.message.trim()) return;
    setSending(true);
    try {
      await api.outbox.create({
        agent_name: sendForm.agent_name,
        chat_id: parseInt(sendForm.chat_id, 10),
        message: sendForm.message,
      });
      setSendForm({ agent_name: "", chat_id: "", message: "" });
      setShowSendForm(false);
      fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to send message");
    } finally {
      setSending(false);
    }
  }

  const uniqueAgents = Array.from(new Set(messages.map((m) => m.agent_name)));

  const counts = {
    total: messages.length,
    pending: messages.filter((m) => m.status === "pending").length,
    sent: messages.filter((m) => m.status === "sent").length,
    failed: messages.filter((m) => m.status === "failed").length,
  };

  return (
    <div className="min-h-screen p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-100">Outbox</h1>
          <p className="text-sm text-neutral-500 mt-0.5">
            Message queue &mdash; sent, pending, and failed deliveries
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Auto-refresh toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-3 py-2 text-sm rounded-lg border transition-colors ${
              autoRefresh
                ? "border-amber-500/40 bg-amber-500/10 text-amber-400"
                : "border-neutral-800 bg-neutral-900/60 text-neutral-400 hover:text-neutral-200"
            }`}
          >
            <svg
              className={`w-4 h-4 ${autoRefresh ? "animate-spin" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182"
              />
            </svg>
            {autoRefresh ? "Live" : "Auto-refresh"}
          </button>
          <button
            onClick={() => setShowSendForm(!showSendForm)}
            className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-neutral-950 font-medium text-sm rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5"
              />
            </svg>
            Send Test Message
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-3">
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <span className="text-xs font-medium text-neutral-400 uppercase tracking-wide">Total</span>
          <p className="text-2xl font-bold text-neutral-200 tabular-nums mt-1">{counts.total}</p>
        </div>
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <span className="text-xs font-medium text-amber-400/70 uppercase tracking-wide flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            Pending
          </span>
          <p className="text-2xl font-bold text-amber-400 tabular-nums mt-1">{counts.pending}</p>
        </div>
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <span className="text-xs font-medium text-emerald-400/70 uppercase tracking-wide flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Sent
          </span>
          <p className="text-2xl font-bold text-emerald-400 tabular-nums mt-1">{counts.sent}</p>
        </div>
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <span className="text-xs font-medium text-red-400/70 uppercase tracking-wide flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            Failed
          </span>
          <p className="text-2xl font-bold text-red-400 tabular-nums mt-1">{counts.failed}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div>
          <label className="block text-xs font-medium text-neutral-500 mb-1">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s === "all" ? "All Statuses" : s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-500 mb-1">Agent</label>
          <select
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
            className="bg-neutral-900 border border-neutral-800 text-neutral-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50"
          >
            <option value="all">All Agents</option>
            {uniqueAgents.map((a) => (
              <option key={a} value={a}>
                {getAgentDisplay(a)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1" />
        <button
          onClick={fetchData}
          className="mt-4 p-2 text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800 rounded-lg transition-colors"
          title="Refresh"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182"
            />
          </svg>
        </button>
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

      {/* Send Test Message Panel */}
      {showSendForm && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-neutral-200">Send Test Message</h2>
            <button
              onClick={() => setShowSendForm(false)}
              className="text-neutral-500 hover:text-neutral-300 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Agent</label>
              <select
                value={sendForm.agent_name}
                onChange={(e) => setSendForm({ ...sendForm, agent_name: e.target.value })}
                className="w-full bg-neutral-800 border border-neutral-700 text-neutral-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50"
              >
                <option value="">Select agent...</option>
                {agents.map((a) => (
                  <option key={a.name} value={a.name}>
                    {a.emoji} {a.display_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Chat ID</label>
              <input
                type="number"
                value={sendForm.chat_id}
                onChange={(e) => setSendForm({ ...sendForm, chat_id: e.target.value })}
                placeholder="123456789"
                className="w-full bg-neutral-800 border border-neutral-700 text-neutral-200 text-sm rounded-lg px-3 py-2 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50 font-mono"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleSend}
                disabled={sending || !sendForm.agent_name || !sendForm.chat_id || !sendForm.message.trim()}
                className="w-full px-4 py-2 bg-amber-500 hover:bg-amber-400 disabled:bg-neutral-800 disabled:text-neutral-600 text-neutral-950 font-medium text-sm rounded-lg transition-colors"
              >
                {sending ? "Sending..." : "Send"}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-400 uppercase tracking-wide mb-1.5">Message</label>
            <textarea
              value={sendForm.message}
              onChange={(e) => setSendForm({ ...sendForm, message: e.target.value })}
              placeholder="Enter message text (HTML supported)..."
              rows={3}
              className="w-full bg-neutral-800 border border-neutral-700 text-neutral-200 text-sm rounded-lg px-3 py-2 placeholder:text-neutral-600 focus:outline-none focus:ring-1 focus:ring-amber-500/50 focus:border-amber-500/50 resize-none font-mono"
            />
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="flex items-center gap-3 text-neutral-400">
            <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
            Loading outbox...
          </div>
        </div>
      ) : messages.length === 0 ? (
        <div className="text-center py-20">
          <svg className="w-12 h-12 mx-auto text-neutral-700 mb-3" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21.75 9v.906a2.25 2.25 0 0 1-1.183 1.981l-6.478 3.488M2.25 9v.906a2.25 2.25 0 0 0 1.183 1.981l6.478 3.488m8.839 2.51-4.66-2.51m0 0-1.023-.55a2.25 2.25 0 0 0-2.134 0l-1.022.55m0 0-4.661 2.51m16.5 1.615a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V8.844a2.25 2.25 0 0 1 1.183-1.981l7.5-4.039a2.25 2.25 0 0 1 2.134 0l7.5 4.039a2.25 2.25 0 0 1 1.183 1.98V21Z"
            />
          </svg>
          <p className="text-neutral-500 text-sm">No messages in the outbox</p>
          <p className="text-neutral-600 text-xs mt-1">Send a test message to get started</p>
        </div>
      ) : (
        <div className="rounded-lg border border-neutral-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-900/80 border-b border-neutral-800">
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide w-24">Status</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide w-40">Agent</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide">Message</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide w-44">Created</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wide w-44">Sent</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/60">
              {messages.map((msg) => (
                <tr key={msg.id} className="hover:bg-neutral-900/40 transition-colors">
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[msg.status] || "bg-neutral-700 text-neutral-400"}`}>
                      {msg.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-neutral-200 text-sm">{getAgentDisplay(msg.agent_name)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-neutral-300 font-mono text-xs" title={msg.message}>
                      {truncate(msg.message, 80)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-neutral-500 tabular-nums">
                    {formatTimestamp(msg.created_at)}
                  </td>
                  <td className="px-4 py-3 text-xs text-neutral-500 tabular-nums">
                    {formatTimestamp(msg.sent_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
