"use client"

import { useState, useCallback } from "react"
import { Room } from "livekit-client"

export type ConnectionState = "disconnected" | "connecting" | "connected" | "error"
export type AgentState = "idle" | "listening" | "thinking" | "speaking"

export function useLiveKitConnection(lmsContext: string = "") {
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected")
  const [agentState, setAgentState] = useState<AgentState>("idle")
  // We no longer manage the room manually — the LiveKit components own the room lifecycle
  const [room, setRoom] = useState<Room | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [livekitUrl, setLivekitUrl] = useState<string | null>(null)

  const connect = useCallback(async () => {
    try {
      setConnectionState("connecting")
      setError(null)

      // Fetch token from backend via Nginx proxy using POST to send context
      const res = await fetch("/api/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lms_context: lmsContext })
      })
      if (!res.ok) {
        throw new Error("Failed to fetch LiveKit token")
      }
      
      const data = await res.json()
      const { token, livekit_url } = data
      
      setToken(token)
      setLivekitUrl(livekit_url)
      
      // Let LiveKitRoom handle the actual WebRTC connection!
      setConnectionState("connected")
      
    } catch (err: any) {
      console.error("LiveKit connection error:", err)
      setError(err.message || "Failed to connect to LiveKit")
      setConnectionState("error")
    }
  }, [lmsContext])

  const disconnect = useCallback(async () => {
    setConnectionState("disconnected")
    setAgentState("idle")
    setRoom(null)
    setToken(null)
    setLivekitUrl(null)
  }, [])

  return {
    connectionState,
    agentState,
    room,
    error,
    token,
    livekitUrl,
    connect,
    disconnect,
  }
}

