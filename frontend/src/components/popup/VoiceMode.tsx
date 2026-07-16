"use client"

import React, { useMemo, useState, useEffect, useCallback } from "react"
import { Mic, MicOff, Square, Radio } from "lucide-react"
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
    startPTT,
    endPTT,
    wakeWordEnabled,
    toggleWakeWord,
  } = voiceConnection

  const [isPTTHeld, setIsPTTHeld] = useState(false)

  const statusText = useMemo(() => {
    if (isPTTHeld) return "Merekam... lepas untuk kirim"
    switch (state) {
      case "listening": return "Viona sedang mendengarkan..."
      case "speaking": return "Viona sedang berbicara..."
      case "thinking": return "Viona sedang memikirkan..."
      default:
        return wakeWordEnabled ? 'Ucapkan "Hai Viona" untuk mulai' : "Menunggu..."
    }
  }, [state, isPTTHeld, wakeWordEnabled])

  const handlePTTDown = useCallback(() => {
    setIsPTTHeld(true)
    startPTT?.()
  }, [startPTT])

  const handlePTTUp = useCallback(() => {
    // Guard: only end if we were actually holding (avoids stray pointerup/leave).
    setIsPTTHeld((held) => {
      if (held) endPTT?.()
      return false
    })
  }, [endPTT])

  // Hold spacebar as push-to-talk. Ignore auto-repeat and typing targets.
  useEffect(() => {
    const isTypingTarget = (t: EventTarget | null) => {
      const el = t as HTMLElement | null
      return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable)
    }
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code !== "Space" || e.repeat || isTypingTarget(e.target)) return
      e.preventDefault()
      handlePTTDown()
    }
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code !== "Space" || isTypingTarget(e.target)) return
      e.preventDefault()
      handlePTTUp()
    }
    window.addEventListener("keydown", onKeyDown)
    window.addEventListener("keyup", onKeyUp)
    return () => {
      window.removeEventListener("keydown", onKeyDown)
      window.removeEventListener("keyup", onKeyUp)
    }
  }, [handlePTTDown, handlePTTUp])

  return (
    <div className="flex flex-col items-center h-full py-5 px-4">
      {/* Wake word MODE toggle */}
      <button
        onClick={toggleWakeWord}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
          wakeWordEnabled
            ? "bg-green-100 text-green-700 border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800"
            : "bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700"
        }`}
        title="Mode Wake Word — Viona hanya menjawab setelah dipanggil 'Hai Viona'"
      >
        <Radio className="w-3.5 h-3.5" />
        Mode Wake Word · {wakeWordEnabled ? "AKTIF" : "MATI"}
      </button>

      {/* State visualizer + status */}
      <div className="flex-1 flex flex-col items-center justify-center min-h-0">
        <div className="relative w-28 h-28 flex items-center justify-center">
          <AudioVisualizer vionaStatus={state} isConnected={true} className="w-full h-full scale-110" />
        </div>
        <p className="mt-4 text-sm font-medium text-slate-700 dark:text-slate-300 text-center">
          {statusText}
        </p>
      </div>

      {/* CENTER: Push-to-talk hero button */}
      <button
        onPointerDown={handlePTTDown}
        onPointerUp={handlePTTUp}
        onPointerLeave={handlePTTUp}
        onContextMenu={(e) => e.preventDefault()}
        className={`flex flex-col items-center justify-center w-24 h-24 rounded-full shadow-lg select-none touch-none transition-all ${
          isPTTHeld
            ? "bg-blue-600 text-white scale-105 ring-4 ring-blue-300 dark:ring-blue-800"
            : "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 hover:bg-blue-200 active:scale-95"
        }`}
        title="Tahan untuk bicara (atau tekan Spasi)"
      >
        <Mic className="w-9 h-9" />
        <span className="text-[11px] font-semibold mt-1">
          {isPTTHeld ? "Merekam" : "Tahan bicara"}
        </span>
      </button>
      <p className="mt-2 text-[11px] text-slate-400">Tahan tombol atau <kbd className="px-1 rounded bg-slate-100 dark:bg-slate-800">Spasi</kbd></p>

      {/* Secondary controls: mute + stop (contextual) */}
      <div className="mt-4 flex items-center justify-center gap-3">
        <button
          onClick={toggleMute}
          className={`p-3 rounded-full transition-all shadow-sm ${
            isMuted
              ? "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400 hover:bg-red-200"
              : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200 hover:bg-slate-200"
          }`}
          title={isMuted ? "Nyalakan Mikrofon (hands-free)" : "Matikan Mikrofon (hands-free)"}
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
