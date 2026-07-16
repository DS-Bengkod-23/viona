"use client"

import { useEffect } from "react"
import { PopupWidget } from "@/components/popup/PopupWidget"

export default function WidgetPage() {
  // This page is rendered inside a transparent iframe on the LMS. globals.css sets
  // `body { bg-background }` (dark ≈ black), which would paint the whole iframe area
  // as a black box behind the floating button. Force transparency for this route only.
  useEffect(() => {
    const html = document.documentElement
    const body = document.body
    const prev = {
      htmlBg: html.style.background,
      bodyBg: body.style.background,
      colorScheme: html.style.colorScheme,
    }
    html.style.background = "transparent"
    body.style.background = "transparent"
    html.style.colorScheme = "normal" // avoid the UA dark canvas bleeding through
    return () => {
      html.style.background = prev.htmlBg
      body.style.background = prev.bodyBg
      html.style.colorScheme = prev.colorScheme
    }
  }, [])

  return (
    <div className="w-full h-full bg-transparent overflow-hidden">
      <PopupWidget />
    </div>
  )
}
