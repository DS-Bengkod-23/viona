"use client"

import { motion, AnimatePresence } from "motion/react"
import { CHART_ICONS, CHART_LABELS } from "./chart-icons"

interface ImageBubbleProps {
  image: string | null
}

export function ImageBubbleCard({ image }: ImageBubbleProps) {
  const Icon = image ? CHART_ICONS[image] : null

  return (
    <AnimatePresence>
      {Icon && (
        <motion.div
          key={image}
          initial={{ opacity: 0, x: 12, scale: 0.9 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          exit={{ opacity: 0, x: 8, scale: 0.9 }}
          transition={{ type: "spring", damping: 20, stiffness: 260 }}
          className="absolute top-24 -left-56 z-10 w-52 max-w-[70vw]"
        >
          <div className="rounded-2xl rounded-bl-sm border border-violet-200 dark:border-violet-800 bg-white dark:bg-slate-900 shadow-lg overflow-hidden">
            <div className="px-3 pt-3 h-44">
              <Icon />
            </div>
            <div className="px-3 py-2 text-base font-semibold text-violet-700 dark:text-violet-300 border-t border-violet-100 dark:border-violet-900">
              {CHART_LABELS[image as string]}
            </div>
          </div>
          {/* Tail pointing right toward the widget */}
          <div className="absolute -bottom-1.5 left-5 w-3 h-3 rotate-45 border-t border-r border-violet-200 dark:border-violet-800 bg-white dark:bg-slate-900" />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
