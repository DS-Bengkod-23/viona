"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { Send, Sun, Moon } from "lucide-react"
import { useTheme } from "next-themes"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
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
const SILENCE_MS = 1400
// Ignore ultra-short blips (a cough, "eh") so background noise never fires a turn.
const MIN_CHARS = 2

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

export function VoiceAssistant() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isBotSpeaking, setIsBotSpeaking] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [selectedMaterial, setSelectedMaterial] = useState("matematika")
  const [selectedVersion, setSelectedVersion] = useState("v1")
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
  // Latest processUserInput, reachable from recognition callbacks without stale closure
  const processUserInputRef = useRef<(text: string) => void>(() => {})

  // Ref mirrors for use inside recognition callbacks (avoids stale closure)
  const isBotSpeakingRef = useRef(false)
  const isConnectedRef   = useRef(false)
  const isMutedRef       = useRef(false)
  const isProcessingRef  = useRef(false)

  // Initialize speech synthesis
  useEffect(() => {
    synthRef.current = window.speechSynthesis
  }, [])

  // Auto-scroll chat container only (not the whole page)
  useEffect(() => {
    const el = chatScrollRef.current
    if (el) el.scrollTop = el.scrollHeight
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
    utterance.lang = "id-ID"
    utterance.rate = 0.9
    utterance.pitch = 1

    utterance.onstart = () => setIsBotSpeaking(true)
    utterance.onend = () => {
      setIsBotSpeaking(false)
      if (isConnectedRef.current && !isMutedRef.current) {
        startListening()
      }
    }
    utterance.onerror = () => {
      setIsBotSpeaking(false)
      if (isConnectedRef.current && !isMutedRef.current) {
        startListening()
      }
    }

    synthRef.current.speak(utterance)
  }, [stopListening])

  // Process user input and generate response
  const processUserInput = useCallback(
    async (userText: string) => {
      // Guard against double-processing
      if (isProcessingRef.current) return
      isProcessingRef.current = true

      stopListening()

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
      try {
        const res = await fetch("/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: userText,
            material_id: selectedMaterial,
            version: selectedVersion,
          }),
        })
        if (res.ok) {
          const data = await res.json()
          response = data.response
        } else {
          throw new Error("Backend error status: " + res.status)
        }
      } catch (err) {
        console.warn("Using fallback local response due to:", err)
        await new Promise((resolve) => setTimeout(resolve, 800))
        response = generateResponse(userText)
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
      setIsProcessing(false)
      isProcessingRef.current = false

      // Speak the response
      speak(response)
    },
    [speak, stopListening, selectedMaterial, selectedVersion]
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
        content: "Halo! Saya Viona, asisten virtual Anda. Ada yang bisa saya bantu hari ini?",
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
            src="/viona-logo-new.png"
            alt="Viona Logo"
            className="w-10 h-10 object-contain"
          />
          <h1 className="text-2xl font-bold bg-linear-to-r from-fuchsia-500 via-violet-600 to-purple-800 bg-clip-text text-transparent mr-4">
            VIONA
          </h1>
        </div>

        {/* LMS Material & Version Dropdowns */}
        <div className="flex items-center gap-3">
          <Select value={selectedMaterial} onValueChange={setSelectedMaterial}>
            <SelectTrigger className="w-[150px] h-9">
              <SelectValue placeholder="Pilih Materi" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="matematika">📐 Matematika</SelectItem>
              <SelectItem value="fisika">⚡ Fisika</SelectItem>
              <SelectItem value="pemrograman">💻 Pemrograman</SelectItem>
              <SelectItem value="sejarah">📜 Sejarah</SelectItem>
            </SelectContent>
          </Select>

          <Select value={selectedVersion} onValueChange={setSelectedVersion}>
            <SelectTrigger className="w-[120px] h-9">
              <SelectValue placeholder="Pilih Versi" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="v1">Versi 1.0</SelectItem>
              <SelectItem value="v2">Versi 2.0</SelectItem>
              <SelectItem value="v3">Versi 3.0</SelectItem>
            </SelectContent>
          </Select>
        </div>

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
                        src="/viona-logo-new.png"
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

// Simple response generator
function generateResponse(input: string): string {
  const lowerInput = input.toLowerCase()

  if (lowerInput.includes("harga") || lowerInput.includes("biaya")) {
    return "Untuk informasi harga, kami memiliki beberapa paket yang bisa disesuaikan dengan kebutuhan Anda. Apakah Anda ingin saya jelaskan paket-paket yang tersedia?"
  }

  if (lowerInput.includes("jam") || lowerInput.includes("buka") || lowerInput.includes("operasional")) {
    return "Layanan kami tersedia setiap hari dari pukul 08.00 hingga 22.00 WIB. Untuk layanan darurat, kami siap 24 jam."
  }

  if (lowerInput.includes("lokasi") || lowerInput.includes("alamat") || lowerInput.includes("kantor")) {
    return "Kantor pusat kami berlokasi di Jakarta. Kami juga memiliki cabang di beberapa kota besar di Indonesia. Kota mana yang paling dekat dengan Anda?"
  }

  if (lowerInput.includes("keluhan") || lowerInput.includes("komplain") || lowerInput.includes("masalah")) {
    return "Saya mohon maaf atas ketidaknyamanan yang Anda alami. Bisa Anda ceritakan lebih detail mengenai masalah yang terjadi agar saya dapat membantu menyelesaikannya?"
  }

  if (lowerInput.includes("terima kasih") || lowerInput.includes("makasih")) {
    return "Sama-sama! Senang bisa membantu Anda. Apakah ada hal lain yang bisa saya bantu?"
  }

  if (lowerInput.includes("bantuan") || lowerInput.includes("help") || lowerInput.includes("tolong")) {
    return "Tentu, saya siap membantu! Anda bisa bertanya tentang produk, layanan, harga, jam operasional, atau menyampaikan keluhan. Apa yang ingin Anda ketahui?"
  }

  if (lowerInput.includes("halo") || lowerInput.includes("hai") || lowerInput.includes("hi")) {
    return "Halo! Senang bertemu dengan Anda. Ada yang bisa saya bantu hari ini?"
  }

  return "Terima kasih atas pertanyaan Anda. Untuk memberikan jawaban yang tepat, bisa Anda jelaskan lebih detail apa yang ingin Anda ketahui?"
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
