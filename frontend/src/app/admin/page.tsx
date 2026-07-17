"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { fetchHealth, fetchSession, type SessionData } from "@/lib/api";
import FAQUpload from "@/components/FAQUpload";
import StatsCard from "@/components/StatsCard";
import { RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import clsx from "clsx";

function SessionRow({ sessionId }: { sessionId: string }) {
  const [data, setData] = useState<SessionData | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSession(sessionId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return (
    <div className="px-4 py-3 animate-pulse bg-slate-800/50 rounded-lg h-12" />
  );
  if (!data) return null;

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-700/30 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-3">
          <div className={clsx(
            "w-2 h-2 rounded-full",
            data.status === "active" ? "bg-green-400 animate-pulse" : "bg-slate-500",
          )} />
          <span className="text-sm font-mono text-slate-300">{data.session_id?.slice(0, 12)}…</span>
          {data.customer_name && (
            <span className="text-sm text-slate-400">{data.customer_name}</span>
          )}
          {data.escalated && (
            <span className="px-2 py-0.5 bg-red-900/40 text-red-400 text-xs rounded-full border border-red-700/40">
              Eskalasi
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-slate-500">
          <span className="text-xs">{(data.complaints?.length ?? 0)} tiket</span>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-700/60 space-y-3 pt-3 animate-fade-in">
          {/* Phone */}
          {data.customer_phone && (
            <p className="text-xs text-slate-400">Telepon: <span className="text-slate-200">{data.customer_phone}</span></p>
          )}
          {/* Complaints */}
          {(data.complaints?.length ?? 0) > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 mb-2">Keluhan:</p>
              <div className="space-y-1.5">
                {data.complaints!.map((c) => (
                  <div key={c.ticket_id} className="flex items-start justify-between gap-2 bg-slate-900/60 rounded-lg px-3 py-2">
                    <div>
                      <span className="text-xs font-mono text-blue-400">{c.ticket_id}</span>
                      <p className="text-xs text-slate-300 mt-0.5">{c.description}</p>
                    </div>
                    <span className="text-xs px-2 py-0.5 bg-slate-700 rounded-full text-slate-400 whitespace-nowrap">
                      {c.category}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* History */}
          {(data.history?.length ?? 0) > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 mb-2">Riwayat Percakapan ({data.history!.length} pesan):</p>
              <div className="max-h-48 overflow-y-auto space-y-1.5">
                {data.history!.slice(-8).map((h, i) => (
                  <div key={i} className={clsx(
                    "flex gap-2 text-xs",
                    h.role === "user" ? "flex-row-reverse" : "flex-row",
                  )}>
                    <span className={clsx(
                      "px-2 py-1 rounded-lg max-w-[85%] leading-relaxed",
                      h.role === "user" ? "bg-blue-900/50 text-blue-200" : "bg-slate-700 text-slate-300",
                    )}>
                      {h.text}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AdminPage() {
  const [healthOk, setHealthOk] = useState<boolean | null>(null);
  const [sessionIds] = useState<string[]>([]);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const refresh = useCallback(async () => {
    setLoadingHealth(true);
    try {
      await fetchHealth();
      setHealthOk(true);
    } catch {
      setHealthOk(false);
    } finally {
      setLoadingHealth(false);
      setLastRefresh(new Date());
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // Demo session IDs - in production, fetch from /sessions endpoint
  const demoSessions = sessionIds.length > 0 ? sessionIds : [];

  return (
    <div className="min-h-screen">
      {/* Navbar */}
      <nav className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-slate-400 hover:text-slate-200 text-sm transition-colors">
              ← Kembali
            </Link>
            <div className="h-4 w-px bg-slate-700" />
            <span className="font-semibold text-white">Admin Dashboard</span>
          </div>
          <button
            onClick={refresh}
            disabled={loadingHealth}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm text-slate-300 transition-colors"
          >
            <RefreshCw className={clsx("w-3.5 h-3.5", loadingHealth && "animate-spin")} />
            Refresh
          </button>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-8">

        {/* System status */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Status Sistem</h2>
            <p className="text-xs text-slate-500">
              Update: {lastRefresh.toLocaleTimeString("id-ID")}
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatsCard
              label="API Backend"
              value={healthOk === null ? "…" : healthOk ? "Online" : "Offline"}
              icon={healthOk ? "✅" : "❌"}
              color={healthOk ? "green" : "red"}
            />
            <StatsCard label="LiveKit Agent" value="—" icon="🤖" color="blue" subtitle="Cek LiveKit console" />
            <StatsCard label="Sesi Aktif" value={demoSessions.length} icon="📞" color="yellow" />
            <StatsCard label="Eskalasi Hari Ini" value="—" icon="🚨" color="red" subtitle="Via Prometheus /metrics" />
          </div>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

          {/* Sessions */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Sesi Terkini</h2>
              <span className="text-xs text-slate-500">
                {demoSessions.length === 0 ? "Tidak ada sesi aktif" : `${demoSessions.length} sesi`}
              </span>
            </div>

            {demoSessions.length === 0 ? (
              <div className="bg-slate-800/40 border border-slate-700 rounded-xl p-8 text-center">
                <p className="text-slate-500 text-sm">Belum ada sesi tersimpan.</p>
                <p className="text-slate-600 text-xs mt-1">
                  Sesi akan muncul setelah ada panggilan masuk.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {demoSessions.map((id) => <SessionRow key={id} sessionId={id} />)}
              </div>
            )}

            {/* Metrics link */}
            <a
              href="/metrics"
              target="_blank"
              className="flex items-center justify-between px-4 py-3 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700 rounded-xl text-sm text-slate-300 transition-colors"
            >
              <span>📊 Prometheus Metrics</span>
              <span className="text-slate-500 text-xs">→</span>
            </a>
          </div>

          {/* FAQ Upload */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4">Basis Pengetahuan</h2>
            <div className="bg-slate-800/40 border border-slate-700 rounded-xl p-5">
              <FAQUpload />
            </div>
          </div>
        </div>

        {/* Quick actions */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Aksi Cepat</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <a href="/docs" target="_blank" className="flex items-center gap-3 px-4 py-3 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700 rounded-xl text-sm text-slate-300 transition-colors">
              <span>📖</span> API Docs
            </a>
            <a href="/metrics" target="_blank" className="flex items-center gap-3 px-4 py-3 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700 rounded-xl text-sm text-slate-300 transition-colors">
              <span>📈</span> Metrics
            </a>
            <a href="/health" target="_blank" className="flex items-center gap-3 px-4 py-3 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700 rounded-xl text-sm text-slate-300 transition-colors">
              <span>💚</span> Health Check
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}
