"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { Send, Sun, Moon, Minimize2 } from "lucide-react"
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
import { normalizeForSpeech } from "@/lib/tts-text"

// ── Speech endpointing (browser Web Speech API) ─────────────────────────────
// The browser gives us words but no reliable "user finished" signal, so we
// detect end-of-turn ourselves: after the last detected speech, wait
// SILENCE_MS of quiet before submitting the turn.
//   • Viona cuts you off mid-sentence?  -> raise SILENCE_MS
//   • Feels sluggish to respond?        -> lower SILENCE_MS
const SILENCE_MS = 800
// Ignore ultra-short blips (a cough, "eh") so background noise never fires a turn.
const MIN_CHARS = 2
// Jumlah pesan terakhir yang dikirim sebagai riwayat percakapan ke backend.
const HISTORY_TURNS = 6

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  image?: string | null
}

export function VoiceAssistant() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isBotSpeaking, setIsBotSpeaking] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [textInput, setTextInput] = useState("")
  const [hasCompletedSession, setHasCompletedSession] = useState(false)
  const [mounted, setMounted] = useState(false)
  const [interimText, setInterimText] = useState("")
  const [sttError, setSttError] = useState("")

  const vionaStatus: "idle" | "thinking" | "speaking" | "ready" =
    isBotSpeaking ? "speaking" : isProcessing ? "thinking" : isConnected ? "ready" : "idle"

  const userStatus: "idle" | "speaking" | "listening" =
    isBotSpeaking ? "listening" : isConnected && isRecording && !isMuted ? "speaking" : "idle"

  const { resolvedTheme, setTheme } = useTheme()

  useEffect(() => setMounted(true), [])

  // Keep refs in sync so recognition callbacks always read current values
  useEffect(() => {
    isBotSpeakingRef.current = isBotSpeaking
    isConnectedRef.current   = isConnected
    isMutedRef.current       = isMuted
  }, [isBotSpeaking, isConnected, isMuted])

  const chatScrollRef  = useRef<HTMLDivElement>(null)
  const synthRef = useRef<SpeechSynthesis | null>(null)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)

  // Turn accumulation + silence timer for our own end-of-turn detection
  const finalTranscriptRef = useRef("")
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)
  // Latest processUserInput, reachable from recognition callbacks without stale closure
  const processUserInputRef = useRef<(text: string) => void>(() => {})

  // Ref mirrors for use inside recognition callbacks (avoids stale closure)
  const isBotSpeakingRef = useRef(false)
  const isConnectedRef   = useRef(false)
  const isMutedRef       = useRef(false)
  const isProcessingRef  = useRef(false)
  // Mirror of `messages`, read inside processUserInput's closure to build chat
  // history for the backend without depending on `messages` (avoids re-creating
  // the callback and stale closures in recognition event handlers).
  const messagesRef = useRef<Message[]>([])

  // Initialize speech synthesis
  useEffect(() => {
    synthRef.current = window.speechSynthesis
  }, [])

  // Auto-scroll chat container only (not the whole page)
  useEffect(() => {
    const el = chatScrollRef.current
    if (el) el.scrollTop = el.scrollHeight
    messagesRef.current = messages
  }, [messages])

  // Start/stop recognition when connection changes
  useEffect(() => {
    if (isConnected) {
      startListening()
    } else {
      stopListening()
    }
  }, [isConnected])

  // Cancel a pending end-of-turn countdown
  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
  }, [])

  // Stop listening
  const stopListening = useCallback(() => {
    clearSilenceTimer()
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    finalTranscriptRef.current = ""
    setInterimText("")
    setIsRecording(false)
  }, [clearSilenceTimer])

  // Start continuous listening with our own end-of-turn detection
  const startListening = useCallback(() => {
    if (typeof window === "undefined") return
    if (isBotSpeakingRef.current) return   // never listen while Viona is talking

    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
    console.info("[STT] startListening — SpeechRecognition available:", !!SpeechRecognitionAPI)
    if (!SpeechRecognitionAPI) {
      console.warn("[STT] no SpeechRecognition API in this browser")
      setSttError(
        "Browser ini tidak mendukung pengenalan suara. Gunakan Google Chrome atau Microsoft Edge.",
      )
      return
    }

    if (recognitionRef.current) {
      recognitionRef.current.stop()
    }

    const recognition = new SpeechRecognitionAPI()
    recognition.lang = "id-ID"
    recognition.interimResults = true   // live partials so we can show + time the turn
    recognition.continuous = true       // keep the stream open; WE decide when a turn ends

    finalTranscriptRef.current = ""

    // Fires after SILENCE_MS of no new speech = the user finished their turn.
    const scheduleEndOfTurn = () => {
      clearSilenceTimer()
      silenceTimerRef.current = setTimeout(() => {
        const text = finalTranscriptRef.current.trim()
        finalTranscriptRef.current = ""
        setInterimText("")
        if (text.length >= MIN_CHARS && !isBotSpeakingRef.current && !isProcessingRef.current) {
          recognition.stop()   // end this session; onend won't restart while processing
          processUserInputRef.current(text)
        }
      }, SILENCE_MS)
    }

    recognition.onstart = () => {
      console.info("[STT] onstart — listening")
      setIsRecording(true)
      setSttError("")   // recognition actually started — clear any stale error
    }

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      if (isBotSpeakingRef.current || isProcessingRef.current) return
      const results = event.results as unknown as ArrayLike<{
        0: { transcript: string }
        isFinal: boolean
      }>
      const startIdx = (event as unknown as { resultIndex?: number }).resultIndex ?? 0
      let interim = ""
      for (let i = startIdx; i < results.length; i++) {
        const res = results[i]
        if (res.isFinal) finalTranscriptRef.current += res[0].transcript + " "
        else interim += res[0].transcript
      }
      const live = (finalTranscriptRef.current + interim).trim()
      if (live) console.debug("[STT] heard:", live)
      setInterimText(live)
      if (live) scheduleEndOfTurn()   // any speech resets the "finished" countdown
    }

    recognition.onend = () => {
      setIsRecording(false)
      // Chrome ends continuous sessions periodically; reopen unless we're mid-turn.
      if (
        isConnectedRef.current &&
        !isMutedRef.current &&
        !isBotSpeakingRef.current &&
        !isProcessingRef.current
      ) {
        setTimeout(() => startListening(), 300)
      }
    }

    recognition.onerror = (event: Event) => {
      setIsRecording(false)
      clearSilenceTimer()
      const err = (event as unknown as { error?: string }).error ?? "unknown"
      console.warn("[STT] onerror:", err)
      // Fatal errors: surface a clear, actionable message instead of failing silently.
      if (err === "network" || err === "service-not-allowed") {
        setSttError(
          "Layanan pengenalan suara diblokir oleh browser. Brave & Firefox mematikan Web Speech — buka demo di Google Chrome.",
        )
      } else if (err === "not-allowed") {
        setSttError(
          "Izin mikrofon ditolak. Klik ikon gembok di address bar → izinkan Microphone, lalu Connect ulang.",
        )
      } else if (err === "audio-capture") {
        setSttError("Mikrofon tidak terdeteksi. Pastikan perangkat mic aktif dan dipilih.")
      }
      // 'no-speech' / 'aborted' are benign; just let it restart below.
      if (
        isConnectedRef.current &&
        !isMutedRef.current &&
        !isBotSpeakingRef.current &&
        !isProcessingRef.current &&
        err !== "network" &&
        err !== "service-not-allowed" &&
        err !== "not-allowed"
      ) {
        setTimeout(() => startListening(), 1000)
      }
    }

    recognitionRef.current = recognition

    try {
      recognition.start()
    } catch {
      // Already running
    }
  }, [clearSilenceTimer])

  // Speak text using TTS
  const speak = useCallback((text: string) => {
    if (!synthRef.current) return

    // Stop mic BEFORE TTS plays so recognition cannot pick up Viona's voice
    stopListening()
    synthRef.current.cancel()

    const utterance = new SpeechSynthesisUtterance(normalizeForSpeech(text))
    utteranceRef.current = utterance // Prevent garbage collection
    utterance.lang = "id-ID"
    utterance.rate = 0.9
    utterance.pitch = 1

    utterance.onstart = () => setIsBotSpeaking(true)
    utterance.onend = () => {
      setIsBotSpeaking(false)
      utteranceRef.current = null
      if (isConnectedRef.current && !isMutedRef.current) {
        startListening()
      }
    }
    utterance.onerror = () => {
      setIsBotSpeaking(false)
      utteranceRef.current = null
      if (isConnectedRef.current && !isMutedRef.current) {
        startListening()
      }
    }

    synthRef.current.speak(utterance)
  }, [stopListening, startListening])

  // Process user input and generate response
  const processUserInput = useCallback(
    async (userText: string) => {
      // Guard against double-processing
      if (isProcessingRef.current) return
      isProcessingRef.current = true

      stopListening()

      // Giliran terakhir SEBELUM pesan user baru ditambahkan, supaya backend
      // punya konteks percakapan untuk pertanyaan lanjutan.
      const history = messagesRef.current.slice(-HISTORY_TURNS).map((m) => ({
        role: m.role,
        content: m.content,
      }))

      // Add user message
      const userMessage: Message = {
        id: Date.now().toString(),
        role: "user",
        content: userText,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMessage])

      setIsProcessing(true)

      let response = ""
      let image: string | null = null
      try {
        const res = await fetch("/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: userText,
            history,
          }),
        })
        if (res.ok) {
          const data = await res.json()
          response = data.response
          image = data.image ?? null
        } else {
          throw new Error("Backend error status: " + res.status)
        }
      } catch (err) {
        console.warn("Backend /chat failed:", err)
        response = "Maaf kak, koneksi ke server sedang bermasalah. Coba lagi ya."
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response,
        timestamp: new Date(),
        image,
      }

      setMessages((prev) => [...prev, assistantMessage])
      setIsProcessing(false)
      isProcessingRef.current = false

      // Speak the response
      speak(response)
    },
    [speak, stopListening]
  )

  // Keep the latest processUserInput reachable from recognition callbacks
  useEffect(() => {
    processUserInputRef.current = processUserInput
  }, [processUserInput])

  // Handle connect/disconnect
  const handleConnectionToggle = async () => {
    if (isConnected) {
      if (synthRef.current) synthRef.current.cancel()
      stopListening()
      micStreamRef.current?.getTracks().forEach((t) => t.stop())
      micStreamRef.current = null
      if (messages.length > 1) setHasCompletedSession(true)
      setIsConnected(false)
      setMessages([])
      setIsBotSpeaking(false)
      setIsProcessing(false)
    } else {
      // Request mic BEFORE SpeechRecognition so AudioContext gets real data
      try {
        micStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      } catch {
        // mic denied — visualizer will stay idle, voice still works via SpeechRecognition
      }
      setHasCompletedSession(false)
      setIsConnected(true)
      const welcomeMessage: Message = {
        id: "welcome",
        role: "assistant",
        content: "Ada yang bisa saya bantu hari ini?",
        timestamp: new Date(),
      }
      setMessages([welcomeMessage])
      setTimeout(() => speak(welcomeMessage.content), 500)
    }
  }

  // Handle mute toggle
  const handleMuteToggle = () => {
    const newMuted = !isMuted
    setIsMuted(newMuted)
    
    if (newMuted) {
      stopListening()
    } else if (isConnected && !isBotSpeaking) {
      startListening()
    }
  }

  // Minimize back: this page is opened via window.open() from the popup
  // widget's Maximize button, so closing it returns the user to the popup.
  // If opened directly (no opener, e.g. bookmark), fall back to the LMS home.
  const handleMinimize = () => {
    if (window.opener) {
      window.close()
    } else {
      window.location.href = "/"
    }
  }

  // Handle text input submission
  const handleTextSubmit = (e: { preventDefault(): void }) => {
    e.preventDefault()
    if (textInput.trim() && isConnected) {
      processUserInput(textInput.trim())
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
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Bot Audio</CardTitle>
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
                isMuted={isMuted}
                isConnected={isConnected}
                onToggleMute={handleMuteToggle}
                micStream={micStreamRef.current}
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
                        image={message.image}
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
