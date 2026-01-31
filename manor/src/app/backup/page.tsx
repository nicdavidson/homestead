"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface BackupEntry {
  filename: string;
  path: string;
  size_bytes: number;
  created_at: number;
  manifest: {
    version: string;
    exported_at: string;
    contents: Record<string, number | boolean>;
  } | null;
}

interface ExportResult {
  archive_path: string;
  size_bytes: number;
  checksum: string;
  manifest: {
    version: string;
    exported_at: string;
    contents: Record<string, number | boolean>;
  };
}

function getApiUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  const host = typeof window !== "undefined" ? window.location.hostname : "localhost";
  return `http://${host}:8700`;
}

export default function BackupPage() {
  const [backups, setBackups] = useState<BackupEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [lastResult, setLastResult] = useState<ExportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const API_URL = getApiUrl();

  async function loadBackups() {
    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/api/backup/list`);
      if (!res.ok) throw new Error(`API ${res.status}`);
      setBackups(await res.json());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load backups");
    } finally {
      setLoading(false);
    }
  }

  async function handleExport(includeLogs: boolean = false) {
    try {
      setExporting(true);
      setError(null);
      const res = await fetch(`${API_URL}/api/backup/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ include_logs: includeLogs }),
      });
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);
      const result: ExportResult = await res.json();
      setLastResult(result);
      await loadBackups();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  useEffect(() => {
    loadBackups();
  }, []);

  function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function formatDate(ts: number): string {
    return new Date(ts * 1000).toLocaleString();
  }

  return (
    <>
      <Header title="Backup" description="Export and restore Homestead data" />
      <main className="flex-1 overflow-y-auto p-6">
        {/* Export section */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-neutral-200">
                Create Backup
              </h3>
              <Badge variant="outline">~600 KB</Badge>
            </div>
          </CardHeader>
          <CardBody>
            <p className="text-sm text-neutral-400 mb-4">
              Exports journal, scratchpad, skills, databases (usage, tasks, jobs), and config
              as a portable .hpa archive.
            </p>
            <div className="flex gap-3">
              <Button
                variant="primary"
                onClick={() => handleExport(false)}
                disabled={exporting}
              >
                {exporting ? "Exporting..." : "Export Now"}
              </Button>
              <Button
                variant="secondary"
                onClick={() => handleExport(true)}
                disabled={exporting}
              >
                Export with Logs
              </Button>
            </div>

            {lastResult && (
              <div className="mt-4 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <p className="text-sm text-emerald-400 font-medium">Backup created</p>
                <p className="text-xs text-neutral-400 mt-1">
                  {lastResult.archive_path} ({formatBytes(lastResult.size_bytes)})
                </p>
                <p className="text-xs text-neutral-500 mt-0.5">
                  {lastResult.checksum}
                </p>
              </div>
            )}
          </CardBody>
        </Card>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Backup list */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-neutral-200">
                Available Backups
              </h3>
              <button
                onClick={loadBackups}
                className="text-xs text-neutral-500 hover:text-neutral-300"
              >
                Refresh
              </button>
            </div>
          </CardHeader>
          <CardBody>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
                <span className="ml-2 text-sm text-neutral-500">Loading...</span>
              </div>
            ) : backups.length === 0 ? (
              <p className="text-sm text-neutral-500 py-4 text-center">
                No backups yet. Click "Export Now" to create one.
              </p>
            ) : (
              <div className="space-y-2">
                {backups.map((b) => (
                  <div
                    key={b.filename}
                    className="flex items-center justify-between p-3 rounded-lg bg-neutral-800/50 border border-neutral-800"
                  >
                    <div>
                      <p className="text-sm font-medium text-neutral-200">
                        {b.filename}
                      </p>
                      <p className="text-xs text-neutral-500">
                        {formatDate(b.created_at)} &middot; {formatBytes(b.size_bytes)}
                      </p>
                      {b.manifest && (
                        <div className="flex gap-2 mt-1">
                          {Object.entries(b.manifest.contents).map(([k, v]) => (
                            typeof v === "number" && v > 0 ? (
                              <Badge key={k} variant="outline">
                                {k}: {v}
                              </Badge>
                            ) : null
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="text-xs text-neutral-600">
                      {b.path}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </main>
    </>
  );
}
