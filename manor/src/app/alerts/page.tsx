"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface AlertRule {
  id: string;
  name: string;
  description: string;
  rule_type: string;
  config: Record<string, unknown>;
  enabled: boolean;
  cooldown_s: number;
  created_at: number;
}

interface AlertEvent {
  id: number;
  rule_id: string;
  fired_at: number;
  message: string;
  resolved: boolean;
  resolved_at: number | null;
}

export default function AlertsPage() {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [history, setHistory] = useState<AlertEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState<string | null>(null);

  async function load() {
    try {
      setLoading(true);
      const [r, h] = await Promise.all([
        api.alerts.rules(),
        api.alerts.history(100),
      ]);
      setRules(r);
      setHistory(h);
    } catch (err) {
      console.error("Failed to load alerts:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleToggle(ruleId: string) {
    try {
      await api.alerts.toggle(ruleId);
      await load();
    } catch (err) {
      console.error("Toggle failed:", err);
    }
  }

  async function handleCheck() {
    try {
      setChecking(true);
      const result = await api.alerts.check();
      if (result.alerts_fired > 0) {
        setCheckResult(`${result.alerts_fired} alert(s) fired`);
      } else {
        setCheckResult("All clear — no alerts triggered");
      }
      await load();
      setTimeout(() => setCheckResult(null), 4000);
    } catch (err) {
      setCheckResult("Check failed");
    } finally {
      setChecking(false);
    }
  }

  function formatDate(ts: number) {
    return new Date(ts * 1000).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function ruleTypeBadge(type: string) {
    const colors: Record<string, string> = {
      error_spike: "bg-red-500/15 text-red-400",
      service_down: "bg-amber-500/15 text-amber-400",
      disk_space: "bg-blue-500/15 text-blue-400",
      custom_query: "bg-purple-500/15 text-purple-400",
      process_check: "bg-cyan-500/15 text-cyan-400",
    };
    return colors[type] || "bg-neutral-700/50 text-neutral-400";
  }

  const enabledRules = rules.filter((r) => r.enabled).length;
  const recentAlerts = history.filter(
    (h) => h.fired_at > Date.now() / 1000 - 86400
  ).length;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-neutral-100">Alerts</h1>
            <p className="text-sm text-neutral-500 mt-1">
              Watchtower monitoring rules and alert history
            </p>
          </div>
          <div className="flex items-center gap-3">
            {checkResult && (
              <span className="text-xs px-3 py-1.5 rounded-lg bg-neutral-800 text-neutral-300">
                {checkResult}
              </span>
            )}
            <button
              onClick={handleCheck}
              disabled={checking}
              className="px-4 py-2 rounded-lg bg-amber-500 text-neutral-950 font-medium text-sm hover:bg-amber-400 disabled:opacity-40 transition-colors"
            >
              {checking ? "Checking..." : "Run Check Now"}
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-4">
            <p className="text-xs text-neutral-500 uppercase tracking-wider">
              Rules
            </p>
            <p className="text-2xl font-bold text-neutral-100 mt-1">
              {rules.length}
            </p>
            <p className="text-xs text-neutral-500 mt-0.5">
              {enabledRules} enabled
            </p>
          </div>
          <div className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-4">
            <p className="text-xs text-neutral-500 uppercase tracking-wider">
              Alerts (24h)
            </p>
            <p
              className={`text-2xl font-bold mt-1 ${
                recentAlerts > 0 ? "text-red-400" : "text-emerald-400"
              }`}
            >
              {recentAlerts}
            </p>
            <p className="text-xs text-neutral-500 mt-0.5">
              {recentAlerts === 0 ? "All quiet" : "Needs attention"}
            </p>
          </div>
          <div className="bg-neutral-900/50 border border-neutral-800 rounded-xl p-4">
            <p className="text-xs text-neutral-500 uppercase tracking-wider">
              Total History
            </p>
            <p className="text-2xl font-bold text-neutral-100 mt-1">
              {history.length}
            </p>
            <p className="text-xs text-neutral-500 mt-0.5">all time</p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
          </div>
        ) : (
          <>
            {/* Rules */}
            <div className="mb-10">
              <h2 className="text-lg font-semibold text-neutral-200 mb-4">
                Alert Rules
              </h2>
              <div className="space-y-2">
                {rules.map((rule) => (
                  <div
                    key={rule.id}
                    className={`flex items-center justify-between p-4 rounded-xl border transition-colors ${
                      rule.enabled
                        ? "bg-neutral-900/50 border-neutral-800"
                        : "bg-neutral-900/20 border-neutral-800/50 opacity-60"
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-neutral-200">
                          {rule.name}
                        </span>
                        <span
                          className={`text-[9px] px-1.5 py-0.5 rounded-full ${ruleTypeBadge(
                            rule.rule_type
                          )}`}
                        >
                          {rule.rule_type.replace("_", " ")}
                        </span>
                      </div>
                      {rule.description && (
                        <p className="text-xs text-neutral-500">
                          {rule.description}
                        </p>
                      )}
                      <p className="text-[10px] text-neutral-600 mt-1">
                        Cooldown: {Math.round(rule.cooldown_s / 60)}min
                      </p>
                    </div>
                    <button
                      onClick={() => handleToggle(rule.id)}
                      className={`shrink-0 w-10 h-5 rounded-full transition-colors relative ${
                        rule.enabled ? "bg-emerald-500" : "bg-neutral-700"
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                          rule.enabled ? "left-5" : "left-0.5"
                        }`}
                      />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* History */}
            <div>
              <h2 className="text-lg font-semibold text-neutral-200 mb-4">
                Alert History
              </h2>
              {history.length === 0 ? (
                <div className="text-center py-12 text-neutral-500">
                  <p className="text-lg">No alerts fired yet</p>
                  <p className="text-sm mt-1">
                    Alerts will appear here when rules are triggered
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {history.map((event) => {
                    const rule = rules.find((r) => r.id === event.rule_id);
                    return (
                      <div
                        key={event.id}
                        className="p-4 bg-neutral-900/50 border border-neutral-800 rounded-xl"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs text-neutral-500">
                                {formatDate(event.fired_at)}
                              </span>
                              {rule && (
                                <span
                                  className={`text-[9px] px-1.5 py-0.5 rounded-full ${ruleTypeBadge(
                                    rule.rule_type
                                  )}`}
                                >
                                  {rule.name}
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-neutral-300">
                              {event.message}
                            </p>
                          </div>
                          {event.resolved && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 shrink-0">
                              resolved
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
