"use client"

import React from "react"
import { motion, AnimatePresence } from "motion/react"

interface FloatingButtonProps {
  onClick: () => void
  isOpen: boolean
}

export function FloatingButton({ onClick, isOpen }: FloatingButtonProps) {
  return (
    <AnimatePresence>
      {!isOpen && (
        <motion.button
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0, opacity: 0 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onClick}
          className="fixed bottom-6 right-6 z-50 flex items-center justify-center w-16 h-16 rounded-full bg-white dark:bg-slate-900 shadow-xl border border-purple-200 dark:border-purple-800 focus:outline-none"
        >
          <div className="relative">
            {/* Mascot Image */}
            <img 
              src="/dashboard/viona-logo-new.png" 
              alt="Viona AI" 
              className="w-12 h-12 object-contain"
            />
            {/* Active Indicator */}
            <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-white rounded-full"></span>
          </div>
        </motion.button>
      )}
    </AnimatePresence>
  )
}
