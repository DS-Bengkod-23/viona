"use client"

import { useMemo } from "react"
import { Mic, MicOff } from "lucide-react"
import { AudioVisualizer } from "../voice-assistant/audio-visualizer"

interface VoiceModeProps {
  voiceConnection: any
}

export function VoiceMode({ voiceConnection }: VoiceModeProps) {
  const { agentState: state, sttError, isMuted, toggleMute } = voiceConnection

  const statusText = useMemo(() => {
    switch (state) {
      case "listening": return "Viona sedang mendengarkan..."
      case "speaking": return "Viona sedang berbicara..."
      case "thinking": return "Viona sedang memikirkan..."
      default: return "Menunggu..."
    }
  }, [state])

  return (
    <div className="flex flex-col items-center justify-center flex-1 h-full py-8">
      <div className="relative w-48 h-48 flex items-center justify-center">
        <AudioVisualizer vionaStatus={state} isConnected={true} className="w-full h-full scale-125" />
      </div>

      <div className="mt-8 text-center">
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300 transition-all">
          {statusText}
        </p>
        <p className="text-xs text-slate-500 mt-2">
          {state === "listening" 
            ? "Bicara sekarang, Viona akan menjawab saat kamu selesai berbicara." 
            : ""}
        </p>
        
        <div className="mt-6 flex justify-center">
          <button
            onClick={toggleMute}
            className={`p-4 rounded-full transition-all shadow-md ${
              isMuted 
                ? "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400 hover:bg-red-200" 
                : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200 hover:bg-slate-200"
            }`}
            title={isMuted ? "Nyalakan Mikrofon" : "Matikan Mikrofon"}
          >
            {isMuted ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
          </button>
        </div>

        {sttError && (
          <p className="text-xs text-red-500 mt-4 px-4 bg-red-50 dark:bg-red-900/20 py-2 rounded-md">
            {sttError}
          </p>
        )}
      </div>
    </div>
  )
}
