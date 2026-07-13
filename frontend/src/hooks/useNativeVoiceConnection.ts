"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { normalizeForSpeech } from "@/lib/tts-text"

const SILENCE_MS = 800
const MIN_CHARS = 2

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

export type ConnectionState = "disconnected" | "connected"
export type AgentState = "idle" | "listening" | "thinking" | "speaking"

export function useNativeVoiceConnection() {
  const [messages, setMessages] = useState<Message[]>([])
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected")
  const [agentState, setAgentState] = useState<AgentState>("idle")
  const [isMuted, setIsMuted] = useState(false)
  const [interimText, setInterimText] = useState("")
  const [sttError, setSttError] = useState("")
  
  const synthRef = useRef<SpeechSynthesis | null>(null)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const finalTranscriptRef = useRef("")
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

  // Ref mirrors to avoid stale closures inside event listeners
  const stateRef = useRef({
    isConnected: false,
    isBotSpeaking: false,
    isProcessing: false,
    isMuted: false,
  })

  useEffect(() => {
    stateRef.current.isConnected = connectionState === "connected"
    stateRef.current.isBotSpeaking = agentState === "speaking"
    stateRef.current.isProcessing = agentState === "thinking"
    stateRef.current.isMuted = isMuted
  }, [connectionState, agentState, isMuted])

  // Initialize SpeechSynthesis
  useEffect(() => {
    if (typeof window !== "undefined") {
      synthRef.current = window.speechSynthesis
    }
  }, [])

  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
  }, [])

  const stopListening = useCallback(() => {
    clearSilenceTimer()
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    finalTranscriptRef.current = ""
    setInterimText("")
    if (stateRef.current.isConnected && !stateRef.current.isProcessing && !stateRef.current.isBotSpeaking) {
       // Only go back to idle if we aren't in another state
       setAgentState("idle")
    }
  }, [clearSilenceTimer])

  const startListening = useCallback(() => {
    if (typeof window === "undefined") return
    if (stateRef.current.isBotSpeaking || stateRef.current.isProcessing) return

    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognitionAPI) {
      setSttError("Browser ini tidak mendukung pengenalan suara. Gunakan Google Chrome atau Microsoft Edge.")
      return
    }

    if (recognitionRef.current) {
      recognitionRef.current.stop()
    }

    const recognition = new SpeechRecognitionAPI()
    recognition.lang = "id-ID"
    recognition.interimResults = true
    recognition.continuous = true
    
    finalTranscriptRef.current = ""
    
    const scheduleEndOfTurn = () => {
      clearSilenceTimer()
      silenceTimerRef.current = setTimeout(() => {
        const text = finalTranscriptRef.current.trim()
        finalTranscriptRef.current = ""
        setInterimText("")
        if (text.length >= MIN_CHARS && !stateRef.current.isBotSpeaking && !stateRef.current.isProcessing) {
          recognition.stop()
          processUserInput(text)
        }
      }, SILENCE_MS)
    }

    recognition.onstart = () => {
      setAgentState("listening")
      setSttError("")
    }

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      if (stateRef.current.isBotSpeaking || stateRef.current.isProcessing) return
      
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
      setInterimText(live)
      
      if (live) scheduleEndOfTurn()
    }

    recognition.onend = () => {
      if (stateRef.current.isConnected && !stateRef.current.isMuted && !stateRef.current.isBotSpeaking && !stateRef.current.isProcessing) {
        setAgentState("idle")
        setTimeout(() => startListening(), 300)
      }
    }

    recognition.onerror = (event: Event) => {
      clearSilenceTimer()
      const err = (event as unknown as { error?: string }).error ?? "unknown"
      
      if (err === "network" || err === "service-not-allowed") {
        setSttError("Layanan pengenalan suara diblokir oleh browser.")
      } else if (err === "not-allowed") {
        setSttError("Izin mikrofon ditolak.")
      } else if (err === "audio-capture") {
        setSttError("Mikrofon tidak terdeteksi.")
      }

      if (stateRef.current.isConnected && !stateRef.current.isMuted && !stateRef.current.isBotSpeaking && !stateRef.current.isProcessing && err !== "network" && err !== "service-not-allowed" && err !== "not-allowed") {
        setTimeout(() => startListening(), 1000)
      } else {
        setAgentState("idle")
      }
    }

    recognitionRef.current = recognition
    try {
      recognition.start()
    } catch {
      // Already running
    }
  }, [clearSilenceTimer])

  // Simple response generator as fallback
  const generateResponse = (input: string): string => {
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

  const speak = useCallback((text: string) => {
    if (!synthRef.current) return

    stopListening()
    synthRef.current.cancel()

    const utterance = new SpeechSynthesisUtterance(normalizeForSpeech(text))
    utteranceRef.current = utterance // Prevent garbage collection
    utterance.lang = "id-ID"
    utterance.rate = 0.9
    utterance.pitch = 1

    utterance.onstart = () => setAgentState("speaking")
    utterance.onend = () => {
      setAgentState("idle")
      utteranceRef.current = null
      if (stateRef.current.isConnected && !stateRef.current.isMuted) {
        startListening()
      }
    }
    utterance.onerror = () => {
      setAgentState("idle")
      utteranceRef.current = null
      if (stateRef.current.isConnected && !stateRef.current.isMuted) {
        startListening()
      }
    }

    synthRef.current.speak(utterance)
  }, [stopListening, startListening])

  const processUserInput = useCallback(async (userText: string) => {
    if (stateRef.current.isProcessing) return
    
    stopListening()
    setAgentState("thinking")

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userText,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])

    let response = ""
    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText, material_id: "matematika", version: "v1" }),
      })
      if (res.ok) {
        const data = await res.json()
        response = data.response
      } else {
        throw new Error("Backend error status: " + res.status)
      }
    } catch (err) {
      console.warn("Using fallback local response due to:", err)
      await new Promise(resolve => setTimeout(resolve, 800))
      response = generateResponse(userText)
    }

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: response,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, assistantMessage])
    speak(response)
  }, [speak, stopListening])

  // Explicit text submission (from chat UI)
  const sendText = useCallback((text: string) => {
    if (text.trim() && stateRef.current.isConnected) {
      processUserInput(text.trim())
    }
  }, [processUserInput])

  const connect = useCallback(async () => {
    try {
      micStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    } catch {
      // Permission denied, but we can still connect and speak back
    }
    
    setConnectionState("connected")
    setMessages([])
    
    const welcomeMessage: Message = {
      id: "welcome",
      role: "assistant",
      content: "Ada yang bisa saya bantu hari ini?",
      timestamp: new Date(),
    }
    setMessages([welcomeMessage])
    
    // Simulate connection delay for UI
    setTimeout(() => {
      speak(welcomeMessage.content)
    }, 500)
  }, [speak])

  const disconnect = useCallback(() => {
    if (synthRef.current) synthRef.current.cancel()
    stopListening()
    micStreamRef.current?.getTracks().forEach(t => t.stop())
    micStreamRef.current = null
    
    setConnectionState("disconnected")
    setAgentState("idle")
    setMessages([])
  }, [stopListening])

  const toggleMute = useCallback(() => {
    const newMuted = !isMuted
    setIsMuted(newMuted)
    
    if (newMuted) {
      stopListening()
    } else if (connectionState === "connected" && agentState !== "speaking") {
      startListening()
    }
  }, [isMuted, connectionState, agentState, stopListening, startListening])

  return {
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
    micStream: micStreamRef.current
  }
}
