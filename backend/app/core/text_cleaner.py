"""
Indonesian text cleaner for STT output preprocessing.

This module provides utilities to clean and normalize text from:
1. STT (Speech-to-Text) output - fixes common transcription errors
2. LLM output - prepares text for TTS synthesis

Common issues handled:
- Whitespace normalization
- Indonesian slang normalization
- URL and mention handling
- Emoji removal (optional)
- Punctuation cleanup
- Number formatting
- LaTeX / math notation -> spoken Indonesian (so TTS doesn't read raw symbols)
- Common transcription error fixes for Indonesian
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern


@dataclass
class CleanerConfig:
    """Configuration for text cleaning."""
    remove_emoji: bool = True
    remove_urls: bool = True
    remove_mentions: bool = True
    normalize_slang: bool = True
    normalize_numbers: bool = True
    fix_stt_errors: bool = True
    max_length: int = 1000


# Indonesian slang dictionary (common informal → formal)
# NOTE: keys must be unique. Duplicate keys are silently overwritten by Python
# (the last one wins), which previously caused "sm" to resolve to "sampai"
# instead of "sama". Keep this list deduplicated.
_INDONESIAN_SLANG_MAP: dict[str, str] = {
    # Negations
    "gak": "tidak",
    "ga": "tidak",
    "nggak": "tidak",
    "enggak": "tidak",
    "nggaknya": "tidak",
    "g": "tidak",
    "tdk": "tidak",
    "gk": "tidak",
    "bkn": "bukan",
    # Time
    "td": "tadi",
    "kmrn": "kemarin",
    "bsk": "besok",
    "skr": "sekarang",
    "skrg": "sekarang",
    "skrng": "sekarang",
    # Intensifiers
    "bgt": "banget",
    "bangett": "banget",
    "banged": "banget",
    "sgt": "sangat",
    # Common abbreviations
    "sdh": "sudah",
    "udah": "sudah",
    "blm": "belum",
    "jd": "jadi",
    "jdi": "jadi",
    "sm": "sama",
    "smpe": "sampai",
    "dr": "dari",
    "tp": "tapi",
    "tpi": "tapi",
    "dl": "dulu",
    "lg": "lagi",
    "lgi": "lagi",
    "kalo": "kalau",
    "kl": "kalau",
    "utk": "untuk",
    "yg": "yang",
    "dgn": "dengan",
    "dg": "dengan",
    "bs": "bisa",
    "bsa": "bisa",
    "trs": "terus",
    "trus": "terus",
    "hrs": "harus",
    "msh": "masih",
    "mn": "mana",
    "kmn": "kemana",
    "dmna": "kemana",
    "spt": "seperti",
    "sprti": "seperti",
    # Pronouns
    "km": "kamu",
    "aq": "aku",
    "gw": "aku",
    "sy": "saya",
    "ane": "saya",
    "gua": "saya",
    "lu": "kamu",
    "loe": "kamu",
    # Nouns
    "org": "orang",
    "orng": "orang",
    "byk": "banyak",
    "bnyk": "banyak",
    "brg": "barang",
    "brp": "berapa",
    # Wishes
    "smg": "semoga",
    "smoga": "semoga",
    # Months
    "feb": "februari",
    "mar": "maret",
    "apr": "april",
    "jun": "juni",
    "jul": "juli",
    "aug": "agustus",
    "sep": "september",
    "okt": "oktober",
    "nov": "november",
    "des": "desember",
    # Greetings
    "pagi2": "pagi",
    "mlm2": "malam",
    "sore2": "sore",
}

# Regex patterns
_URL_PATTERN: Pattern[str] = re.compile(
    r'https?://\S+|www\.\S+',
    re.IGNORECASE
)
_MENTION_PATTERN: Pattern[str] = re.compile(r'@\w+')
_EMAIL_PATTERN: Pattern[str] = re.compile(r'\S+@\S+\.\S+')
_MULTIPLE_SPACES: Pattern[str] = re.compile(r'\s+')
_MULTIPLE_PUNCTUATION: Pattern[str] = re.compile(r'([.!?])\1+')
_LEADING_PUNCTUATION: Pattern[str] = re.compile(r'^[\s.,;:!?]+')
_TRAILING_PUNCTUATION: Pattern[str] = re.compile(r'[\s.,;:!?]+$')

# Emoji ranges (common emojis)
_EMOJI_PATTERN: Pattern[str] = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE
)

# ---------------------------------------------------------------------------
# LaTeX / math -> spoken Indonesian
#
# The LLM sometimes answers with math notation (e.g. "$\frac{1}{2}$" or
# "x^2 + 3"). If passed straight to TTS it is read literally ("dollar frac
# satu...", "x caret 2"), which sounds broken. We translate the notation into
# words the TTS can pronounce naturally in Indonesian.
# ---------------------------------------------------------------------------

# Backslash LaTeX commands -> Indonesian words. These are unambiguous so they
# are safe to translate anywhere in the text. Keys are regex strings for the
# command name; we sort by length (desc) at apply time so e.g. "\leq" wins
# over "\le".
_LATEX_WORDS: dict[str, str] = {
    # operators / relations
    r"\\times": " kali ",
    r"\\cdot": " kali ",
    r"\\div": " dibagi ",
    r"\\pm": " plus minus ",
    r"\\mp": " minus plus ",
    r"\\leq": " kurang dari atau sama dengan ",
    r"\\le": " kurang dari atau sama dengan ",
    r"\\geq": " lebih dari atau sama dengan ",
    r"\\ge": " lebih dari atau sama dengan ",
    r"\\neq": " tidak sama dengan ",
    r"\\ne": " tidak sama dengan ",
    r"\\approx": " kira-kira sama dengan ",
    r"\\equiv": " identik dengan ",
    r"\\propto": " sebanding dengan ",
    # symbols / operators
    r"\\infty": " tak hingga ",
    r"\\sum": " sigma ",
    r"\\prod": " hasil kali ",
    r"\\int": " integral ",
    r"\\partial": " parsial ",
    r"\\nabla": " nabla ",
    r"\\angle": " sudut ",
    r"\\circ": " derajat ",
    r"\\degree": " derajat ",
    # logic / set notation
    r"\\rightarrow": " menuju ",
    r"\\Rightarrow": " maka ",
    r"\\Leftrightarrow": " jika dan hanya jika ",
    r"\\to": " menuju ",
    r"\\forall": " untuk setiap ",
    r"\\exists": " terdapat ",
    r"\\notin": " bukan anggota dari ",
    r"\\in": " anggota dari ",
    r"\\subset": " himpunan bagian dari ",
    r"\\cup": " gabungan ",
    r"\\cap": " irisan ",
    # functions
    r"\\log": " log ",
    r"\\ln": " ln ",
    r"\\sin": " sin ",
    r"\\cos": " cos ",
    r"\\tan": " tan ",
    # ellipsis / spacing
    r"\\cdots": " dan seterusnya ",
    r"\\ldots": " dan seterusnya ",
    r"\\dots": " dan seterusnya ",
    r"\\quad": " ",
    r"\\left": " ",
    r"\\right": " ",
    r"\\%": " persen ",
    r"\\,": " ",
    r"\\;": " ",
    r"\\:": " ",
    r"\\!": "",
    # greek letters
    r"\\alpha": " alfa ",
    r"\\beta": " beta ",
    r"\\gamma": " gama ",
    r"\\Gamma": " gama ",
    r"\\delta": " delta ",
    r"\\Delta": " delta ",
    r"\\varepsilon": " epsilon ",
    r"\\epsilon": " epsilon ",
    r"\\zeta": " zeta ",
    r"\\eta": " eta ",
    r"\\theta": " teta ",
    r"\\Theta": " teta ",
    r"\\lambda": " lambda ",
    r"\\Lambda": " lambda ",
    r"\\mu": " mu ",
    r"\\nu": " nu ",
    r"\\xi": " ksi ",
    r"\\pi": " pi ",
    r"\\Pi": " pi ",
    r"\\rho": " ro ",
    r"\\varphi": " fi ",
    r"\\phi": " fi ",
    r"\\Phi": " fi ",
    r"\\sigma": " sigma ",
    r"\\Sigma": " sigma ",
    r"\\tau": " tau ",
    r"\\chi": " chi ",
    r"\\psi": " psi ",
    r"\\Psi": " psi ",
    r"\\omega": " omega ",
    r"\\Omega": " omega ",
}

# ASCII operators -> words. These are AMBIGUOUS in normal prose (e.g. "-" in
# "anak-anak", "/" in dates), so they are only translated inside detected math
# segments, never on free text.
# NOTE: "-" is handled separately (digit-flanked) so it doesn't clobber the
# hyphen inside expanded words like "kira-kira" (from \approx).
_ASCII_MATH_OPERATORS: list[tuple[str, str]] = [
    ("=", " sama dengan "),
    ("+", " tambah "),
    ("*", " kali "),
    ("/", " bagi "),
    ("<", " kurang dari "),
    (">", " lebih dari "),
]

# Math delimiters: $$...$$, \[...\], \(...\), $...$
_MATH_BLOCK_PATTERNS: list[Pattern[str]] = [
    re.compile(r"\$\$(.+?)\$\$", re.DOTALL),
    re.compile(r"\\\[(.+?)\\\]", re.DOTALL),
    re.compile(r"\\\((.+?)\\\)", re.DOTALL),
    re.compile(r"\$(.+?)\$", re.DOTALL),
]

_FRAC_PATTERN: Pattern[str] = re.compile(
    r"\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}"
)


def _convert_math(content: str, *, full: bool) -> str:
    """Translate LaTeX notation in ``content`` into spoken Indonesian.

    ``full=True`` also translates ASCII operators (= + - * / < >) and
    super/subscripts; use it only on confirmed math segments. ``full=False``
    only translates unambiguous backslash commands, safe for free text.
    """
    s = content

    # \frac{a}{b} -> "a per b" (inner-out to handle nesting)
    while True:
        new = _FRAC_PATTERN.sub(r" \1 per \2 ", s)
        if new == s:
            break
        s = new

    # \sqrt[n]{x} -> "akar pangkat n dari x"; \sqrt{x} -> "akar x"
    s = re.sub(r"\\sqrt\s*\[([^\]]*)\]\s*\{([^{}]*)\}", r" akar pangkat \1 dari \2 ", s)
    s = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r" akar \1 ", s)

    # Backslash commands (longest first so prefixes don't shadow longer names).
    for cmd in sorted(_LATEX_WORDS, key=len, reverse=True):
        word = _LATEX_WORDS[cmd]
        if cmd[-1].isalpha():
            # Don't match e.g. "\pi" inside "\pizza".
            s = re.sub(cmd + r"(?![a-zA-Z])", word, s)
        else:
            s = re.sub(cmd, word, s)

    if full:
        # Superscripts / subscripts.
        s = re.sub(r"\^\{([^{}]+)\}", r" pangkat \1 ", s)
        s = re.sub(r"\^(-?\d+|[A-Za-z])", r" pangkat \1 ", s)
        s = re.sub(r"_\{([^{}]+)\}", r" indeks \1 ", s)
        s = re.sub(r"_(-?\d+|[A-Za-z])", r" indeks \1 ", s)
        # ASCII operators. "-" is digit-flanked so it never touches the hyphen
        # in expanded words (e.g. "kira-kira" from \approx).
        s = re.sub(r"(?<=\d)\s*-\s*(?=\d)", " kurang ", s)
        for op, word in _ASCII_MATH_OPERATORS:
            s = s.replace(op, word)

    # Drop any remaining (unknown) commands and structural characters.
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = s.replace("{", " ").replace("}", " ").replace("\\", " ")
    if full:
        s = s.replace("$", " ")

    return s


def _latex_to_speech(text: str) -> str:
    r"""Convert LaTeX/math notation to spoken Indonesian, safely.

    Delimited math segments ($$...$$, \[...\], \(...\), $...$) get the full
    translation (operators included). Bare backslash commands elsewhere get the
    safe translation only, so ordinary prose is left untouched.
    """
    if "\\" not in text and "$" not in text and "^" not in text and "_{" not in text:
        return text

    def _repl(match: re.Match[str]) -> str:
        return " " + _convert_math(match.group(1), full=True) + " "

    for pattern in _MATH_BLOCK_PATTERNS:
        text = pattern.sub(_repl, text)

    # Bare commands (\frac, \sqrt, greek, ...) outside any delimiter.
    text = _convert_math(text, full=False)
    return text


# Unicode superscript digits (e.g. x²) -> spoken exponent.
_SUPERSCRIPT: dict[str, str] = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
}
_SUPERSCRIPT_RE: Pattern[str] = re.compile(
    r"([⁰¹²³⁴-⁹]+)"
)


def _plain_math_to_speech(text: str) -> str:
    """Convert inline (non-LaTeX) math notation to spoken Indonesian.

    Many LLM answers contain math in plain text (``x^2``, ``3 x 4``, ``10/2``)
    with no ``$``/``\\(`` delimiters, so the LaTeX pass leaves them untouched and
    the TTS reads them wrong ("x" -> "eks", "/" and "^" silent).

    Safety rule: unambiguous symbols (``^ × ÷ · √ ² ³``) are converted anywhere,
    but ASCII operators that also occur in normal prose (``- / x``) are only
    converted when flanked by digits — so "anak-anak", "dan/atau", dates, and
    variable names stay intact. Run this AFTER ``_format_numbers`` so real dates
    (10/06/2026) are already neutralised.
    """
    s = text

    # Strip markdown list bullets at line start ("- ", "* ", "• ") so a leading
    # dash is never later mistaken for a minus sign ("kurang").
    s = re.sub(r"(?m)^[ \t]*[-*•]\s+", "", s)

    # Unicode superscripts: x² -> "x pangkat 2"
    s = _SUPERSCRIPT_RE.sub(
        lambda m: " pangkat " + "".join(_SUPERSCRIPT[c] for c in m.group(1)) + " ",
        s,
    )

    # Caret exponent (unambiguous): a^{...}, a^2, a^n
    s = re.sub(r"\^\s*\{([^{}]+)\}", r" pangkat \1 ", s)
    s = re.sub(r"\^\s*(-?\d+(?:[.,]\d+)?|[A-Za-z]+)", r" pangkat \1 ", s)

    # Square root symbol: √(x), √16, √x
    s = re.sub(r"√\s*\(([^()]+)\)", r" akar \1 ", s)
    s = re.sub(r"√\s*([A-Za-z0-9.,]+)", r" akar \1 ", s)

    # Unambiguous symbol operators (never used in Indonesian prose).
    for sym, word in (
        ("×", " kali "), ("✕", " kali "), ("∙", " kali "),
        ("·", " kali "), ("÷", " bagi "),
        ("≠", " tidak sama dengan "),
        ("≤", " kurang dari atau sama dengan "),
        ("≥", " lebih dari atau sama dengan "),
        ("≈", " kira-kira sama dengan "),
        ("±", " plus minus "), ("∞", " tak hingga "),
        ("π", " pi "),
    ):
        s = s.replace(sym, word)

    # Asterisk multiplication between operands: 2*3, a*b
    s = re.sub(r"(?<=[\w)])\s*\*\s*(?=[\w(])", " kali ", s)

    # 'x' as multiplication — needs a DIGIT next to it (separated only by
    # spaces/punctuation), so "3 x 4", "3x4" and "2. x 2" convert, while a
    # variable x in prose ("nilai x adalah") stays untouched.
    s = re.sub(r"(?<=\d)[ \t.,:]*[xX][ \t.,:]*(?=\d)", " kali ", s)

    # Division slash — only between digits, no newline crossing.
    s = re.sub(r"(?<=\d)[ \t]*/[ \t]*(?=\d)", " bagi ", s)

    # Subtraction — digits on BOTH sides, no newline crossing, so "anak-anak"
    # and markdown list dashes ("2\n- 3") survive.
    s = re.sub(r"(?<=\d)[ \t]*-[ \t]*(?=\d)", " kurang ", s)

    # +, =, <, > — flanked by word chars / digits.
    s = re.sub(r"(?<=\w)\s*\+\s*(?=\w)", " tambah ", s)
    s = re.sub(r"(?<=\w)\s*=\s*(?=\w)", " sama dengan ", s)
    s = re.sub(r"(?<=\d)\s*<\s*(?=\d)", " kurang dari ", s)
    s = re.sub(r"(?<=\d)\s*>\s*(?=\d)", " lebih dari ", s)

    # Decimal comma (Indonesian) -> spoken "koma": 1,43 -> "1 koma 43".
    # Done here so the later comma-spacing rule doesn't split it into "1, 43".
    s = re.sub(r"(?<=\d),(?=\d)", " koma ", s)

    return s


def clean_stt_output(text: str, config: CleanerConfig | None = None) -> str:
    """Clean STT output for better LLM processing.

    Args:
        text: Raw text from STT
        config: Optional cleaner configuration

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    if config is None:
        config = CleanerConfig()

    result = text.strip()

    # Remove emoji
    if config.remove_emoji:
        result = _EMOJI_PATTERN.sub('', result)

    # Remove URLs
    if config.remove_urls:
        result = _URL_PATTERN.sub('', result)
        result = _EMAIL_PATTERN.sub('', result)

    # Remove mentions
    if config.remove_mentions:
        result = _MENTION_PATTERN.sub('', result)

    # Normalize slang
    if config.normalize_slang:
        result = _normalize_slang(result)

    # Fix common STT errors
    if config.fix_stt_errors:
        result = _fix_stt_errors(result)

    # Normalize whitespace
    result = _MULTIPLE_SPACES.sub(' ', result)
    result = result.strip()

    # Normalize punctuation
    result = _MULTIPLE_PUNCTUATION.sub(r'\1', result)

    # Truncate if too long
    if config.max_length and len(result) > config.max_length:
        result = result[:config.max_length].rsplit(' ', 1)[0] + "..."

    return result


def normalize_for_tts(text: str) -> str:
    """Prepare text for TTS synthesis.

    This makes text more speakable by:
    - Expanding abbreviations
    - Fixing number formatting
    - Removing special characters that might cause issues
    - Normalizing punctuation for natural speech

    Args:
        text: Text to prepare for TTS

    Returns:
        TTS-friendly text
    """
    if not text:
        return ""

    result = text.strip()

    # Convert LaTeX / math notation to spoken Indonesian (before braces and
    # backslashes get stripped further down, which would destroy the notation).
    result = _latex_to_speech(result)

    # Expand common abbreviations
    result = _expand_abbreviations(result)

    # Format numbers (phone/currency/percent/dates) — must run before plain-math
    # so real dates like 10/06/2026 are neutralised before "/" -> "bagi".
    result = _format_numbers(result)

    # Convert inline (non-LaTeX) math: x^2, 3 x 4, 10/2, 5+3, x² ...
    result = _plain_math_to_speech(result)

    # Remove excessive punctuation
    result = _MULTIPLE_PUNCTUATION.sub('.', result)

    # Clean up spacing around punctuation
    result = re.sub(r'\s+([.,!?])', r'\1', result)
    result = re.sub(r'([.,!?])(?=\S)', r'\1 ', result)

    # Remove special characters that might cause TTS issues (incl. leftover
    # markdown emphasis: *, `, #, ~ — math * already consumed above).
    result = re.sub(r'[\[\]{}*`#~|]', '', result)
    result = _EMOJI_PATTERN.sub('', result)

    # Normalize smart/curly quotes to straight quotes
    result = (
        result.replace("“", '"').replace("”", '"')  # “ ”
        .replace("‘", "'").replace("’", "'")  # ‘ ’
    )

    # Collapse extra whitespace (LaTeX expansion can leave double spaces)
    result = _MULTIPLE_SPACES.sub(' ', result).strip()

    # Ensure sentence ends with punctuation
    if result and result[-1] not in '.!?':
        result += '.'

    return result


def _normalize_slang(text: str) -> str:
    """Convert Indonesian slang to formal form."""
    words = text.split()
    normalized = []

    for word in words:
        # Check lowercase version
        lower = word.lower().strip('.,!?')
        if lower in _INDONESIAN_SLANG_MAP:
            # Preserve original case pattern
            if word.isupper():
                normalized.append(_INDONESIAN_SLANG_MAP[lower].upper())
            elif word[0].isupper():
                normalized.append(_INDONESIAN_SLANG_MAP[lower].capitalize())
            else:
                normalized.append(_INDONESIAN_SLANG_MAP[lower])
        else:
            normalized.append(word)

    return ' '.join(normalized)


def _fix_stt_errors(text: str) -> str:
    """Fix common STT transcription errors."""
    # Handle common patterns
    corrections = [
        # Collapse a letter repeated 4+ times (e.g. "haaaalo" -> "haalo").
        # Restricted to letters so numbers like 150000 are left intact.
        (r'([^\W\d_])\1{3,}', r'\1\1'),
        # Fix common number word issues
        (r'\bdua\s+puluh\b', '20'),
        (r'\btiga\s+puluh\b', '30'),
        (r'\bempat\s+puluh\b', '40'),
        (r'\blima\s+puluh\b', '50'),
        (r'\benam\s+puluh\b', '60'),
        (r'\btujuh\s+puluh\b', '70'),
        (r'\bdelapan\s+puluh\b', '80'),
        (r'\bsembilan\s+puluh\b', '90'),
        # Fix common words
        (r'\bkak\b', 'kak'),  # Already correct, but kept for consistency
    ]

    result = text
    for pattern, replacement in corrections:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def _expand_abbreviations(text: str) -> str:
    """Expand common abbreviations for TTS."""
    abbreviations = {
        'ATM': 'A T M',
        'SMS': 'S M S',
        'MMA': 'M M A',
        'API': 'A P I',
        'URL': 'U R L',
        'PDF': 'P D F',
        'VIP': 'V I P',
        'CEO': 'C E O',
        'DNA': 'D N A',
        'FAQ': 'F A Q',
        'OK': 'oke',
        'OKEY': 'oke',
        'OKEE': 'oke',
        'GB': 'giga byte',
        'MB': 'mega byte',
        'KB': 'kilo byte',
        'TB': 'tera byte',
    }

    result = text
    for abbr, expansion in abbreviations.items():
        # Case-insensitive replacement
        result = re.sub(r'\b' + abbr + r'\b', expansion, result, flags=re.IGNORECASE)

    return result


def _format_numbers(text: str) -> str:
    """Format numbers for natural speech."""
    # Format phone numbers
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?(\d{3,4})[-.\s]?(\d{3,4})[-.\s]?(\d{3,4})'
    text = re.sub(phone_pattern, lambda m: ' '.join(g for g in m.groups() if g), text)

    # Format currency (印尼盾)
    text = re.sub(r'Rp\.?\s*(\d+(?:,\d{3})*(?:\.\d+)?)', r'Rp \1', text)

    # Format percentages
    text = re.sub(r'(\d+)%', r'\1 persen', text)

    # Format dates (slash and dash forms) -> spaced, so the plain-math pass
    # does not later turn the separators into "bagi"/"kurang".
    text = re.sub(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', r'\1 \2 \3', text)
    text = re.sub(r'(\d{1,2})-(\d{1,2})-(\d{2,4})', r'\1 \2 \3', text)

    return text


def clean_transcript(text: str) -> str:
    """Convenience function: full cleaning pipeline for transcripts."""
    return normalize_for_tts(clean_stt_output(text))


# Test function
if __name__ == "__main__":
    test_cases = [
        "halo kak, aku mau tanya soal refund 😐",
        "hmm... gk pa2 deh kak, thanks ya! https://example.com",
        "Refund bisa dlm 14 hari kerja ya kak?",
        "iya dong👍 bgt kak",
        "Saya mau pesan product dgn harga 150000",
        # LaTeX / math notation
        r"Hasilnya adalah $\frac{1}{2}$ dari total.",
        r"Rumusnya $x^2 + 3x - 5 = 0$ ya kak.",
        r"Luas lingkaran \(\pi r^2\).",
        r"Akar dari 16 adalah \sqrt{16} yaitu 4.",
        r"Diskon \(20\%\) untuk pembelian \(x \geq 100000\).",
        # Plain-text (non-LaTeX) math — the cases the LLM actually emits
        "Jadi 3 x 4 = 12 ya kak.",
        "Hitung 2^3 dulu, lalu 10 / 2.",
        "Luas = panjang x lebar.",
        "Nilai x^2 + 5 itu berapa?",
        "Diskonnya 20% dari 150000.",
        "Akar √16 sama dengan 4, dan 5 ≥ 3.",
        "Suhu turun 5 - 2 derajat, hasilnya x².",
        # Plain text that must stay intact (no false math conversion)
        "anak-anak bermain di taman pukul 10/06/2026",
        "pilih ya/tidak dan baca FAQ dulu",
    ]

    print("Text Cleaning Test Results:")
    print("=" * 60)
    for text in test_cases:
        cleaned = clean_transcript(text)
        print(f"Input:  {text}")
        print(f"Output: {cleaned}")
        print("-" * 60)