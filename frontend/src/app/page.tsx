"use client"

import dynamic from "next/dynamic"

const VoiceAssistant = dynamic(
  () => import("@/components/voice-assistant").then((m) => m.VoiceAssistant),
  { ssr: false }
)

export default function Home() {
  return <VoiceAssistant />
}
