"use client"

import React, { useState, useRef, useEffect } from "react"
import { Send, ChevronDown, ChevronUp } from "lucide-react"
import { Message } from "@/hooks/useNativeVoiceConnection"

interface TranscriptModeProps {
  voiceConnection: any
}

export function TranscriptMode({ voiceConnection }: TranscriptModeProps) {
  const { messages, sendText, connectionState } = voiceConnection
  const [inputText, setInputText] = useState("")
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (inputText.trim() && connectionState === "connected") {
      sendText(inputText)
      setInputText("")
    }
  }

  return (
    <div className="flex flex-col h-full bg-slate-50 dark:bg-slate-900/50">
      {/* Chat History Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 opacity-70">
            <img src="/dashboard/viona-logo-new.png" alt="Viona" className="w-12 h-12 grayscale opacity-50 mb-2" />
            <p className="text-sm">Belum ada percakapan</p>
          </div>
        ) : (
          messages.map((msg: Message) => (
            <ChatMessage 
              key={msg.id} 
              message={msg.content} 
              isUser={msg.role === "user"} 
              timestamp={new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-3 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 flex gap-2 items-center">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Ketik pesan kamu di sini..."
          disabled={connectionState !== "connected"}
          className="flex-1 py-2 px-4 bg-slate-100 dark:bg-slate-800 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!inputText.trim() || connectionState !== "connected"}
          className="w-10 h-10 rounded-full bg-purple-600 hover:bg-purple-700 disabled:bg-slate-300 dark:disabled:bg-slate-700 flex items-center justify-center text-white transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  )
}

function ChatMessage({ message, isUser, timestamp }: { message: string, isUser: boolean, timestamp: string }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = message.length > 150

  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      <span className="text-[10px] text-slate-400 mb-1 px-2">
        {isUser ? "Anda" : "Viona"} • {timestamp}
      </span>
      <div className={`flex gap-2 max-w-[85%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        {/* Avatar for Viona */}
        {!isUser && (
          <div className="w-8 h-8 rounded-full bg-purple-100 flex-shrink-0 flex items-center justify-center border border-purple-200">
            <img src="/dashboard/viona-logo-new.png" alt="Viona" className="w-6 h-6 object-contain" />
          </div>
        )}
        
        {/* Message Bubble */}
        <div className={`relative px-4 py-3 rounded-2xl text-sm shadow-sm ${
          isUser 
            ? "bg-purple-600 text-white rounded-tr-sm" 
            : "bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 border border-slate-200 dark:border-slate-700 rounded-tl-sm"
        }`}>
          <p className="whitespace-pre-wrap leading-relaxed">
            {isLong && !expanded ? `${message.substring(0, 150)}...` : message}
          </p>
          
          {/* Expandable UI for long texts (only for agent) */}
          {!isUser && isLong && (
            <button 
              onClick={() => setExpanded(!expanded)}
              className="mt-2 flex items-center gap-1 text-xs text-purple-600 dark:text-purple-400 hover:underline font-medium"
            >
              {expanded ? (
               <>Tutup penjelasan <ChevronUp className="w-3 h-3" /></>
              ) : (
                <>Lihat penjelasan lengkap <ChevronDown className="w-3 h-3" /></>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
