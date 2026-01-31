"use client";

import { Badge } from "@/components/ui/badge";

interface HeaderProps {
  title: string;
  description?: string;
}

export function Header({ title, description }: HeaderProps) {
  return (
    <header className="h-14 shrink-0 border-b border-neutral-800 bg-neutral-950/80 backdrop-blur-sm px-6 flex items-center justify-between">
      <div>
        <h1 className="text-sm font-semibold text-neutral-100">{title}</h1>
        {description && (
          <p className="text-xs text-neutral-500">{description}</p>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* Current session */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-neutral-400">Session:</span>
          <span className="text-xs text-neutral-200 font-medium">
            default
          </span>
          <Badge variant="default">opus-4</Badge>
        </div>

        {/* Agent status indicators */}
        <div className="flex items-center gap-1.5 pl-3 border-l border-neutral-800">
          <StatusDot color="emerald" label="Herald" />
          <StatusDot color="amber" label="Scribe" />
          <StatusDot color="neutral" label="Watcher" />
        </div>
      </div>
    </header>
  );
}

function StatusDot({
  color,
  label,
}: {
  color: "emerald" | "amber" | "red" | "neutral";
  label: string;
}) {
  const colorClasses = {
    emerald: "bg-emerald-500",
    amber: "bg-amber-500",
    red: "bg-red-500",
    neutral: "bg-neutral-600",
  };

  return (
    <div className="group relative flex items-center">
      <span
        className={`inline-block h-1.5 w-1.5 rounded-full ${colorClasses[color]}`}
      />
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover:block whitespace-nowrap rounded bg-neutral-800 px-2 py-0.5 text-[10px] text-neutral-300 shadow-lg">
        {label}
      </span>
    </div>
  );
}
