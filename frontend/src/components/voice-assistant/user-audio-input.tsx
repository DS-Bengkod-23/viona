"use client"

import { useEffect, useRef } from "react"
import { Mic, MicOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface UserAudioInputProps {
  isRecording: boolean
  isMuted: boolean
  isConnected: boolean
  onToggleMute: () => void
  micStream?: MediaStream | null
  className?: string
}

const BAR_COUNT = 28

const C = {
  top:  "216,180,254",
  mid:  "139,92,246",
  base: "109,40,217",
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t
}

function FrequencyBars({ isActive, micStream }: { isActive: boolean; micStream?: MediaStream | null }) {
  const wrapperRef = useRef<HTMLDivElement>(null)
  const canvasRef  = useRef<HTMLCanvasElement>(null)
  const rafRef     = useRef<number>(0)
  const analyserRef  = useRef<AnalyserNode | null>(null)
  const dataArrayRef = useRef<Uint8Array | null>(null)
  const smoothedRef  = useRef<number[]>(Array(BAR_COUNT).fill(0))

  // Keep canvas pixel dimensions in sync with layout size
  useEffect(() => {
    const wrapper = wrapperRef.current
    const canvas  = canvasRef.current
    if (!wrapper || !canvas) return
    const sync = () => {
      const dpr = window.devicePixelRatio || 1
      canvas.width  = wrapper.clientWidth  * dpr
      canvas.height = wrapper.clientHeight * dpr
    }
    sync()
    const ro = new ResizeObserver(sync)
    ro.observe(wrapper)
    return () => ro.disconnect()
  }, [])

  const drawFrame = (values: number[], alpha = 1) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    const W = canvas.width
    const H = canvas.height
    const dpr = window.devicePixelRatio || 1
    const GAP  = 3 * dpr
    const barW = (W - GAP * (BAR_COUNT - 1)) / BAR_COUNT
    const MIN_H = 4 * dpr

    ctx.clearRect(0, 0, W, H)
    values.forEach((v, i) => {
      const barH = Math.max(MIN_H, v * H)
      const x = i * (barW + GAP)
      const y = H - barH
      const grad = ctx.createLinearGradient(0, y, 0, H)
      grad.addColorStop(0,   `rgba(${C.top},${alpha})`)
      grad.addColorStop(0.4, `rgba(${C.mid},${alpha})`)
      grad.addColorStop(1,   `rgba(${C.base},${alpha})`)
      ctx.fillStyle = grad
      ctx.beginPath()
      ctx.roundRect(x, y, barW, barH, 2 * dpr)
      ctx.fill()
    })
  }

  // Idle: gentle pulse animation
  useEffect(() => {
    if (isActive) return
    cancelAnimationFrame(rafRef.current)
    let tick = 0
    const idle = () => {
      rafRef.current = requestAnimationFrame(idle)
      tick++
      const s = smoothedRef.current
      for (let i = 0; i < BAR_COUNT; i++) {
        const target = 0.03 + 0.015 * Math.sin((tick + i * 3) / 30)
        s[i] = lerp(s[i], target, 0.08)
      }
      drawFrame(s, 0.3)
    }
    idle()
    return () => cancelAnimationFrame(rafRef.current)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive])

  // Active: build AudioContext from the provided micStream
  useEffect(() => {
    if (!isActive || !micStream) return

    cancelAnimationFrame(rafRef.current)

    const audioCtx = new AudioContext()
    const source   = audioCtx.createMediaStreamSource(micStream)
    const analyser = audioCtx.createAnalyser()
    analyser.fftSize = 1024
    analyser.smoothingTimeConstant = 0.8
    source.connect(analyser)
    analyserRef.current  = analyser
    dataArrayRef.current = new Uint8Array(analyser.frequencyBinCount)

    const render = () => {
      rafRef.current = requestAnimationFrame(render)
      const data = dataArrayRef.current!
      analyser.getByteFrequencyData(data)

      const maxBin = Math.floor((4000 / (audioCtx.sampleRate / 2)) * analyser.frequencyBinCount)
      const step   = maxBin / BAR_COUNT
      const s      = smoothedRef.current

      for (let i = 0; i < BAR_COUNT; i++) {
        let sum = 0
        const from = Math.floor(i * step)
        const to   = Math.min(Math.floor((i + 1) * step), data.length - 1)
        for (let j = from; j <= to; j++) sum += data[j]
        const raw = (sum / (to - from + 1)) / 255
        s[i] = lerp(s[i], raw, 0.15)
      }

      drawFrame(s)
    }
    render()

    return () => {
      cancelAnimationFrame(rafRef.current)
      audioCtx.close()
      analyserRef.current  = null
      dataArrayRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive, micStream])

  return (
    <div ref={wrapperRef} className="w-full h-24">
      <canvas ref={canvasRef} className="w-full h-full" />
    </div>
  )
}

export function UserAudioInput({
  isRecording,
  isMuted,
  isConnected,
  onToggleMute,
  micStream,
  className,
}: UserAudioInputProps) {
  return (
    <div className={cn("space-y-3", className)}>
      <div className="px-2">
        <FrequencyBars isActive={isConnected && !isMuted} micStream={micStream} />
      </div>

      <div className="flex items-center justify-center">
        <Button
          variant={isMuted ? "destructive" : "secondary"}
          size="sm"
          className={cn(
            "rounded-full gap-2",
            !isMuted && isRecording && "bg-primary/15 text-primary hover:bg-primary/25"
          )}
          onClick={onToggleMute}
          aria-label={isMuted ? "Aktifkan mikrofon" : "Nonaktifkan mikrofon"}
        >
          {isMuted ? (
            <><MicOff className="w-4 h-4" /><span>Muted</span></>
          ) : (
            <><Mic className="w-4 h-4" /><span>Mikrofon Aktif</span></>
          )}
        </Button>
      </div>
    </div>
  )
}
