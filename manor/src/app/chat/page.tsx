"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import {
  createChatConnection,
  sendMessage,
  disconnect,
} from "@/lib/websocket";
import { MessageList } from "@/components/chat/message-list";
import { InputBar } from "@/components/chat/input-bar";
import type { Session, Message } from "@/lib/types";

export default function ChatPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const streamRef = useRef("");
  const activeSessionRef = useRef<Session | null>(null);
  activeSessionRef.current = activeSession;

  // Load sessions
  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await api.sessions.list();
        setSessions(data);
        const active = data.find((s) => s.is_active) || data[0] || null;
        setActiveSession(active);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load sessions");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Connect WebSocket (once)
  useEffect(() => {
    const ws = createChatConnection({
      onDelta: (text) => {
        streamRef.current += text;
        setStreamingContent(streamRef.current);
      },
      onResult: (fullText) => {
        const session = activeSessionRef.current;
        const assistantMsg: Message = {
          id: `msg-${Date.now()}-assistant`,
          role: "assistant",
          content: fullText || streamRef.current,
          timestamp: new Date().toISOString(),
          session_name: session?.name || "",
          model: session?.model,
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setStreamingContent("");
        streamRef.current = "";
        setIsStreaming(false);
      },
      onError: (errMsg) => {
        setError(errMsg);
        setIsStreaming(false);
        setStreamingContent("");
        streamRef.current = "";
      },
      onClose: () => {
        setConnected(false);
      },
      onOpen: () => {
        setConnected(true);
      },
    });

    return () => {
      disconnect();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSend = useCallback(
    (content: string) => {
      if (!activeSession || isStreaming) return;

      const userMsg: Message = {
        id: `msg-${Date.now()}-user`,
        role: "user",
        content,
        timestamp: new Date().toISOString(),
        session_name: activeSession.name,
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      streamRef.current = "";
      setStreamingContent("");

      try {
        sendMessage(activeSession.name, activeSession.chat_id, content);
      } catch {
        setError("Failed to send message. WebSocket not connected.");
        setIsStreaming(false);
      }
    },
    [activeSession, isStreaming]
  );

  const handleSessionChange = async (sessionName: string) => {
    const session = sessions.find((s) => s.name === sessionName);
    if (!session) return;
    try {
      await api.sessions.activate(session.chat_id, session.name);
      setActiveSession(session);
      setMessages([]);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to switch session");
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex items-center gap-3 text-neutral-400">
          <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
          Loading sessions...
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-neutral-800 px-4 py-3 flex items-center justify-between bg-neutral-950">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-neutral-100">Chat</h1>
          {sessions.length > 0 && (
            <select
              value={activeSession?.name || ""}
              onChange={(e) => handleSessionChange(e.target.value)}
              className="text-sm bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-1.5 text-neutral-300 focus:outline-none focus:border-amber-500/50"
            >
              {sessions.map((s) => (
                <option key={`${s.chat_id}-${s.name}`} value={s.name}>
                  {s.name}
                </option>
              ))}
            </select>
          )}
          {activeSession && (
            <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400">
              {activeSession.model}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-500" : "bg-red-500"}`}
          />
          <span className="text-xs text-neutral-500">
            {connected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      {/* Error banner */}
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

      {/* Messages */}
      <MessageList messages={messages} streamingContent={streamingContent} />

      {/* Typing indicator */}
      {isStreaming && !streamingContent && (
        <div className="px-4 py-2">
          <div className="flex items-center gap-2 text-neutral-500 text-sm">
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
            Thinking...
          </div>
        </div>
      )}

      {/* Input */}
      <InputBar onSend={handleSend} disabled={isStreaming || !activeSession} />
    </div>
  );
}
