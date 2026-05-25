"use client"

import { useState } from "react"
import { ThumbsUp, ThumbsDown, Star, Send } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface FeedbackWidgetProps {
  className?: string
}

export function FeedbackWidget({ className }: FeedbackWidgetProps) {
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null)
  const [rating, setRating] = useState<number>(0)
  const [hoverRating, setHoverRating] = useState<number>(0)
  const [suggestion, setSuggestion] = useState("")
  const [submitted, setSubmitted] = useState(false)

  const handleThumbsFeedback = (type: "up" | "down") => {
    setFeedback(type)
  }

  const handleStarClick = (star: number) => {
    setRating(star)
  }

  const handleSubmitFeedback = () => {
    // Log feedback data (in production, send to API)
    console.log({
      feedback,
      rating,
      suggestion,
      timestamp: new Date().toISOString(),
    })
    
    setSubmitted(true)
    setTimeout(() => {
      setSubmitted(false)
      setFeedback(null)
      setRating(0)
      setSuggestion("")
    }, 2000)
  }

  const hasFeedback = feedback !== null || rating > 0

  return (
    <Card className={cn("py-4 gap-2", className)}>
      <CardHeader className="pb-0">
        <CardTitle className="text-sm font-medium">Penilaian Layanan</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {submitted ? (
          <div className="py-4 text-center">
            <p className="text-sm text-green-600 dark:text-green-400 font-medium">
              Terima kasih atas masukan Anda!
            </p>
          </div>
        ) : (
          <>
            {/* Feedback Question */}
            <div className="space-y-3">
              <p className="text-sm">Apakah pelayanan Viona membantu Anda?</p>
              <div className="flex items-center gap-3">
                <Button
                  variant={feedback === "up" ? "default" : "outline"}
                  size="sm"
                  className="flex-1 gap-2"
                  onClick={() => handleThumbsFeedback("up")}
                >
                  <ThumbsUp className="w-4 h-4" />
                  Ya
                </Button>
                <Button
                  variant={feedback === "down" ? "destructive" : "outline"}
                  size="sm"
                  className="flex-1 gap-2"
                  onClick={() => handleThumbsFeedback("down")}
                >
                  <ThumbsDown className="w-4 h-4" />
                  Tidak
                </Button>
              </div>
            </div>

            {/* Rating Section */}
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Atau beri rating</p>
              <div className="flex items-center justify-center gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    className="p-1 transition-transform hover:scale-110"
                    onClick={() => handleStarClick(star)}
                    onMouseEnter={() => setHoverRating(star)}
                    onMouseLeave={() => setHoverRating(0)}
                    aria-label={`Rating ${star} dari 5`}
                  >
                    <Star
                      className={cn(
                        "w-6 h-6 transition-colors",
                        (hoverRating || rating) >= star
                          ? "fill-yellow-400 text-yellow-400"
                          : "text-muted-foreground/40"
                      )}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Kritik dan Saran Section */}
            <div className="space-y-2 border-t border-border pt-4">
              <p className="text-sm font-medium">Kritik dan Saran</p>
              <textarea
                value={suggestion}
                onChange={(e) => setSuggestion(e.target.value)}
                placeholder="Sampaikan ulasan Anda"
                className="w-full min-h-22.5 px-3 py-2 text-sm rounded-md border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              />
            </div>

            {/* Submit Button */}
            <Button
              size="sm"
              className="w-full gap-2"
              onClick={handleSubmitFeedback}
              disabled={!hasFeedback && !suggestion.trim()}
            >
              <Send className="w-4 h-4" />
              Kirim Feedback
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}
