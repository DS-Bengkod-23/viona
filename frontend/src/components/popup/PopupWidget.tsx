"use client"

import React, { useState, useEffect } from "react"
import { motion, AnimatePresence } from "motion/react"
import { MessageSquare, Mic, Maximize2, X } from "lucide-react"
import { useRouter } from "next/navigation"
import { useNativeVoiceConnection } from "@/hooks/useNativeVoiceConnection"

import { FloatingButton } from "./FloatingButton"
import { VoiceMode } from "./VoiceMode"
import { TranscriptMode } from "./TranscriptMode"
import { InsightBubbleCard } from "./InsightBubble"
import { ImageBubbleCard } from "./ImageBubble"

export function PopupWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [mode, setMode] = useState<"voice" | "transcript">("voice")
  const [lmsContext, setLmsContext] = useState<string>("")
  const [quotedText, setQuotedText] = useState<string>("")
  const router = useRouter()
  
  const voiceConnection = useNativeVoiceConnection(lmsContext)
  const { connectionState, connect, disconnect, activeBubble, activeImage } = voiceConnection

  // Connect when popup opens
  useEffect(() => {
    if (isOpen && connectionState === "disconnected") {
      connect()
    }
  }, [isOpen, connectionState, connect])

  // Send resize message to parent iframe if embedded
  useEffect(() => {
    if (typeof window !== "undefined" && window.parent !== window) {
      window.parent.postMessage({ type: 'viona-resize', isOpen }, '*')
    }
  }, [isOpen])

  // Listen for lms-context and viona-quote from parent iframe
  useEffect(() => {
    if (typeof window === "undefined") return
    
    const handleMessage = (event: MessageEvent) => {
      if (event.data && event.data.type === 'viona-context') {
        setLmsContext(event.data.text || "")
      } else if (event.data && event.data.type === 'viona-quote') {
        setQuotedText(event.data.text || "")
        setQuotedText(event.data.text || "")
        setIsOpen(true) // Open widget automatically
        setMode("transcript") // Switch to transcript mode
      }
    }
    
    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [])

  const handleMaximize = () => {
    // Navigate to dashboard in a new tab since we are in an iframe
    setIsOpen(false)
    window.open(window.location.origin + "/dashboard", "_blank")
  }

  const handleClose = () => {
    setIsOpen(false)
    disconnect()
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
            {/* Header */}
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
                    <><MessageSquare className="w-3.5 h-3.5" /> Switch to Transcript</>
                  ) : (
                    <><Mic className="w-3.5 h-3.5" /> Switch to Voice</>
                  )}
                </button>
                <button onClick={handleMaximize} className="p-1.5 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors" title="Maximize">
                  <Maximize2 className="w-4 h-4" />
                </button>
                <button onClick={handleClose} className="p-1.5 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors" title="Close">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 relative overflow-hidden flex flex-col">
              {connectionState === "connected" ? (
                mode === "voice" ? (
                  <VoiceMode voiceConnection={voiceConnection} />
                ) : (
                  <TranscriptMode 
                    voiceConnection={voiceConnection} 
                    quotedText={quotedText}
                    setQuotedText={setQuotedText}
                  />
                )
              ) : (
                <div className="flex-1 flex items-center justify-center p-6 text-center">
                  <p className="text-sm text-slate-500">Mempersiapkan asisten...</p>
                </div>
              )}
            </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
