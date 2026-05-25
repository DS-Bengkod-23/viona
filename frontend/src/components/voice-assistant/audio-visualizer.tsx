"use client"

import { useTheme } from "next-themes"
import type { AgentState } from "@livekit/components-react"
import { AgentAudioVisualizerAura } from "@/components/agents-ui/agent-audio-visualizer-aura"
import { cn } from "@/lib/utils"

interface AudioVisualizerProps {
  vionaStatus: "idle" | "thinking" | "speaking" | "ready"
  isConnected: boolean
  className?: string
}

function toAgentState(status: string, connected: boolean): AgentState {
  if (!connected) return "disconnected"
  switch (status) {
    case "speaking":  return "speaking"
    case "thinking":  return "thinking"
    case "ready":     return "listening"
    default:          return "idle"
  }
}

export function AudioVisualizer({ vionaStatus, isConnected, className }: AudioVisualizerProps) {
  const { resolvedTheme } = useTheme()
  const state = toAgentState(vionaStatus, isConnected)

  return (
    <div className={cn("flex items-center justify-center", className)}>
      <AgentAudioVisualizerAura
        size="md"
        state={state}
        color="#4d00ff"
        colorShift={0.3}
        themeMode={resolvedTheme as "dark" | "light" | undefined}
        className="w-40 h-40"
      />
    </div>
  )
}
