"use client"

import React, { useMemo } from "react"
import { Mic, MicOff, Square } from "lucide-react"
import { AudioVisualizer } from "../voice-assistant/audio-visualizer"

interface VoiceModeProps {
  voiceConnection: any
}

export function VoiceMode({ voiceConnection }: VoiceModeProps) {
  const {
    agentState: state,
    sttError,
    isMuted,
    toggleMute,
    stopSpeaking,
    conversationActive,
  } = voiceConnection

  const statusText = useMemo(() => {
    switch (state) {
      case "listening":
        return conversationActive ? "Mendengarkan... (percakapan aktif)" : "Mendengarkan..."
      case "speaking":
        return "Viona sedang berbicara..."
      case "thinking":
        return "Viona sedang memikirkan..."
      default:
        return conversationActive
          ? "Silakan lanjut bicara..."
          : 'Ucapkan "Hai Viona" untuk mulai bicara'
    }
  }, [state, conversationActive])

  return (
    <div className="flex flex-col items-center justify-center flex-1 h-full py-6 px-4">
      <div className="relative w-32 h-32 flex items-center justify-center">
        <AudioVisualizer vionaStatus={state} isConnected={true} className="w-full h-full scale-125" />
      </div>

      <p className="mt-5 text-sm font-medium text-slate-700 dark:text-slate-300 text-center transition-all">
        {statusText}
      </p>

      {/* Sepenuhnya hands-free: tidak ada tombol bicara. Gerbangnya wake-word
          ("Hai Viona"), lalu percakapan tetap terbuka beberapa detik untuk lanjutan. */}
      <p className="mt-2 text-[11px] text-slate-400">
        Selalu mendengarkan panggilan{" "}
        <span className="font-medium text-violet-500">&quot;Hai Viona&quot;</span>
      </p>

      {/* Kontrol sekunder: mute + stop (kontekstual) */}
      <div className="mt-4 flex items-center justify-center gap-3">
        <button
          onClick={toggleMute}
          className={`p-3 rounded-full transition-all shadow-sm ${
            isMuted
              ? "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400 hover:bg-red-200"
              : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200 hover:bg-slate-200"
          }`}
          title={isMuted ? "Nyalakan Mikrofon" : "Matikan Mikrofon"}
        >
          {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>

        {state === "speaking" && (
          <button
            onClick={stopSpeaking}
            className="p-3 rounded-full transition-all shadow-sm bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400 hover:bg-red-200"
            title="Hentikan Viona"
          >
            <Square className="w-5 h-5 fill-current" />
          </button>
        )}
      </div>

      {sttError && (
        <p className="text-xs text-red-500 mt-3 px-4 bg-red-50 dark:bg-red-900/20 py-2 rounded-md text-center">
          {sttError}
        </p>
      )}
    </div>
  )
}
