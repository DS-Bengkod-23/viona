"use client"

import { useEffect, useRef, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface SessionTimerProps {
  isConnected: boolean
  className?: string
}

export function SessionTimer({ isConnected, className }: SessionTimerProps) {
  const [seconds, setSeconds] = useState(0)
  const [lastDuration, setLastDuration] = useState<number | null>(null)
  const [sessionCount, setSessionCount] = useState(0)
  const secondsRef = useRef(0)

  useEffect(() => {
    if (isConnected) {
      secondsRef.current = 0
      setSeconds(0)
      const interval = setInterval(() => {
        secondsRef.current++
        setSeconds(secondsRef.current)
      }, 1000)
      return () => clearInterval(interval)
    } else if (secondsRef.current > 0) {
      setLastDuration(secondsRef.current)
      setSessionCount((c) => c + 1)
      secondsRef.current = 0
      setSeconds(0)
    }
  }, [isConnected])

  const formatTime = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60)
    const secs = totalSeconds % 60
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
  }

  return (
    <Card className={cn("py-4 gap-2", className)}>
      <CardHeader className="pb-0">
        <CardTitle className="text-sm font-medium">Informasi Sesi</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="space-y-0.5">
            <p className="text-xs text-muted-foreground">Durasi Obrolan</p>
            {isConnected ? (
              <p className="text-2xl font-mono font-semibold tabular-nums">
                {formatTime(seconds)}
              </p>
            ) : (
              <p className="text-sm font-medium text-muted-foreground">Belum terhubung</p>
            )}
          </div>

          {lastDuration !== null && (
            <div className="space-y-0.5 pt-2 border-t border-border">
              <p className="text-xs text-muted-foreground">Sesi Sebelumnya</p>
              <p className="text-sm font-mono font-medium tabular-nums">
                {formatTime(lastDuration)}
              </p>
              <p className="text-xs text-muted-foreground">
                Sesi ke-{sessionCount}
              </p>
            </div>
          )}

          {lastDuration === null && !isConnected && (
            <div className="space-y-0.5 pt-2 border-t border-border">
              <p className="text-xs text-muted-foreground">Total Sesi</p>
              <p className="text-sm font-medium text-muted-foreground">Belum ada sesi</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
