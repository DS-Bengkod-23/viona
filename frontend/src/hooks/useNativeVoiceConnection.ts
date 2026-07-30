"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { normalizeForSpeech } from "@/lib/tts-text"
import { fetchTTS } from "@/lib/api"

const SILENCE_MS = 700
const MIN_CHARS = 2

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  image?: string | null
}

export type ConnectionState = "disconnected" | "connected"
export type AgentState = "idle" | "listening" | "thinking" | "speaking"

export interface InsightBubble {
  type: "insight" | "mnemonic" | "formula" | "warning"
  text: string
}

// Bubble tampil 8-10 detik setelah muncul, mulai 2-3 detik setelah Viona selesai bicara.
const BUBBLE_SHOW_DELAY_MS = 2500
const BUBBLE_VISIBLE_MS = 9000

// Jumlah pesan terakhir (gabungan user+assistant) yang dikirim sebagai riwayat
// percakapan ke backend, supaya pertanyaan lanjutan tetap paham konteks topik.
const HISTORY_TURNS = 6

// Setelah wake-word membuka gerbang, percakapan tetap "terbuka" selama ini —
// lanjutan bisa diucapkan tanpa memanggil "Hai Viona" lagi. Reset tiap giliran.
const CONVERSATION_WINDOW_MS = 10000

// Wake-word (gate). Web Speech tidak memberi confidence yang andal di mode
// continuous, jadi gate = phrase-match toleran: terima "viona" + variasi salah-dengar
// umum dari STT id-ID. `query` = teks setelah pemicu ("hai viona apa itu EDA" -> "apa itu EDA").
const WAKE_WORDS = [
  "viona", "fiona", "viyona", "fiyona", "piona", "biona",
  "vionna", "vyona", "wiona", "vi ona", "fi ona", "viana",
]
function matchWakeWord(text: string): { matched: boolean; query: string } {
  const lower = text.toLowerCase()
  for (const w of WAKE_WORDS) {
    const idx = lower.indexOf(w)
    if (idx !== -1) {
      const query = text.slice(idx + w.length).replace(/^[\s,.!?]+/, "").trim()
      return { matched: true, query }
    }
  }
  // Fallback longgar: pola "v/f/p/b/w + i + (y)o/a + n + a".
  const m = lower.match(/[vfpbw]i+\s?y?[oa]nn?a/)
  if (m) {
    const query = text.slice((m.index ?? 0) + m[0].length).replace(/^[\s,.!?]+/, "").trim()
    return { matched: true, query }
  }
  return { matched: false, query: "" }
}

// Bersihkan transkrip STT sebelum dikirim ke LLM: buang filler & rapikan spasi.
// Rule-based (nol latensi, tanpa model). Lihat rencana bagian Parafrase.
function cleanTranscript(text: string): string {
  return text
    .replace(/\b(?:e{2,}|m{2,}|eh{1,}|hmm+|anu)\b/gi, " ")
    .replace(/\s{2,}/g, " ")
    .trim()
}

export function useNativeVoiceConnection(
  lmsContext: string = "",
  syllabus: string = "",
  isQuiz: boolean = false,
  courseTitle: string = "",
  sessionId: string = "",
) {
  const [messages, setMessages] = useState<Message[]>([])
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected")
  const [agentState, setAgentState] = useState<AgentState>("idle")
  const [isMuted, setIsMuted] = useState(true)
  const [interimText, setInterimText] = useState("")
  const [sttError, setSttError] = useState("")
  const [activeBubble, setActiveBubble] = useState<InsightBubble | null>(null)
  const [activeImage, setActiveImage] = useState<string | null>(null)
  // Percakapan sedang "terbuka" (untuk indikator UI). Gate wake-word SELALU aktif;
  // window ini menandai boleh-lanjut-tanpa-wake-word selama beberapa detik.
  const [conversationActive, setConversationActive] = useState(false)

  const synthRef = useRef<SpeechSynthesis | null>(null)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const finalTranscriptRef = useRef("")
  // Teks "hidup" = hasil final + interim terbaru. Web Speech sering belum men-final-kan
  // saat silence timer menyala, jadi ini yang dibaca (bukan
  // hanya finalTranscriptRef) agar ucapan & wake-word tidak hilang di interim.
  const liveTextRef = useRef("")
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)
  // TTS Cartesia: elemen audio yang sedang diputar + request sintesis yang masih
  // terbang + object URL blob-nya (wajib di-revoke agar tidak bocor memori).
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const ttsAbortRef = useRef<AbortController | null>(null)
  const audioUrlRef = useRef<string | null>(null)
  // Nomor urut giliran bicara; dinaikkan tiap speak()/stopSpeaking() agar callback
  // ucapan lama bisa dikenali dan diabaikan.
  const speakSeqRef = useRef(0)
  // startListening is memoized once (deps never change) and calls processUserInput
  // from inside a closure created on mount — without this ref indirection it would
  // permanently call the FIRST processUserInput, frozen with lmsContext="" from
  // mount time, even after lmsContext updates from the LMS page's postMessage.
  const processUserInputRef = useRef<(text: string) => void>(() => {})
  const pendingBubblesRef = useRef<InsightBubble[]>([])
  const pendingImageRef = useRef<string | null>(null)
  const bubbleQueueRef = useRef<InsightBubble[]>([])
  const bubbleShowTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const bubbleHideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Mirror of `messages` for reading inside processUserInput's closure — that
  // callback isn't recreated when messages changes (see its deps below), so a
  // direct `messages` read there would be stale. Same pattern as stateRef.
  const messagesRef = useRef<Message[]>([])
  // Conversation window: gate wake-word terbuka sementara untuk lanjutan.
  const conversationOpenRef = useRef(false)
  const conversationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

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

  // Buka/segarkan window percakapan: selama ~10 dtk berikutnya, ucapan diterima
  // tanpa perlu menyebut "Hai Viona" lagi. Dipanggil saat giliran user diterima
  // dan saat Viona selesai membalas (biar lanjutan mulus).
  const openConversationWindow = useCallback(() => {
    conversationOpenRef.current = true
    setConversationActive(true)
    if (conversationTimerRef.current) clearTimeout(conversationTimerRef.current)
    conversationTimerRef.current = setTimeout(() => {
      conversationOpenRef.current = false
      setConversationActive(false)
    }, CONVERSATION_WINDOW_MS)
  }, [])

  const closeConversationWindow = useCallback(() => {
    if (conversationTimerRef.current) {
      clearTimeout(conversationTimerRef.current)
      conversationTimerRef.current = null
    }
    conversationOpenRef.current = false
    setConversationActive(false)
  }, [])

  const clearBubbleTimers = useCallback(() => {
    if (bubbleShowTimerRef.current) {
      clearTimeout(bubbleShowTimerRef.current)
      bubbleShowTimerRef.current = null
    }
    if (bubbleHideTimerRef.current) {
      clearTimeout(bubbleHideTimerRef.current)
      bubbleHideTimerRef.current = null
    }
  }, [])

  // Menampilkan bubble berikutnya dari antrean, lalu menjadwalkan diri sendiri
  // lagi setelah BUBBLE_VISIBLE_MS — sehingga beberapa bubble (mis. formula +
  // mnemonic) tampil bergantian satu per satu, bukan sekaligus menumpuk.
  const showNextBubble = useCallback(() => {
    const queue = bubbleQueueRef.current
    if (queue.length === 0) {
      setActiveBubble(null)
      setActiveImage(null)
      return
    }
    const [next, ...rest] = queue
    bubbleQueueRef.current = rest
    setActiveBubble(next)
    bubbleHideTimerRef.current = setTimeout(showNextBubble, BUBBLE_VISIBLE_MS)
  }, [])

  // Bubble gambar (chart) tampil bersamaan dengan bubble teks pertama, dan
  // tetap terlihat selama antrean bubble teks masih berjalan — hilang bareng
  // saat antrean habis (lihat showNextBubble) atau saat konteks berubah.
  const scheduleBubbles = useCallback((bubbles: InsightBubble[], image: string | null = null) => {
    clearBubbleTimers()
    setActiveBubble(null)
    setActiveImage(null)
    bubbleQueueRef.current = []
    if (!bubbles || bubbles.length === 0) return
    bubbleQueueRef.current = bubbles
    bubbleShowTimerRef.current = setTimeout(() => {
      setActiveImage(image)
      showNextBubble()
    }, BUBBLE_SHOW_DELAY_MS)
  }, [clearBubbleTimers, showNextBubble])

  // Konteks materi berubah (user pindah artikel/halaman) -> bubble yang sedang
  // tampil tidak relevan lagi, sembunyikan segera.
  useEffect(() => {
    clearBubbleTimers()
    setActiveBubble(null)
    setActiveImage(null)
    bubbleQueueRef.current = []
    pendingBubblesRef.current = []
    pendingImageRef.current = null
  }, [lmsContext, clearBubbleTimers])

  const stopListening = useCallback(() => {
    clearSilenceTimer()
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    finalTranscriptRef.current = ""
    liveTextRef.current = ""
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
    liveTextRef.current = ""

    const scheduleEndOfTurn = () => {
      clearSilenceTimer()
      silenceTimerRef.current = setTimeout(() => {
        let text = liveTextRef.current.trim()
        finalTranscriptRef.current = ""
        liveTextRef.current = ""
        setInterimText("")

        const needsWakeWord = stateRef.current.isMuted
        let finalQuery = text

        if (needsWakeWord) {
          const { matched, query } = matchWakeWord(text)
          if (!matched) {
             // Ignored if wake word not found
             return
          }
          finalQuery = query
          // Wake word matched! Unmute the mic automatically
          setIsMuted(false)
          stateRef.current.isMuted = false
        }

        const cleaned = cleanTranscript(finalQuery)
        if (cleaned.length >= MIN_CHARS && !stateRef.current.isBotSpeaking && !stateRef.current.isProcessing) {
          openConversationWindow() // segarkan window
          recognition.stop()
          processUserInputRef.current(cleaned)
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
      liveTextRef.current = live
      setInterimText(live)

      if (live) scheduleEndOfTurn()
    }

    recognition.onend = () => {
      if (stateRef.current.isConnected && !stateRef.current.isBotSpeaking && !stateRef.current.isProcessing) {
        setAgentState("idle")
        setTimeout(() => startListening(), 300)
      }
    }

    recognition.onerror = (event: Event) => {
      clearSilenceTimer()
      const err = (event as unknown as { error?: string }).error ?? "unknown"
      
      if (err === "network" || err === "service-not-allowed") {
        setSttError("Koneksi STT terputus, mencoba ulang...")
      } else if (err === "not-allowed") {
        setSttError("Izin mikrofon ditolak.")
      } else if (err === "audio-capture") {
        setSttError("Mikrofon tidak terdeteksi.")
      }

      if (stateRef.current.isConnected && !stateRef.current.isBotSpeaking && !stateRef.current.isProcessing && err !== "not-allowed") {
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

  // Akhir satu giliran bicara — dulu diduplikasi di onend & onerror. `seq` menjaga
  // agar callback ucapan LAMA (yang keburu di-barge-in atau diganti) tidak
  // menyalakan ulang listening setelah ucapan baru dimulai.
  const finishSpeaking = useCallback((seq: number) => {
    if (seq !== speakSeqRef.current) return
    setAgentState("idle")
    utteranceRef.current = null
    // Viona selesai membalas: jika sedang dalam percakapan, segarkan window agar
    // user bisa lanjut tanpa memanggil "Hai Viona" lagi.
    if (conversationOpenRef.current) openConversationWindow()
    // Selalu nyalakan STT setelah bicara, meskipun muted (karena muted = mode wake word)
    if (stateRef.current.isConnected) {
      startListening()
    }
  }, [startListening, openConversationWindow])

  // Hentikan audio Cartesia yang sedang berjalan + batalkan request yang masih terbang.
  const teardownAudio = useCallback(() => {
    ttsAbortRef.current?.abort()
    ttsAbortRef.current = null
    const audio = audioRef.current
    if (audio) {
      audio.onended = null
      audio.onerror = null
      audio.pause()
      audioRef.current = null
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current)
      audioUrlRef.current = null
    }
  }, [])

  // Fallback: Web Speech API browser. Dipakai kalau Cartesia gagal (kunci belum
  // diset, jaringan mati, autoplay diblokir) supaya Viona tetap bersuara.
  // Di sini normalizeForSpeech() dipakai klien; untuk Cartesia normalisasi
  // dikerjakan server via normalize_for_tts().
  const speakWithWebSpeech = useCallback((text: string, seq: number) => {
    if (!synthRef.current) return
    
    setIsMuted(true)
    stateRef.current.isMuted = true
    
    const utterance = new SpeechSynthesisUtterance(normalizeForSpeech(text))
    utteranceRef.current = utterance // Prevent garbage collection
    utterance.lang = "id-ID"
    utterance.rate = 0.9
    utterance.pitch = 1
    utterance.onstart = () => setAgentState("speaking")
    utterance.onend = () => {
      finishSpeaking(seq)
    }
    utterance.onerror = () => {
      finishSpeaking(seq)
    }
    synthRef.current.speak(utterance)
  }, [finishSpeaking])

  // TTS utama: Cartesia (via server), kualitas & suara Indonesia konsisten di semua
  // browser — tidak lagi bergantung SpeechSynthesis yang hanya baik di Chrome/Edge.
  const speak = useCallback((text: string) => {
    setIsMuted(true)
    stateRef.current.isMuted = true
    stopListening()

    // Batalkan ucapan sebelumnya, apa pun jalurnya.
    const seq = ++speakSeqRef.current
    teardownAudio()
    synthRef.current?.cancel()

    void (async () => {
      const controller = new AbortController()
      ttsAbortRef.current = controller
      try {
        const blob = await fetchTTS(text, controller.signal)
        if (seq !== speakSeqRef.current) return // keburu di-barge-in saat sintesis

        const url = URL.createObjectURL(blob)
        audioUrlRef.current = url
        const audio = new Audio(url)
        audioRef.current = audio
        audio.onended = () => {
          finishSpeaking(seq)
        }
        audio.onerror = () => {
          finishSpeaking(seq)
        }
        setAgentState("speaking")
        await audio.play()
      } catch {
        if (seq !== speakSeqRef.current) return // dibatalkan, bukan kegagalan nyata
        teardownAudio()
        speakWithWebSpeech(text, seq)
      }
    })()
  }, [stopListening, teardownAudio, finishSpeaking, speakWithWebSpeech])

  // Barge-in: potong ucapan Viona di tengah. Menaikkan seq membatalkan callback
  // ucapan berjalan, lalu siklus dilanjutkan eksplisit — audio yang di-pause tidak
  // memicu onended sendiri (berbeda dari synth.cancel() yang memicu onend).
  const stopSpeaking = useCallback(() => {
    // Kalau Viona tidak sedang bicara, ini harus no-op: melanjutkan siklus di sini
    // akan memaksa state "thinking" jadi "idle" dan menyalakan listening di tengah
    // proses. (Web Speech dulu aman sendiri: cancel() tanpa ucapan tak memicu onend.)
    const wasSpeaking = stateRef.current.isBotSpeaking
    const seq = ++speakSeqRef.current
    teardownAudio()
    synthRef.current?.cancel()
    if (wasSpeaking) finishSpeaking(seq)
  }, [teardownAudio, finishSpeaking])

  const processUserInput = useCallback(async (userText: string) => {
    if (stateRef.current.isProcessing) return

    openConversationWindow() // sedang berdialog -> lanjutan boleh tanpa wake-word
    stopListening()
    setAgentState("thinking")

    // Ambil beberapa giliran terakhir SEBELUM menambahkan pesan user yang baru,
    // supaya backend punya konteks percakapan untuk pertanyaan lanjutan yang
    // merujuk jawaban sebelumnya tanpa mengulang kata kunci topiknya.
    const history = messagesRef.current.slice(-HISTORY_TURNS).map(m => ({
      role: m.role,
      content: m.content,
    }))

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userText,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])

    let response = ""
    pendingBubblesRef.current = []
    pendingImageRef.current = null
    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText, material_id: "matematika", version: "v1", lms_context: lmsContext, syllabus, history, is_quiz: isQuiz, course_title: courseTitle, session_id: sessionId }),
      })
      if (res.ok) {
        const data = await res.json()
        response = data.response
        pendingBubblesRef.current = data.bubbles ?? []
        pendingImageRef.current = data.image ?? null
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
      image: pendingImageRef.current,
    }
    setMessages(prev => [...prev, assistantMessage])
    // Dijadwalkan langsung begitu jawaban tiba — TIDAK menunggu event 'onend' dari
    // speechSynthesis, karena beberapa browser tidak pernah memicu onend/onerror
    // kalau tidak ada output audio (mis. speaker mati), sehingga bubble bisa macet
    // selamanya kalau ditaruh di situ.
    scheduleBubbles(pendingBubblesRef.current, pendingImageRef.current)
    speak(response)
  }, [speak, stopListening, lmsContext, syllabus, scheduleBubbles, isQuiz, courseTitle, sessionId, openConversationWindow])

  // Keep the ref pointed at the latest processUserInput (current lmsContext) so
  // startListening's frozen closure always dispatches through up-to-date logic.
  useEffect(() => {
    processUserInputRef.current = processUserInput
  }, [processUserInput])

  // Explicit text submission (from chat UI)
  const sendText = useCallback((text: string) => {
    if (text.trim() && stateRef.current.isConnected) {
      processUserInput(text.trim())
    }
  }, [processUserInput])

  const connect = useCallback(async (options?: { startMuted?: boolean, autoGreeting?: boolean }) => {
    const startMuted = options?.startMuted ?? false
    const autoGreeting = options?.autoGreeting ?? false

    try {
      micStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    } catch {
      // Permission denied, but we can still connect and speak back
    }

    setConnectionState("connected")

    // Restore transkrip session dari Redis (bila ada) supaya tidak hilang saat
    // buka ulang / refresh / maximize. GET 404 = session baru -> mulai dengan sapaan.
    let restored: Message[] = []
    if (sessionId) {
      try {
        const res = await fetch(`/sessions/${encodeURIComponent(sessionId)}/history`)
        if (res.ok) {
          const data = await res.json()
          restored = (data.history || []).map(
            (h: any, i: number): Message => ({
              id: `h-${i}`,
              role: h.role === "user" ? "user" : "assistant",
              content: h.text || h.content || "",
              timestamp: new Date(),
              image: h.image || null,
            }),
          )
        }
      } catch {
        // gagal ambil history -> lanjut sebagai session baru
      }
    }

    if (restored.length > 0) {
      setMessages(restored) // lanjut session lama, tanpa menambahkan sapaan ke history
    } else {
      const welcomeMessage: Message = {
        id: "welcome",
        role: "assistant",
        content: "Ada yang bisa saya bantu hari ini?",
        timestamp: new Date(),
      }
      setMessages([welcomeMessage])
      
      if (autoGreeting) {
        setTimeout(() => speak("Ada yang bisa saya bantu hari ini?"), 500)
        
        // Jaring pengaman: kalau sintesis/pemutaran salam gagal tanpa memicu callback
        // selesai, pastikan state isBotSpeaking tidak tersangkut.
        setTimeout(() => {
          if (stateRef.current.isConnected && !stateRef.current.isBotSpeaking) {
            // Jangan auto-unmute. Biarkan mute tetap true sesuai dengan mode manual.
          }
        }, 4500)
      }
    }

    setIsMuted(startMuted)
    stateRef.current.isMuted = startMuted
    setTimeout(() => startListening(), 100)
  }, [speak, sessionId, startListening])
  
  const playGreeting = useCallback(() => {
    speak("Ada yang bisa saya bantu hari ini?")
  }, [speak])

  const disconnect = useCallback(() => {
    if (synthRef.current) synthRef.current.cancel()
    // Naikkan seq + hentikan audio Cartesia, kalau tidak suara Viona lanjut
    // terputar setelah popup ditutup.
    speakSeqRef.current++
    teardownAudio()
    closeConversationWindow()
    stopListening()
    micStreamRef.current?.getTracks().forEach(t => t.stop())
    micStreamRef.current = null
    clearBubbleTimers()
    pendingBubblesRef.current = []
    pendingImageRef.current = null
    bubbleQueueRef.current = []

    setConnectionState("disconnected")
    setAgentState("idle")
    setMessages([])
    setActiveBubble(null)
    setActiveImage(null)
  }, [stopListening, clearBubbleTimers, closeConversationWindow, teardownAudio])

  const toggleMute = useCallback(() => {
    const newMuted = !isMuted
    setIsMuted(newMuted)
    stateRef.current.isMuted = newMuted
    
    // Kita TIDAK menghentikan STT saat mute, karena Mute = Mode Wake Word.
    if (!newMuted && connectionState === "connected" && agentState !== "speaking" && !recognitionRef.current) {
      startListening()
    }
  }, [isMuted, connectionState, agentState, startListening])

  return {
    connectionState,
    agentState,
    messages,
    interimText,
    sttError,
    isMuted,
    activeBubble,
    activeImage,
    conversationActive,
    connect,
    disconnect,
    sendText,
    toggleMute,
    stopSpeaking,
    playGreeting,
    micStream: micStreamRef.current
  }
}
