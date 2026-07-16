"use client"

import React from "react"

// Ilustrasi mini bergaya konsisten (palet violet #7C3AED + amber #F59E0B untuk
// aksen kedua, tervalidasi lolos cek CVD/kontras) — dekoratif untuk bubble
// gambar, bukan chart data presisi.

const AXIS = "#C4B5FD"
const VIOLET = "#7C3AED"
const VIOLET_DARK = "#4C1D95"
const AMBER = "#F59E0B"

export function ScatterplotIcon() {
  return (
    <svg viewBox="0 0 160 120" className="w-full h-full">
      <line x1="16" y1="8" x2="16" y2="104" stroke={AXIS} strokeWidth="1.5" />
      <line x1="16" y1="104" x2="150" y2="104" stroke={AXIS} strokeWidth="1.5" />
      {/* Tanda skala sumbu */}
      {[20, 45, 70, 95].map((y, i) => (
        <text key={`y-${i}`} x="12" y={y + 3} textAnchor="end" fontSize="6.5" fill={VIOLET_DARK}>
          {10 - i * 2}
        </text>
      ))}
      {[30, 65, 100, 135].map((x, i) => (
        <text key={`x-${i}`} x={x} y="113" textAnchor="middle" fontSize="6.5" fill={VIOLET_DARK}>
          {10 + i * 15}
        </text>
      ))}
      {[
        [32, 88], [40, 78], [45, 92], [55, 70], [60, 82], [68, 60],
        [75, 68], [82, 50], [90, 58], [98, 42], [105, 48], [112, 34],
        [120, 40], [128, 26], [135, 32],
      ].map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="3.5" fill={VIOLET} opacity="0.85" />
      ))}
      <line x1="28" y1="94" x2="140" y2="24" stroke={VIOLET_DARK} strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  )
}

export function HistogramIcon() {
  const heights = [24, 48, 72, 60, 40, 28, 16]
  const counts = [3, 6, 9, 7, 5, 3, 2]
  const w = 16
  const gap = 4
  return (
    <svg viewBox="0 0 160 120" className="w-full h-full">
      <line x1="10" y1="104" x2="150" y2="104" stroke={AXIS} strokeWidth="1.5" />
      {[0, 3, 6, 9].map((v, i) => (
        <text key={i} x="8" y={104 - i * 24 + 3} textAnchor="end" fontSize="6.5" fill={VIOLET_DARK}>
          {v}
        </text>
      ))}
      {heights.map((h, i) => (
        <g key={i}>
          <rect
            x={16 + i * (w + gap)}
            y={104 - h}
            width={w}
            height={h}
            rx="2"
            fill={VIOLET}
            opacity={0.55 + (i % 3) * 0.15}
          />
          <text x={16 + i * (w + gap) + w / 2} y={104 - h - 4} textAnchor="middle" fontSize="6.5" fill={VIOLET_DARK}>
            {counts[i]}
          </text>
        </g>
      ))}
    </svg>
  )
}

export function BoxplotIcon() {
  return (
    <svg viewBox="0 0 160 120" className="w-full h-full">
      <line x1="16" y1="8" x2="16" y2="104" stroke={AXIS} strokeWidth="1.5" />
      <line x1="16" y1="104" x2="150" y2="104" stroke={AXIS} strokeWidth="1.5" />
      {[0, 3, 6, 9].map((v, i) => (
        <text key={i} x="12" y={104 - i * 30 + 3} textAnchor="end" fontSize="6.5" fill={VIOLET_DARK}>
          {v}
        </text>
      ))}
      {/* Whisker atas & bawah */}
      <line x1="80" y1="18" x2="80" y2="42" stroke={VIOLET_DARK} strokeWidth="2" />
      <line x1="80" y1="80" x2="80" y2="96" stroke={VIOLET_DARK} strokeWidth="2" />
      <line x1="62" y1="18" x2="98" y2="18" stroke={VIOLET_DARK} strokeWidth="2" />
      <line x1="62" y1="96" x2="98" y2="96" stroke={VIOLET_DARK} strokeWidth="2" />
      {/* Kotak IQR */}
      <rect x="52" y="42" width="56" height="38" rx="3" fill={VIOLET} opacity="0.7" stroke={VIOLET_DARK} strokeWidth="2" />
      <line x1="52" y1="60" x2="108" y2="60" stroke="white" strokeWidth="2.5" />
      <text x="112" y="63" fontSize="7" fontWeight="700" fill={VIOLET_DARK}>Med: 5.2</text>
      {/* Outlier */}
      <circle cx="80" cy="10" r="3" fill={AMBER} />
    </svg>
  )
}

export function HeatmapIcon() {
  const ramp = ["#EDE9FE", "#C4B5FD", "#A78BFA", "#8B5CF6", "#7C3AED", "#6D28D9", "#5B21B6", "#4C1D95"]
  // Nilai korelasi (0.00–1.00) sejajar index dengan `ramp` — dipakai untuk label
  // angka di tiap kotak, supaya user bisa lihat besarannya, bukan cuma warnanya.
  const values = [0.02, 0.16, 0.31, 0.44, 0.50, 0.57, 0.69, 1.00]
  const grid = [
    [7, 5, 4, 2], [5, 7, 3, 1], [4, 3, 7, 6], [2, 1, 6, 7],
  ]
  const cell = 26
  const ox = 24
  const oy = 6
  return (
    <svg viewBox="0 0 160 120" className="w-full h-full">
      {grid.map((row, r) =>
        row.map((v, c) => (
          <g key={`${r}-${c}`}>
            <rect
              x={ox + c * cell}
              y={oy + r * cell}
              width={cell - 2}
              height={cell - 2}
              rx="2"
              fill={ramp[v]}
            />
            <text
              x={ox + c * cell + (cell - 2) / 2}
              y={oy + r * cell + (cell - 2) / 2 + 3.5}
              textAnchor="middle"
              fontSize="8"
              fontWeight="700"
              fill={v >= 4 ? "white" : VIOLET_DARK}
            >
              {values[v].toFixed(2)}
            </text>
          </g>
        ))
      )}
    </svg>
  )
}

export function ConfusionMatrixIcon() {
  const cellW = 56
  const cellH = 40
  const ox = 20
  const oy = 12
  const cells = [
    { label: "TP", count: 13, x: ox, y: oy },
    { label: "FP", count: 2, x: ox + cellW + 4, y: oy },
    { label: "FN", count: 3, x: ox, y: oy + cellH + 4 },
    { label: "TN", count: 9, x: ox + cellW + 4, y: oy + cellH + 4 },
  ]
  return (
    <svg viewBox="0 0 160 120" className="w-full h-full">
      {cells.map((c) => (
        <g key={c.label}>
          <rect
            x={c.x}
            y={c.y}
            width={cellW}
            height={cellH}
            rx="3"
            fill={c.label === "TP" || c.label === "TN" ? VIOLET : AMBER}
            opacity={c.label === "TP" || c.label === "TN" ? 0.85 : 0.55}
          />
          <text x={c.x + cellW / 2} y={c.y + cellH / 2 - 2} textAnchor="middle" fontSize="11" fontWeight="700" fill="white">
            {c.label}
          </text>
          <text x={c.x + cellW / 2} y={c.y + cellH / 2 + 13} textAnchor="middle" fontSize="12" fontWeight="700" fill="white">
            {c.count}
          </text>
        </g>
      ))}
    </svg>
  )
}

export function ClassificationMetricsIcon() {
  const rows = [
    { label: "Acc", formula: "(TP+TN)/Total", violet: true },
    { label: "Prec", formula: "TP/(TP+FP)", violet: false },
    { label: "Recall", formula: "TP/(TP+FN)", violet: true },
    { label: "F1", formula: "2PR/(P+R)", violet: false },
  ]
  const rowH = 27
  const oy = 6
  return (
    <svg viewBox="0 0 160 120" className="w-full h-full">
      {rows.map((r, i) => (
        <g key={r.label}>
          <rect
            x={8}
            y={oy + i * rowH}
            width={44}
            height={20}
            rx="4"
            fill={r.violet ? VIOLET : AMBER}
            opacity={r.violet ? 0.85 : 0.55}
          />
          <text x={30} y={oy + i * rowH + 14} textAnchor="middle" fontSize="9.5" fontWeight="700" fill="white">
            {r.label}
          </text>
          <text x={58} y={oy + i * rowH + 14} fontSize="9.5" fill={VIOLET_DARK} fontFamily="monospace">
            {r.formula}
          </text>
        </g>
      ))}
    </svg>
  )
}

export function ImbalanceIcon() {
  // Donut 78% / 22% — mengikuti proporsi kelas pada dataset Heart Failure di kursus ini.
  const r = 42
  const cx = 80
  const cy = 60
  const circumference = 2 * Math.PI * r
  const majority = 0.78
  return (
    <svg viewBox="0 0 160 120" className="w-full h-full">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={AMBER} strokeWidth="16" opacity="0.6" />
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke={VIOLET}
        strokeWidth="16"
        strokeDasharray={`${circumference * majority} ${circumference}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
      />
      <text x={cx} y={cy + 6} textAnchor="middle" fontSize="18" fontWeight="700" fill={VIOLET_DARK}>78%</text>
    </svg>
  )
}

export function RocCurveIcon() {
  return (
    <svg viewBox="0 0 160 120" className="w-full h-full">
      <line x1="16" y1="8" x2="16" y2="104" stroke={AXIS} strokeWidth="1.5" />
      <line x1="16" y1="104" x2="150" y2="104" stroke={AXIS} strokeWidth="1.5" />
      {["1.0", "0.5", "0.0"].map((v, i) => (
        <text key={`y-${i}`} x="12" y={10 + i * 47} textAnchor="end" fontSize="6.5" fill={VIOLET_DARK}>{v}</text>
      ))}
      {["0.0", "0.5", "1.0"].map((v, i) => (
        <text key={`x-${i}`} x={16 + i * 67} y="113" textAnchor="middle" fontSize="6.5" fill={VIOLET_DARK}>{v}</text>
      ))}
      <line x1="16" y1="104" x2="150" y2="8" stroke="#94A3B8" strokeWidth="1.5" strokeDasharray="4 4" />
      <path
        d="M 16 104 C 30 40, 45 18, 70 14 S 120 8, 150 8"
        fill="none"
        stroke={VIOLET}
        strokeWidth="3"
        strokeLinecap="round"
      />
      <text x="95" y="55" fontSize="9" fontWeight="700" fill={VIOLET_DARK}>AUC = 0.93</text>
    </svg>
  )
}

export const CHART_ICONS: Record<string, React.FC> = {
  scatterplot: ScatterplotIcon,
  histogram: HistogramIcon,
  boxplot: BoxplotIcon,
  heatmap: HeatmapIcon,
  confusion_matrix: ConfusionMatrixIcon,
  imbalance: ImbalanceIcon,
  roc_curve: RocCurveIcon,
  classification_metrics: ClassificationMetricsIcon,
}

export const CHART_LABELS: Record<string, string> = {
  scatterplot: "Scatterplot + Regresi",
  histogram: "Histogram",
  boxplot: "Boxplot",
  heatmap: "Heatmap Korelasi",
  confusion_matrix: "Confusion Matrix",
  imbalance: "Imbalance Kelas",
  roc_curve: "Kurva ROC",
  classification_metrics: "Akurasi, Precision, Recall, F1",
}
