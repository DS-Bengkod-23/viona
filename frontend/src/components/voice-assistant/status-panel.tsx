"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface StatusPanelProps {
  userStatus: "idle" | "speaking" | "listening"
  vionaStatus: "idle" | "thinking" | "speaking" | "ready"
  className?: string
}

const userStatusLabels: Record<string, string> = {
  idle: "Siap berbicara",
  speaking: "Sedang berbicara...",
  listening: "Mendengarkan Viona...",
}

const vionaStatusLabels: Record<string, string> = {
  idle: "Siap membantu",
  thinking: "Sedang berpikir...",
  speaking: "Sedang berbicara...",
  ready: "Siap membantu",
}

export function StatusPanel({ userStatus, vionaStatus, className }: StatusPanelProps) {
  return (
    <Card className={cn("py-4 gap-2", className)}>
      <CardHeader className="pb-0">
        <CardTitle className="text-sm font-medium">Status Aktivitas</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-0.5">
          <p className="text-xs text-muted-foreground">Status Anda</p>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "w-2 h-2 rounded-full shrink-0",
                userStatus === "speaking" && "bg-green-500 animate-pulse",
                userStatus === "listening" && "bg-blue-500 animate-pulse",
                userStatus === "idle" && "bg-muted-foreground/50"
              )}
            />
            <span className="text-sm font-medium">{userStatusLabels[userStatus]}</span>
          </div>
        </div>

        <div className="space-y-0.5">
          <p className="text-xs text-muted-foreground">Status Viona</p>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "w-2 h-2 rounded-full shrink-0",
                vionaStatus === "speaking" && "bg-primary animate-pulse",
                vionaStatus === "thinking" && "bg-yellow-500 animate-pulse",
                (vionaStatus === "idle" || vionaStatus === "ready") && "bg-green-500"
              )}
            />
            <span className="text-sm font-medium">{vionaStatusLabels[vionaStatus]}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
