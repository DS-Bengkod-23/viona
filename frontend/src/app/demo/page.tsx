"use client"

import dynamic from "next/dynamic"
import Link from "next/link"

const VoiceAssistant = dynamic(
  () => import("@/components/voice-assistant").then((m) => m.VoiceAssistant),
  { ssr: false }
)

export default function DemoPage() {
  return (
    <>
      <div className="fixed top-2 left-2 z-50">
        <Link
          href="/"
          className="text-xs px-3 py-1.5 rounded-full bg-amber-500/20 text-amber-200 border border-amber-500/40 hover:bg-amber-500/30 transition-colors"
        >
          ← Mode demo (tanpa backend)
        </Link>
      </div>
      <VoiceAssistant />
    </>
  )
}
