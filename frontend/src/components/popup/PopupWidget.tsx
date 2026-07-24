"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "motion/react"
import { MessageSquare, Mic, MicOff, Maximize2, X } from "lucide-react"
import { useNativeVoiceConnection } from "@/hooks/useNativeVoiceConnection"

import { FloatingButton } from "./FloatingButton"
import { VoiceMode } from "./VoiceMode"
import { TranscriptMode } from "./TranscriptMode"
import { InsightBubbleCard } from "./InsightBubble"
import { ImageBubbleCard } from "./ImageBubble"

// Session id persist di localStorage — dibagi antara iframe widget & tab maximize
// (same-origin) supaya transkrip bisa di-restore dari Redis.
function getSessionId(): string {
  if (typeof window === "undefined") return ""
  let id = localStorage.getItem("viona-session-id")
  if (!id) {
    id = crypto?.randomUUID?.() ?? `s-${Date.now()}-${Math.random().toString(36).slice(2)}`
    localStorage.setItem("viona-session-id", id)
  }
  return id
}

export function PopupWidget() {
  // Mode "full" = dibuka dari tombol Maximize (/dashboard/widget?full=1): tampil penuh,
  // tanpa floating button, langsung mulai (restore session yang sama). Ditentukan di
  // useEffect (bukan saat init) agar tidak memicu hydration mismatch SSR.
  const [isFull, setIsFull] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [mode, setMode] = useState<"voice" | "transcript">("voice")
  const [lmsContext, setLmsContext] = useState<string>("")
  const [syllabus, setSyllabus] = useState<string>("")
  const [quotedText, setQuotedText] = useState<string>("")
  const [isQuizPage, setIsQuizPage] = useState(false)
  const [courseTitle, setCourseTitle] = useState("")
  const [sessionId] = useState(getSessionId)
  // started = user sudah menekan "Mulai" (atau mode full). Sebelum itu → layar intro.
  const [started, setStarted] = useState(false)
  const [micDenied, setMicDenied] = useState(false)

  // Deteksi mode full setelah mount (client-only).
  useEffect(() => {
    if (typeof window === "undefined") return
    if (new URLSearchParams(window.location.search).get("full") === "1") {
      setIsFull(true)
      setIsOpen(true)
      setStarted(true)
    }
  }, [])

  const voiceConnection = useNativeVoiceConnection(lmsContext, syllabus, isQuizPage, courseTitle, sessionId)
  const { connectionState, connect, disconnect, activeBubble, activeImage } = voiceConnection

  // Sambungkan otomatis saat pop up terbuka supaya wake word bisa langsung bekerja
  // (Minta izin mikrofon di latar belakang).
  useEffect(() => {
    if (isOpen && connectionState === "disconnected") {
      // Mulai dengan mode Mute = Wake Word Mode
      connect({ startMuted: true, autoGreeting: false })
    }
  }, [isOpen, connectionState, connect])

  // Kalau Viona sudah merespons (misal via wake word) atau mic terbuka dari wake word, langsung hilangkan layar "Mulai"
  useEffect(() => {
    if (!voiceConnection.isMuted && !started) {
      setStarted(true)
    }
    if (voiceConnection.agentState === "thinking" && !started) {
      setStarted(true)
    }
  }, [voiceConnection.isMuted, voiceConnection.agentState, started])

  // Resize iframe induk (kalau embedded)
  useEffect(() => {
    if (typeof window !== "undefined" && window.parent !== window) {
      window.parent.postMessage({ type: "viona-resize", isOpen }, "*")
    }
  }, [isOpen])

  // Terima lms-context & viona-quote dari iframe induk
  useEffect(() => {
    if (typeof window === "undefined") return
    const handleMessage = (event: MessageEvent) => {
      if (event.data && event.data.type === "viona-context") {
        setLmsContext(event.data.text || "")
        setSyllabus(event.data.syllabus || "")
        setIsQuizPage(!!event.data.isQuiz)
        if (event.data.courseTitle) setCourseTitle(event.data.courseTitle)
      } else if (event.data && event.data.type === "viona-quote") {
        setQuotedText(event.data.text || "")
        setIsOpen(true)
        setMode("transcript")
      }
    }
    window.addEventListener("message", handleMessage)
    return () => window.removeEventListener("message", handleMessage)
  }, [])

  // Klik "Mulai": hilangkan layar intro (sudah connect otomatis di atas)
  const handleStart = async () => {
    if (connectionState === "disconnected") {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach((t) => t.stop())
        connect({ startMuted: true, autoGreeting: false })
      } catch {
        setMicDenied(true)
        setMode("transcript")
      }
    }
    setStarted(true)
    // Pengguna meminta agar sapaan selalu dimainkan setiap kali klik "Mulai"
    voiceConnection.playGreeting()
  }

  const handleMaximize = () => {
    setIsOpen(false)
    window.open(window.location.origin + "/dashboard", "_blank")
  }

  const handleClose = () => {
    if (isFull) {
      window.close()
      return
    }
    setIsOpen(false)
    setStarted(false)
    disconnect()
  }

  const body = () => {
    if (!started) {
      return (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 p-6 text-center">
          <img src="/dashboard/viona-logo-new.png" alt="Viona" className="w-14 h-14 object-contain" />
          <p className="text-base font-semibold text-slate-800 dark:text-slate-100">
            Siap belajar bareng Viona?
          </p>
          <p className="text-xs text-slate-500 max-w-[240px]">
            Viona mendengarkan lewat mikrofon. Ucapkan &quot;Hai Viona&quot; atau tahan tombol untuk bertanya.
          </p>
          <button
            onClick={handleStart}
            className="mt-1 px-6 py-2.5 text-sm font-semibold rounded-lg bg-violet-600 text-white hover:bg-violet-700 transition-colors"
          >
            Mulai
          </button>
        </div>
      )
    }
    if (micDenied && mode === "voice") {
      return (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 p-6 text-center">
          <MicOff className="w-8 h-8 text-red-500" />
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Akses mikrofon ditolak</p>
          <p className="text-xs text-slate-500">Kamu masih bisa mengobrol lewat teks.</p>
          <button
            onClick={() => setMode("transcript")}
            className="mt-1 px-4 py-2 text-sm font-medium rounded-lg bg-violet-600 text-white hover:bg-violet-700 transition-colors"
          >
            Gunakan Mode Teks
          </button>
        </div>
      )
    }
    if (connectionState !== "connected") {
      return (
        <div className="flex-1 flex items-center justify-center p-6 text-center">
          <p className="text-sm text-slate-500">Mempersiapkan asisten...</p>
        </div>
      )
    }
    return mode === "voice" ? (
      <VoiceMode voiceConnection={voiceConnection} />
    ) : (
      <TranscriptMode
        voiceConnection={voiceConnection}
        quotedText={quotedText}
        setQuotedText={setQuotedText}
      />
    )
  }

  const header = (
    <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900">
      <div className="flex items-center gap-2">
        <img src="/dashboard/viona-logo-new.png" alt="Viona" className="w-8 h-8 object-contain" />
        <div className="flex flex-col">
          <span className="font-bold text-sm bg-linear-to-r from-violet-600 via-violet-700 to-indigo-600 bg-clip-text text-transparent">
            VIONA
          </span>
          <span className="text-[10px] text-slate-500 font-medium">AI Assistant Bengkel Koding</span>
        </div>
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={() => setMode(mode === "voice" ? "transcript" : "voice")}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          {mode === "voice" ? (
            <>
              <MessageSquare className="w-3.5 h-3.5" /> Switch to Transcript
            </>
          ) : (
            <>
              <Mic className="w-3.5 h-3.5" /> Switch to Voice
            </>
          )}
        </button>
        {!isFull && (
          <button
            onClick={handleMaximize}
            className="p-1.5 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
            title="Maximize"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        )}
        <button
          onClick={handleClose}
          className="p-1.5 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
          title="Close"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  )

  // Sembunyikan widget sepenuhnya di halaman quiz (kecuali mode full/maximize).
  if (isQuizPage && !isFull) {
    return null
  }

  // Full-page (dari Maximize): tampil penuh tanpa floating button.
  if (isFull) {
    return (
      <div className="fixed inset-0 z-50 flex flex-col bg-white dark:bg-slate-900">
        <InsightBubbleCard bubble={activeBubble} />
        <ImageBubbleCard image={activeImage} />
        {header}
        <div className="flex-1 relative overflow-hidden flex flex-col">{body()}</div>
      </div>
    )
  }

  return (
    <>
      <FloatingButton onClick={() => setIsOpen(true)} isOpen={isOpen} />

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.95 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed bottom-6 right-6 z-50 w-[320px] h-115 max-w-[calc(100vw-32px)] max-h-[calc(100vh-32px)]"
          >
            <InsightBubbleCard bubble={activeBubble} />
            <ImageBubbleCard image={activeImage} />

            <div className="w-full h-full bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col overflow-hidden">
              {header}
              <div className="flex-1 relative overflow-hidden flex flex-col">{body()}</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
