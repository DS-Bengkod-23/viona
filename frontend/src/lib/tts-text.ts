/**
 * Frontend TTS text normaliser (spoken Indonesian).
 *
 * The demo speaks assistant replies with the browser `SpeechSynthesis` API,
 * which would otherwise read LaTeX/math literally ("dollar … backslash times").
 * This mirrors the backend `normalize_for_tts` intent: turn math notation into
 * spoken Indonesian and strip markdown, so Viona sounds natural.
 */
export function normalizeForSpeech(input: string): string {
  let s = input

  // \frac{a}{b} -> "a per b"
  s = s.replace(/\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}/g, "$1 per $2")
  // \sqrt{x} / \sqrt x -> "akar x"
  s = s.replace(/\\sqrt\s*\{([^{}]+)\}/g, "akar $1")
  s = s.replace(/\\sqrt\s*/g, "akar ")

  // named LaTeX operators -> words
  s = s
    .replace(/\\times|\\cdot/g, " kali ")
    .replace(/\\div/g, " bagi ")
    .replace(/\\approx/g, " kira-kira ")
    .replace(/\\neq/g, " tidak sama dengan ")
    .replace(/\\leq/g, " kurang dari atau sama dengan ")
    .replace(/\\geq/g, " lebih dari atau sama dengan ")
    .replace(/\\pm/g, " plus minus ")
    .replace(/\\pi/g, " pi ")

  // Unicode pecahan umum -> kata (mis. hasil model yang menulis "½")
  s = s
    .replace(/½/g, " setengah ")
    .replace(/⅓/g, " sepertiga ")
    .replace(/⅔/g, " dua per tiga ")
    .replace(/¼/g, " seperempat ")
    .replace(/¾/g, " tiga per empat ")

  // Unicode simbol matematika/umum -> kata terucap
  s = s
    .replace(/×/g, " kali ")
    .replace(/÷/g, " bagi ")
    .replace(/√/g, " akar ")
    .replace(/π/g, " pi ")
    .replace(/≈/g, " kira-kira ")
    .replace(/≠/g, " tidak sama dengan ")
    .replace(/≤/g, " kurang dari atau sama dengan ")
    .replace(/≥/g, " lebih dari atau sama dengan ")
    .replace(/±/g, " plus minus ")
    .replace(/²/g, " kuadrat ")
    .replace(/³/g, " pangkat tiga ")
    .replace(/°/g, " derajat ")
    .replace(/%/g, " persen ")

  // strip math delimiters $$ $ \( \) \[ \]
  s = s.replace(/\$\$?|\\\(|\\\)|\\\[|\\\]/g, " ")

  // superscript power: x^{2} / x^2 -> "x pangkat 2"
  s = s.replace(/\^\s*\{([^{}]+)\}/g, " pangkat $1 ")
  s = s.replace(/\^\s*([0-9a-zA-Z]+)/g, " pangkat $1 ")

  // digit-flanked operators
  s = s.replace(/(?<=\d)\s*[x×*]\s*(?=\d)/g, " kali ")
  s = s.replace(/(?<=\d)\s*\/\s*(?=\d)/g, " bagi ")
  s = s.replace(/(?<=\d)\s*-\s*(?=\d)/g, " kurang ")
  s = s.replace(/(?<=\w)\s*=\s*(?=\w)/g, " sama dengan ")
  s = s.replace(/(?<=\w)\s*\+\s*(?=\w)/g, " tambah ")

  // drop any remaining LaTeX commands and braces
  s = s.replace(/\\[a-zA-Z]+/g, " ").replace(/[{}]/g, " ")

  // strip markdown emphasis / headings / code ticks
  s = s.replace(/[*_`#~|>]/g, " ")

  // collapse whitespace
  return s.replace(/\s+/g, " ").trim()
}
