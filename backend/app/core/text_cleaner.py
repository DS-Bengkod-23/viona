"""Indonesian text cleaner for STT output preprocessing.

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
- Common transcription error fixes for Indonesian
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern


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
_INDONESIAN_SLANG_MAP: dict[str, str] = {
    # Common abbreviations
    "gak": "tidak",
    "ga": "tidak",
    "nggak": "tidak",
    "enggak": "tidak",
    "nggaknya": "tidak",
    "g": "tidak",
    "tdk": "tidak",
    "gk": "tidak",
    "td": "tadi",
    "d": "di",
    "bgt": "banget",
    "bangett": "banget",
    "banged": "banget",
    "sgt": "sangat",
    "sdh": "sudah",
    "udah": "sudah",
    "blm": "belum",
    "jd": "jadi",
    "jdi": "jadi",
    "sm": "sama",
    "sama": "sama",
    "dr": "dari",
    "tp": "tapi",
    "tpi": "tapi",
    "dl": "dulu",
    "lg": "lagi",
    "lgi": "lagi",
    "kalo": "kalau",
    "kl": "kalau",
    "utk": "untuk",
    "utk": "untuk",
    "yg": "yang",
    "yg": "yang",
    "dgn": "dengan",
    "dg": "dengan",
    "dgn": "dengan",
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
    "km": "kamu",
    "aq": "aku",
    "gw": "aku",
    "sy": "saya",
    "ane": "saya",
    "gua": "saya",
    "lu": "kamu",
    "loe": "kamu",
    "loe": "kamu",
    "org": "orang",
    "orng": "orang",
    "byk": "banyak",
    "bnyk": "banyak",
    "brg": "barang",
    "brp": "berapa",
    "kmrn": "kemarin",
    "kmrn": "kemarin",
    "bsk": "besok",
    "bsk": "besok",
    "lusa": "besok",
    "skr": "sekarang",
    "skrg": "sekarang",
    "skrng": "sekarang",
    "smg": "semoga",
    "smoga": "semoga",
    "jd": "jadi",
    "jd": "jadi",
    "bkn": "bukan",
    "bukan": "bukan",
    "sm": "sampai",
    "smpe": "sampai",
    "jn": "jan",
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
    # Common greetings
    "pagi2": "pagi",
    "mlm2": "malam",
    "sore2": "sore",
}

# Common STT errors for Indonesian (homophones, common mistakes)
_STT_ERROR_FIXES: dict[str, str] = {
    # Numbers
    "satu ": "1 ",
    "dua ": "2 ",
    "tiga ": "3 ",
    "empat ": "4 ",
    "lima ": "5 ",
    "enam ": "6 ",
    "tujuh ": "7 ",
    "delapan ": "8 ",
    "sembilan ": "9 ",
    "sepuluh ": "10 ",
    # Common confusions
    "ribu ": "ribu ",
    "juta ": "juta ",
    "ratus ": "ratus ",
    # Time
    "pagi": "pagi",
    "siang": "siang",
    "sore": "sore",
    "malam": "malam",
    # Common words
    "iya": "iya",
    "ya": "ya",
    "Tidak": "tidak",
    "kok": "kok",
    "kan": "kan",
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

    # Expand common abbreviations
    result = _expand_abbreviations(result)

    # Format numbers
    result = _format_numbers(result)

    # Remove excessive punctuation
    result = _MULTIPLE_PUNCTUATION.sub('.', result)

    # Clean up spacing around punctuation
    result = re.sub(r'\s+([.,!?])', r'\1', result)
    result = re.sub(r'([.,!?])(?=\S)', r'\1 ', result)

    # Remove special characters that might cause TTS issues
    result = re.sub(r'[\[\]{}]', '', result)
    result = _EMOJI_PATTERN.sub('', result)

    # Normalize quotes
    result = result.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")

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
        # Remove repeated characters (except for emphasis like "bagus banget")
        (r'(\w)\1{3,}', r'\1\1'),
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

    # Format dates
    text = re.sub(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', r'\1 \2 \3', text)

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
    ]

    print("Text Cleaning Test Results:")
    print("=" * 60)
    for text in test_cases:
        cleaned = clean_transcript(text)
        print(f"Input:  {text}")
        print(f"Output: {cleaned}")
        print("-" * 60)