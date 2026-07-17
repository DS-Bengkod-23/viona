"use client"

import React from "react"
import { motion, AnimatePresence } from "motion/react"
import { Lightbulb, Brain, Calculator, AlertTriangle } from "lucide-react"
import type { InsightBubble as InsightBubbleData } from "@/hooks/useNativeVoiceConnection"

const VARIANTS = {
  insight: {
    icon: Lightbulb,
    bg: "bg-amber-50 dark:bg-amber-950/60",
    border: "border-amber-200 dark:border-amber-800",
    text: "text-amber-900 dark:text-amber-200",
    iconBg: "bg-amber-400 text-amber-950",
  },
  mnemonic: {
    icon: Brain,
    bg: "bg-emerald-50 dark:bg-emerald-950/60",
    border: "border-emerald-200 dark:border-emerald-800",
    text: "text-emerald-900 dark:text-emerald-200",
    iconBg: "bg-emerald-400 text-emerald-950",
  },
  formula: {
    icon: Calculator,
    bg: "bg-blue-50 dark:bg-blue-950/60",
    border: "border-blue-200 dark:border-blue-800",
    text: "text-blue-900 dark:text-blue-200",
    iconBg: "bg-blue-400 text-blue-950",
  },
  warning: {
    icon: AlertTriangle,
    bg: "bg-rose-50 dark:bg-rose-950/60",
    border: "border-rose-200 dark:border-rose-800",
    text: "text-rose-900 dark:text-rose-200",
    iconBg: "bg-rose-400 text-rose-950",
  },
} as const

interface InsightBubbleProps {
  bubble: InsightBubbleData | null
}

export function InsightBubbleCard({ bubble }: InsightBubbleProps) {
  return (
    <AnimatePresence>
      {bubble && (
        <motion.div
          key={`${bubble.type}-${bubble.text}`}
          initial={{ opacity: 0, y: 12, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8, scale: 0.9 }}
          transition={{ type: "spring", damping: 20, stiffness: 260 }}
          className="absolute -top-3 right-4 -translate-y-full z-10 max-w-60"
        >
          <div
            className={`flex items-start gap-2 px-3 py-2.5 rounded-2xl rounded-br-sm border shadow-lg ${VARIANTS[bubble.type].bg} ${VARIANTS[bubble.type].border}`}
          >
            <span className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${VARIANTS[bubble.type].iconBg}`}>
              {React.createElement(VARIANTS[bubble.type].icon, { className: "w-3.5 h-3.5" })}
            </span>
            <span className={`text-xs font-semibold leading-snug ${VARIANTS[bubble.type].text}`}>
              {bubble.text}
            </span>
          </div>
          {/* Tail pointing down toward the widget */}
          <div
            className={`absolute -bottom-1.5 right-5 w-3 h-3 rotate-45 border-b border-r ${VARIANTS[bubble.type].bg} ${VARIANTS[bubble.type].border}`}
          />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
