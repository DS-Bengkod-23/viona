"use client"

import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { MathText } from "./math-text"
import { CHART_ICONS, CHART_LABELS } from "@/components/popup/chart-icons"

interface ChatMessageProps {
  role: "user" | "assistant"
  content: string
  timestamp?: Date
  image?: string | null
}

export function ChatMessage({ role, content, timestamp, image }: ChatMessageProps) {
  const isUser = role === "user"
  const [formattedTime, setFormattedTime] = useState<string>("")
  const Icon = image ? CHART_ICONS[image] : null

  // Format timestamp on client only to avoid hydration mismatch
  useEffect(() => {
    if (timestamp) {
      const hours = timestamp.getHours().toString().padStart(2, "0")
      const minutes = timestamp.getMinutes().toString().padStart(2, "0")
      setFormattedTime(`${hours}:${minutes}`)
    }
  }, [timestamp])

  return (
    <div className={cn("flex w-full mb-4", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed",
          isUser
            ? "bg-primary text-primary-foreground rounded-br-md shadow-sm"
            : "bg-white dark:bg-white/10 border border-white/80 dark:border-white/15 text-foreground rounded-bl-md shadow-sm"
        )}
      >
        <p
          className={cn(
            "text-[10px] font-semibold tracking-widest uppercase mb-1.5",
            isUser ? "text-right text-primary-foreground/60" : "text-left text-primary"
          )}
        >
          {isUser ? "Anda" : "Viona"}
        </p>

        <MathText content={content} />

        {Icon && (
          <div className="mt-3 w-56 max-w-full rounded-xl border border-violet-200 dark:border-violet-800 bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
            <div className="px-3 pt-3">
              <Icon />
            </div>
            <div className="px-3 py-2 text-xs font-semibold text-violet-700 dark:text-violet-300 border-t border-violet-100 dark:border-violet-900">
              {CHART_LABELS[image as string]}
            </div>
          </div>
        )}

        {formattedTime && (
          <p className={cn("text-[10px] mt-2 opacity-50", isUser ? "text-right" : "text-left")}>
            {formattedTime}
          </p>
        )}
      </div>
    </div>
  )
}
