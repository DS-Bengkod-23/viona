"use client";

import {
  BarVisualizer,
  DisconnectButton,
  LiveKitRoom,
  RoomAudioRenderer,
  useVoiceAssistant,
  VoiceAssistantControlBar,
} from "@livekit/components-react";
import { MicOff, PhoneOff } from "lucide-react";
import { useCallback, useState } from "react";
import { fetchToken, type TokenResponse } from "@/lib/api";
import Transcript from "./Transcript";

type ConnectionState = "idle" | "connecting" | "connected" | "disconnected";

function AgentVisualizer() {
  const { state, audioTrack } = useVoiceAssistant();

  const stateLabel: Record<string, string> = {
    disconnected:  "Terputus",
    connecting:    "Menghubungkan...",
    initializing:  "Memulai sesi...",
    listening:     "🎤 Mendengarkan",
    thinking:      "🤔 Memproses...",
    speaking:      "🔊 Berbicara",
  };

  const stateBadgeColor: Record<string, string> = {
    listening: "bg-green-500/20 text-green-400 border-green-500/30",
    thinking:  "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    speaking:  "bg-blue-500/20 text-blue-400 border-blue-500/30",
  };

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Circular visualizer */}
      <div className="relative w-40 h-40 flex items-center justify-center">
        <div className={`absolute inset-0 rounded-full border-2 transition-all duration-500 ${
          state === "speaking" ? "border-blue-500 animate-pulse-slow" : "border-slate-700"
        }`} />
        <div className="w-28 h-28 rounded-full bg-slate-800 flex items-center justify-center overflow-hidden">
          {audioTrack ? (
            <BarVisualizer
              trackRef={audioTrack}
              barCount={12}
              options={{ minHeight: 4 }}
              className="w-full h-full"
            />
          ) : (
            <span className="text-4xl">🤖</span>
          )}
        </div>
      </div>

      {/* Agent name */}
      <div className="text-center">
        <p className="text-xl font-semibold text-white">Viona AI</p>
        <p className="text-sm text-slate-400">Asisten Layanan Pelanggan</p>
      </div>

      {/* State badge */}
      <span className={`px-3 py-1 rounded-full text-xs font-medium border ${
        stateBadgeColor[state] ?? "bg-slate-700 text-slate-300 border-slate-600"
      }`}>
        {stateLabel[state] ?? state}
      </span>
    </div>
  );
}

function ConnectedRoom({ onDisconnect }: { onDisconnect: () => void }) {
  return (
    <div className="flex flex-col h-full gap-4">
      <RoomAudioRenderer />

      {/* Top: visualizer */}
      <div className="bg-slate-800/60 rounded-2xl p-8 border border-slate-700 flex items-center justify-center">
        <AgentVisualizer />
      </div>

      {/* Middle: transcript */}
      <div className="flex-1 min-h-0">
        <Transcript />
      </div>

      {/* Bottom: controls */}
      <div className="bg-slate-800/60 rounded-2xl p-4 border border-slate-700">
        <VoiceAssistantControlBar />
        <div className="flex justify-center mt-3">
          <DisconnectButton onClick={onDisconnect}>
            <span className="flex items-center gap-2 px-6 py-2 bg-red-600 hover:bg-red-700 rounded-full text-sm font-medium transition-colors">
              <PhoneOff className="w-4 h-4" />
              Akhiri Panggilan
            </span>
          </DisconnectButton>
        </div>
      </div>
    </div>
  );
}

export default function VoiceAgent() {
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const [tokenData, setTokenData] = useState<TokenResponse | null>(null);
  const [error, setError] = useState<string>("");

  const handleConnect = useCallback(async () => {
    setConnectionState("connecting");
    setError("");
    try {
      const data = await fetchToken();
      setTokenData(data);
      setConnectionState("connected");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal terhubung");
      setConnectionState("idle");
    }
  }, []);

  const handleDisconnect = useCallback(() => {
    setConnectionState("disconnected");
    setTokenData(null);
    setTimeout(() => setConnectionState("idle"), 1500);
  }, []);

  if (connectionState === "idle" || connectionState === "disconnected") {
    return (
      <div className="flex flex-col items-center justify-center gap-8 py-16">
        {/* Avatar */}
        <div className="w-32 h-32 rounded-full bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center shadow-xl shadow-blue-900/40">
          <span className="text-5xl">🤖</span>
        </div>

        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-white">Viona AI</h2>
          <p className="text-slate-400">Asisten layanan pelanggan 24/7 berbahasa Indonesia</p>
        </div>

        {connectionState === "disconnected" && (
          <div className="bg-slate-800 border border-slate-700 rounded-xl px-6 py-3 text-slate-300 text-sm animate-fade-in">
            Panggilan berakhir. Terima kasih!
          </div>
        )}

        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-xl px-6 py-3 text-red-300 text-sm max-w-sm text-center">
            {error}
          </div>
        )}

        <button
          onClick={handleConnect}
          className="flex items-center gap-3 px-8 py-4 bg-blue-600 hover:bg-blue-700 active:scale-95 rounded-full text-white font-semibold text-lg transition-all shadow-lg shadow-blue-900/40"
        >
          <span className="text-2xl">📞</span>
          Mulai Panggilan
        </button>

        <p className="text-slate-500 text-sm text-center max-w-xs">
          Bicara langsung dengan AI kami. Tanyakan apa saja,
          kami siap membantu.
        </p>
      </div>
    );
  }

  if (connectionState === "connecting") {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-16">
        <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-300">Menghubungkan ke Viona...</p>
      </div>
    );
  }

  return (
    <LiveKitRoom
      serverUrl={tokenData!.livekit_url}
      token={tokenData!.token}
      connect
      audio
      video={false}
      onDisconnected={handleDisconnect}
      className="h-full"
    >
      <ConnectedRoom onDisconnect={handleDisconnect} />
    </LiveKitRoom>
  );
}
