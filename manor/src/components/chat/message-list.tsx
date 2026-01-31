"use client";

import { useEffect, useRef } from "react";
import type { Message } from "@/lib/types";

interface MessageListProps {
  messages: Message[];
  streamingContent?: string;
}

function formatTime(timestamp: string): string {
  try {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export function MessageList({ messages, streamingContent }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  if (messages.length === 0 && !streamingContent) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-neutral-500 text-lg">No messages yet</p>
          <p className="text-neutral-600 text-sm mt-1">
            Start a conversation below
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[75%] rounded-xl px-4 py-3 ${
              msg.role === "user"
                ? "bg-neutral-800 text-neutral-100"
                : "bg-neutral-900 border-l-2 border-amber-500/30 text-neutral-200"
            }`}
          >
            {msg.role === "assistant" && msg.model && (
              <span className="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 mb-2">
                {msg.model}
              </span>
            )}
            <div className="whitespace-pre-wrap text-sm leading-relaxed break-words">
              {msg.content}
            </div>
            <p
              className={`text-[10px] mt-2 ${
                msg.role === "user" ? "text-neutral-500" : "text-neutral-600"
              }`}
            >
              {formatTime(msg.timestamp)}
            </p>
          </div>
        </div>
      ))}

      {streamingContent && (
        <div className="flex justify-start">
          <div className="max-w-[75%] rounded-xl px-4 py-3 bg-neutral-900 border-l-2 border-amber-500/30 text-neutral-200">
            <div className="whitespace-pre-wrap text-sm leading-relaxed break-words">
              {streamingContent}
              <span className="inline-block w-1.5 h-4 bg-amber-500 ml-0.5 animate-pulse" />
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
