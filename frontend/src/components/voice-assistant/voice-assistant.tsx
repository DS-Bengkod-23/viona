"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { Send, Sun, Moon, Minimize2, Square } from "lucide-react"
import { useTheme } from "next-themes"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { AudioVisualizer } from "./audio-visualizer"
import { ChatMessage } from "./chat-message"
import { UserAudioInput } from "./user-audio-input"
import { StatusPanel } from "./status-panel"
import { SessionTimer } from "./session-timer"
import { FeedbackWidget } from "./feedback-widget"
import { cn } from "@/lib/utils"
import { useNativeVoiceConnection } from "@/hooks/useNativeVoiceConnection"

const getSessionId = () => {
  if (typeof window !== "undefined") {
    let id = localStorage.getItem("viona-session-id")
    if (!id) {
      id = "session-" + Math.random().toString(36).slice(2)
      localStorage.setItem("viona-session-id", id)
    }
    return id
  }
  return ""
}

export function VoiceAssistant() {
  const [sessionId] = useState(getSessionId)
  const [textInput, setTextInput] = useState("")
  const [hasCompletedSession, setHasCompletedSession] = useState(false)
  const [mounted, setMounted] = useState(false)

  const { resolvedTheme, setTheme } = useTheme()
  useEffect(() => setMounted(true), [])

  const voiceConnection = useNativeVoiceConnection("", "", false, "", sessionId)
  const {
    connectionState,
    agentState,
    messages,
    interimText,
    sttError,
    isMuted,
    connect,
    disconnect,
    sendText,
    toggleMute,
    stopSpeaking,
    micStream
  } = voiceConnection

  const isConnected = connectionState === "connected"
  const isBotSpeaking = agentState === "speaking"
  const isProcessing = agentState === "thinking"
  const isRecording = agentState === "listening"

  const vionaStatus = isBotSpeaking ? "speaking" : isProcessing ? "thinking" : isConnected ? "ready" : "idle"
  const userStatus = isBotSpeaking ? "listening" : isConnected && isRecording && !isMuted ? "speaking" : "idle"

  const chatScrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll chat container
  useEffect(() => {
    const el = chatScrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages])

  // Auto connect on mount
  useEffect(() => {
    if (connectionState === "disconnected") {
      connect({ startMuted: true, autoGreeting: true })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleConnectionToggle = () => {
    if (isConnected) {
      if (messages.length > 1) setHasCompletedSession(true)
      disconnect()
    } else {
      setHasCompletedSession(false)
      connect({ startMuted: true, autoGreeting: true })
    }
  }

  const handleMuteToggle = () => {
    toggleMute()
  }

  const handleMinimize = () => {
    if (window.opener) {
      window.close()
    } else {
      window.location.href = "/"
    }
  }

  const handleTextSubmit = (e: { preventDefault(): void }) => {
    e.preventDefault()
    if (textInput.trim() && isConnected) {
      sendText(textInput)
      setTextInput("")
    }
  }

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-card">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
          aria-label="Toggle theme"
          className="w-30 shrink-0"
        >
          {mounted && resolvedTheme === "dark"
            ? <Sun className="w-4 h-4" />
            : <Moon className="w-4 h-4" />
          }
        </Button>
        <div className="flex items-center gap-1">
          <img
            src="/dashboard/viona-logo-new.png"
            alt="Viona Logo"
            className="w-10 h-10 object-contain"
          />
          <h1 className="text-2xl font-bold bg-linear-to-r from-violet-600 via-violet-700 to-indigo-600 bg-clip-text text-transparent mr-4">
            VIONA
          </h1>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="icon"
            onClick={handleMinimize}
            aria-label="Minimize"
            title="Minimize"
          >
            <Minimize2 className="w-4 h-4" />
          </Button>
          <Button
            onClick={handleConnectionToggle}
            className={cn(
              "min-w-30 font-medium transition-all",
              isConnected
                ? "bg-red-500 hover:bg-red-600 text-white"
                : "bg-green-500 hover:bg-green-600 text-white"
            )}
          >
            {isConnected ? "Disconnect" : "Connect"}
          </Button>
        </div>
      </header>

      {/* Main Content - 3 Column Layout */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Left Column - Audio Hub */}
        <div className="lg:w-1/4 w-full border-b lg:border-b-0 lg:border-r border-border p-4 flex flex-col gap-4 overflow-y-auto">
          {/* Bot Audio Card */}
          <Card className="flex-1">
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium">Bot Audio</CardTitle>
              {isBotSpeaking && (
                <Button 
                  variant="destructive" 
                  size="sm" 
                  onClick={stopSpeaking} 
                  className="h-6 px-2 text-xs"
                >
                  <Square className="w-3 h-3 mr-1 fill-current" /> Stop
                </Button>
              )}
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center">
              <AudioVisualizer vionaStatus={vionaStatus} isConnected={isConnected} />
              <p className="text-xs text-muted-foreground mt-2">
                {isBotSpeaking ? "Viona sedang berbicara..." : "Menunggu..."}
              </p>
            </CardContent>
          </Card>

          {/* Input Audio Card */}
          <Card className="flex-1">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Input Audio</CardTitle>
            </CardHeader>
            <CardContent>
              <UserAudioInput
                isRecording={isRecording}
                isMuted={isMuted || isBotSpeaking}
                isConnected={isConnected}
                onToggleMute={handleMuteToggle}
                micStream={micStream}
              />
            </CardContent>
          </Card>
        </div>

        {/* Center Column - Conversation */}
        <div className="lg:w-1/2 w-full border-b lg:border-b-0 lg:border-r border-border p-4 flex flex-col min-h-0">
          <Card className="flex-1 flex flex-col min-h-0 overflow-hidden py-0 gap-0">
            <CardHeader className="pt-6 pb-2 shrink-0">
              <CardTitle className="text-sm font-medium">Percakapan</CardTitle>
            </CardHeader>

            {/* Chat Area */}
            <div ref={chatScrollRef} className="flex-1 border-t border-border chat-area-bg overflow-y-auto">
              <div className="p-4">
                {!isConnected ? (
                  <div className="h-full flex items-center justify-center p-8">
                    <div className="text-center max-w-md space-y-4">
                      <img
                        src="/dashboard/viona-logo-new.png"
                        alt="Viona Logo"
                        className="w-20 h-20 mx-auto object-contain"
                      />
                      <p className="text-muted-foreground leading-relaxed">
                        Selamat datang di Viona. Silakan klik &apos;Connect&apos; untuk mulai berbicara dengan asisten virtual kami.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="pb-4">
                    {sttError && (
                      <div className="mb-4 px-4 py-3 rounded-xl border border-red-400/50 bg-red-500/10 text-red-600 dark:text-red-400 text-sm">
                        ⚠️ {sttError}
                      </div>
                    )}
                    {messages.map((message) => (
                      <ChatMessage
                        key={message.id}
                        role={message.role}
                        content={message.content}
                        timestamp={message.timestamp}
                      />
                    ))}
                    {interimText && !isProcessing && (
                      <div className="flex w-full mb-4 justify-end">
                        <div className="max-w-[85%] px-4 py-3 rounded-2xl rounded-br-md text-sm italic bg-primary/50 text-primary-foreground shadow-sm">
                          {interimText}
                          <span className="ml-1 animate-pulse">…</span>
                        </div>
                      </div>
                    )}
                    {isProcessing && (
                      <div className="flex justify-start mb-4">
                        <div className="bg-white dark:bg-white/10 border border-border px-4 py-3 rounded-2xl rounded-bl-md shadow-sm">
                          <div className="flex gap-1">
                            <span className="w-2 h-2 bg-primary/50 rounded-full animate-bounce" />
                            <span
                              className="w-2 h-2 bg-primary/50 rounded-full animate-bounce"
                              style={{ animationDelay: "0.1s" }}
                            />
                            <span
                              className="w-2 h-2 bg-primary/50 rounded-full animate-bounce"
                              style={{ animationDelay: "0.2s" }}
                            />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Text Input */}
            <form onSubmit={handleTextSubmit} className="px-6 pb-6 pt-4 border-t border-border shrink-0">
              <div className="flex items-center gap-2">
                <Input
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  placeholder="Ketik pesan di sini..."
                  disabled={!isConnected}
                  className="flex-1"
                />
                <Button
                  type="submit"
                  size="icon"
                  disabled={!isConnected || !textInput.trim()}
                  className="shrink-0"
                >
                  <Send className="w-4 h-4" />
                  <span className="sr-only">Kirim pesan</span>
                </Button>
              </div>
            </form>
          </Card>
        </div>

        {/* Right Column - Session & Status */}
        <div className="lg:w-1/4 w-full p-4 flex flex-col gap-4 overflow-y-auto h-full">
          <StatusPanel
            userStatus={userStatus}
            vionaStatus={vionaStatus}
          />
          <SessionTimer isConnected={isConnected} />
          {hasCompletedSession && !isConnected && (
            <FeedbackWidget />
          )}
        </div>
      </div>
    </div>
  )
}

declare global {
  interface SpeechRecognition extends EventTarget {
    lang: string
    interimResults: boolean
    continuous: boolean
    onstart: (() => void) | null
    onend: (() => void) | null
    onerror: ((event: Event) => void) | null
    onresult: ((event: SpeechRecognitionEvent) => void) | null
    start(): void
    stop(): void
  }

  interface SpeechRecognitionEvent extends Event {
    readonly results: SpeechRecognitionResultList
  }

  interface Window {
    SpeechRecognition: new () => SpeechRecognition
    webkitSpeechRecognition: new () => SpeechRecognition
  }
}
