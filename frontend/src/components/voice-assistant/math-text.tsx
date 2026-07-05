"use client"

import { useMemo } from "react"
import katex from "katex"

/**
 * Renders a chat string that may contain LaTeX math, converting delimited
 * segments to KaTeX and leaving prose untouched. Supported delimiters:
 *   - display: `$$...$$` and `\[...\]`
 *   - inline:  `$...$`   and `\(...\)`
 *
 * Non-math text keeps its whitespace (the parent uses `whitespace-pre-wrap`).
 * Malformed math never throws — KaTeX falls back to showing the raw source.
 */

type Segment =
  | { type: "text"; value: string }
  | { type: "math"; value: string; display: boolean }

// group 1: $$…$$ (display) · 2: \[…\] (display) · 3: $…$ (inline) · 4: \(…\) (inline)
const MATH_RE =
  /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\$([^$\n]+?)\$|\\\(([\s\S]+?)\\\)/g

function tokenize(input: string): Segment[] {
  const segments: Segment[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  MATH_RE.lastIndex = 0
  while ((match = MATH_RE.exec(input)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: "text", value: input.slice(lastIndex, match.index) })
    }
    const [display1, display2, inline1, inline2] = [
      match[1],
      match[2],
      match[3],
      match[4],
    ]
    const value = (display1 ?? display2 ?? inline1 ?? inline2 ?? "").trim()
    const display = display1 !== undefined || display2 !== undefined
    segments.push({ type: "math", value, display })
    lastIndex = MATH_RE.lastIndex
  }

  if (lastIndex < input.length) {
    segments.push({ type: "text", value: input.slice(lastIndex) })
  }
  return segments
}

function renderMath(tex: string, display: boolean): string {
  try {
    return katex.renderToString(tex, {
      displayMode: display,
      throwOnError: false,
      output: "html",
    })
  } catch {
    return tex
  }
}

export function MathText({ content }: { content: string }) {
  const segments = useMemo(() => tokenize(content), [content])

  return (
    <span className="whitespace-pre-wrap">
      {segments.map((seg, i) =>
        seg.type === "text" ? (
          <span key={i}>{seg.value}</span>
        ) : (
          <span
            key={i}
            className={seg.display ? "block my-1 overflow-x-auto" : ""}
            dangerouslySetInnerHTML={{ __html: renderMath(seg.value, seg.display) }}
          />
        ),
      )}
    </span>
  )
}
