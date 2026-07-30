from __future__ import annotations

import asyncio
import json
import re
from time import perf_counter

import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.infrastructure.rag.retriever import get_rag_retriever
from app.infrastructure.session.store import get_session_store

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Skema JSON untuk structured output Ollama: model mengembalikan jawaban lengkap
# (diucapkan via TTS) SEKALIGUS satu bubble insight singkat (≤4 kata) yang paling
# relevan dari jawaban itu, dalam satu roundtrip (menghindari 2x panggilan LLM).
_BUBBLE_TYPES = ("insight", "mnemonic", "formula", "warning")
_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {"type": "string"},
        "bubble": {
            "type": ["object", "null"],
            "properties": {
                "type": {"type": "string", "enum": list(_BUBBLE_TYPES)},
                "text": {"type": "string"},
            },
            "required": ["type", "text"],
        },
    },
    "required": ["response"],
}
_LANGUAGE_INSTRUCTION = (
    "\n\nATURAN BAHASA: SELALU jawab dalam Bahasa Indonesia yang natural. "
    "Jangan pernah bercampur dengan aksara atau bahasa lain (mis. Mandarin, "
    "Jepang, Korea) di tengah jawaban, kecuali istilah teknis yang memang "
    "lazim ditulis apa adanya (mis. \"accuracy\", \"precision\", \"epoch\")."
)

_BREVITY_INSTRUCTION = (
    "\n\nGAYA JAWABAN (dibacakan via suara): ringkas dan natural seperti sedang "
    "ngobrol — idealnya 2-3 kalimat. Langsung ke inti, hindari bertele-tele. "
    "Untuk matematika saat diucapkan: pakai kata/simbol yang mudah dibaca "
    "(mis. \"×\" untuk kali, bukan huruf \"x\")."
)

_BUBBLE_INSTRUCTION = (
    "\n\nFORMAT OUTPUT (WAJIB JSON, jangan tulis apa pun di luar JSON ini):\n"
    '{"response": "<jawaban lengkap seperti biasa, akan dibacakan via TTS>", '
    '"bubble": {"type": "insight|mnemonic|formula|warning", "text": "<maks 4 kata>"} atau null}\n'
    "Isi \"bubble\" HANYA jika ada satu poin kunci yang layak ditonjolkan dari jawaban Anda:\n"
    "- insight: fakta/poin penting inti\n"
    "- mnemonic: jembatan keledai/cara mengingat\n"
    "- formula: rumus/persamaan singkat\n"
    "- warning: peringatan miskonsepsi umum\n"
    "Pilih tipe yang paling sesuai dengan isi jawaban saat itu (tidak harus selalu sama). "
    "\"text\" pada bubble MAKSIMAL 4 kata. Jika tidak ada poin yang cukup layak, isi \"bubble\" dengan null."
)

# Memori Q&A statis: jawaban & bubble sudah disiapkan manual untuk pertanyaan
# tertentu (dicek sebelum memanggil LLM — instan & deterministik). Cocok dipakai
# untuk pertanyaan umum yang sering muncul, tidak perlu digenerate ulang tiap kali.
# Matching: cocok jika PESAN mengandung minimal satu keyword dari SETIAP grup
# (AND antar grup, OR di dalam grup) — mis. ["rumus"] AND ["mean","rata-rata"].
_STATIC_QA: list[dict] = [
    {
        "keyword_groups": [["rumus"], ["mean", "rata-rata", "rata rata"]],
        "answer": (
            "Rumus mean (rata-rata) adalah jumlah seluruh nilai data dibagi dengan "
            "banyaknya data. Misalnya untuk data 2, 4, 6, 8, mean-nya adalah "
            "(2 + 4 + 6 + 8) dibagi 4, sama dengan 5."
        ),
        "bubbles": [
            {"type": "formula", "text": "Mean = Σx / n"},
            {"type": "mnemonic", "text": "Jumlah bagi banyak"},
        ],
    },
    {
        "keyword_groups": [["preprocessing", "praproses", "pra-proses", "pra proses"]],
        "answer": (
            "Preprocessing adalah tahap membersihkan dan menyiapkan data mentah sebelum "
            "dipakai untuk melatih model. Contohnya menangani missing value, encoding "
            "data kategorikal jadi angka, dan scaling atau normalisasi fitur numerik "
            "supaya rentang nilainya sebanding."
        ),
        "bubbles": [
            {"type": "insight", "text": "Bersihkan data dulu"},
            {"type": "mnemonic", "text": "Encode, Impute, Scale"},
        ],
    },
    {
        "keyword_groups": [
            ["model", "modeling", "pemodelan"],
            ["machine learning", "algoritma", "latih", "training"],
        ],
        "answer": (
            "Modeling adalah tahap melatih algoritma machine learning menggunakan data "
            "yang sudah di-preprocessing, supaya model bisa mempelajari pola dalam data "
            "dan membuat prediksi pada data baru yang belum pernah dilihat sebelumnya."
        ),
        "bubbles": [
            {"type": "insight", "text": "Model belajar dari data"},
            {"type": "warning", "text": "Hindari data leakage"},
        ],
    },
    {
        "keyword_groups": [["hyperparameter", "hyper parameter"]],
        "answer": (
            "Hyperparameter tuning adalah proses mencari kombinasi pengaturan model, "
            "seperti learning rate atau jumlah pohon, yang menghasilkan performa "
            "terbaik. Caranya biasanya dengan Grid Search (coba semua kombinasi) atau "
            "Random Search (coba kombinasi acak)."
        ),
        "bubbles": [
            {"type": "formula", "text": "Grid vs Random Search"},
            {"type": "insight", "text": "Cari kombinasi terbaik"},
        ],
    },
    {
        "keyword_groups": [
            ["cross validation", "cross-validation", "validasi silang", "k-fold", "kfold"]
        ],
        "answer": (
            "Cross validation (validasi silang) membagi data menjadi beberapa bagian "
            "atau fold, lalu melatih dan menguji model secara bergantian di tiap "
            "bagian. Tujuannya supaya evaluasi performa model lebih stabil dan tidak "
            "bergantung pada satu pembagian data saja."
        ),
        "bubbles": [
            {"type": "formula", "text": "Data dibagi K bagian"},
            {"type": "mnemonic", "text": "Latih gantian, uji gantian"},
        ],
    },
    {
        "keyword_groups": [["scatterplot", "scatter plot", "diagram pencar", "titik sebar"]],
        "answer": (
            "Scatterplot (diagram pencar) menampilkan hubungan antara dua variabel "
            "numerik sebagai titik-titik di bidang koordinat. Kalau titik-titiknya "
            "membentuk pola naik atau turun, itu tanda ada korelasi antara kedua "
            "variabel tersebut. Sering ditambahkan garis regresi untuk menunjukkan "
            "arah tren datanya."
        ),
        "bubbles": [
            {"type": "insight", "text": "Lihat pola sebaran titik"},
            {"type": "formula", "text": "Garis tren = regresi"},
        ],
        "image": "scatterplot",
    },
    {
        "keyword_groups": [["histogram"]],
        "answer": (
            "Histogram menampilkan distribusi (sebaran) satu variabel numerik dengan "
            "mengelompokkan data ke dalam beberapa rentang nilai (bin), lalu "
            "menghitung berapa banyak data di tiap rentang. Bentuknya membantu "
            "melihat apakah data condong ke kiri, ke kanan, atau simetris."
        ),
        "bubbles": [
            {"type": "insight", "text": "Lihat bentuk sebaran data"},
        ],
        "image": "histogram",
    },
    {
        "keyword_groups": [["boxplot", "box plot", "diagram kotak"]],
        "answer": (
            "Boxplot (diagram kotak) menampilkan ringkasan sebaran data lewat lima "
            "angka: nilai minimum, kuartil 1, median, kuartil 3, dan maksimum. "
            "Titik-titik di luar whisker (garis) menandakan outlier atau nilai yang "
            "tidak biasa."
        ),
        "bubbles": [
            {"type": "formula", "text": "Q1, Median, Q3"},
            {"type": "warning", "text": "Titik luar = outlier"},
        ],
        "image": "boxplot",
    },
    {
        "keyword_groups": [["heatmap", "peta panas", "korelasi", "correlation"]],
        "answer": (
            "Heatmap korelasi menampilkan kekuatan hubungan antar variabel numerik "
            "dalam bentuk warna: warna makin gelap/pekat berarti korelasinya makin "
            "kuat. Nilai korelasi berkisar dari -1 (berlawanan sempurna) sampai +1 "
            "(searah sempurna), dengan 0 berarti tidak ada hubungan."
        ),
        "bubbles": [
            {"type": "formula", "text": "Korelasi -1 sampai 1"},
            {"type": "warning", "text": "Korelasi ≠ kausalitas"},
        ],
        "image": "heatmap",
    },
    {
        "keyword_groups": [
            ["confusion matrix", "matriks kebingungan", "true positive", "false positive"]
        ],
        "answer": (
            "Confusion matrix menampilkan hasil prediksi model dibandingkan dengan "
            "label sebenarnya, dibagi jadi empat: True Positive (benar diprediksi "
            "positif), False Positive (salah diprediksi positif), False Negative "
            "(salah diprediksi negatif), dan True Negative (benar diprediksi negatif)."
        ),
        "bubbles": [
            {"type": "mnemonic", "text": "TP, FP, FN, TN"},
            {"type": "insight", "text": "Bandingkan prediksi vs aktual"},
        ],
        "image": "confusion_matrix",
    },
    {
        "keyword_groups": [
            ["akurasi", "accuracy", "precision", "presisi", "recall", "f1", "f1-score", "f1 score"]
        ],
        "answer": (
            "Ada empat metrik evaluasi utama untuk model klasifikasi: Accuracy (akurasi) "
            "mengukur proporsi prediksi benar dari seluruh data, Precision mengukur "
            "seberapa tepat prediksi positif model, Recall mengukur seberapa banyak "
            "kasus positif sebenarnya yang berhasil ditemukan, dan F1 Score adalah "
            "rata-rata harmonik antara Precision dan Recall untuk menyeimbangkan "
            "keduanya."
        ),
        "bubbles": [
            {"type": "formula", "text": "Akurasi = (TP+TN)/Total"},
            {"type": "formula", "text": "Precision = TP/(TP+FP)"},
            {"type": "formula", "text": "Recall = TP/(TP+FN)"},
            {"type": "formula", "text": "F1 = 2PR/(P+R)"},
        ],
        "image": "classification_metrics",
    },
    {
        "keyword_groups": [["imbalance", "kelas tidak seimbang", "data tidak seimbang"]],
        "answer": (
            "Data imbalance terjadi ketika satu kelas jumlahnya jauh lebih banyak "
            "dari kelas lainnya, misalnya pada dataset Heart Failure yang lebih "
            "banyak pasien sehat daripada yang berisiko. Kalau dibiarkan, model "
            "cenderung bias menebak kelas mayoritas terus."
        ),
        "bubbles": [
            {"type": "warning", "text": "Model bias ke mayoritas"},
            {"type": "insight", "text": "Cek proporsi tiap kelas"},
        ],
        "image": "imbalance",
    },
    {
        "keyword_groups": [["roc curve", "kurva roc", "roc-auc", "auc"]],
        "answer": (
            "Kurva ROC menampilkan performa model klasifikasi dengan membandingkan "
            "True Positive Rate dan False Positive Rate di berbagai ambang batas "
            "(threshold). Makin kurva mendekati pojok kiri atas dan makin jauh dari "
            "garis diagonal, makin bagus performa modelnya."
        ),
        "bubbles": [
            {"type": "insight", "text": "Dekat pojok kiri atas"},
            {"type": "formula", "text": "AUC mendekati 1"},
        ],
        "image": "roc_curve",
    },
]


def _extract_json_obj(text: str) -> str:
    """Ambil objek JSON dari output model untuk structured-output.

    Model cloud (mis. *-cloud) sering MENGABAIKAN param `format` dan membungkus
    JSON dalam pagar markdown ```json ... ``` atau menambah prosa. Fungsi ini
    membuang pagar dan mengambil dari '{' pertama sampai '}' terakhir agar
    json.loads berhasil.
    """
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t).strip()
    if not t.startswith("{"):
        i, j = t.find("{"), t.rfind("}")
        if i != -1 and j > i:
            t = t[i : j + 1]
    return t


def _match_static_qa(message: str, history: list[ChatHistoryTurn] | None = None) -> dict | None:
    lower = message.lower()
    for entry in _STATIC_QA:
        if all(any(kw in lower for kw in group) for group in entry["keyword_groups"]):
            return entry
    return None


class ChatHistoryTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    material_id: str | None = None  # filter RAG per-materi LMS (mis. "matematika")
    version: str | None = None      # filter RAG per-versi (mis. "v1")
    lms_context: str | None = None  # text context directly injected from the web page
    syllabus: str | None = None     # Daftar isi/silabus keseluruhan course
    history: list[ChatHistoryTurn] | None = None  # beberapa giliran terakhir, untuk konteks follow-up
    is_quiz: bool = False            # halaman kuis: Viona tolak jawaban soal (tetap bantu konsep)
    course_title: str | None = None  # judul course aktif (dinamis dari DOM)
    session_id: str | None = None    # id session (persist transkrip ke Redis)


async def _retrieve_context(query: str, material_id: str | None, version: str | None) -> str:
    """Ambil konteks relevan dari basis pengetahuan (RAG). Gagal-aman: kalau RAG
    bermasalah, kembalikan string kosong agar chat tetap jalan (degradasi mulus)."""
    try:
        retriever = await get_rag_retriever()
        hits = await retriever.search(
            query,
            material_id=material_id,
            version=version,
            top_k=3,
            score_threshold=0.45,
        )
    except Exception as e:
        logger.warning("rag retrieval failed, lanjut tanpa konteks", error=str(e))
        return ""

    if not hits:
        return ""
    return "\n".join(f"- {h['text']}" for h in hits)


# Guardrail kuis (halaman KUIS): Viona TIDAK boleh memberi jawaban langsung soal,
# tapi WAJIB tetap membantu menjelaskan KONSEP dari materi course (rule 2
# app/prompts/indonesian.py). Disisipkan ke system prompt saat is_quiz — bukan
# memblok semua pertanyaan (bantuan konsep tetap jalan).
_QUIZ_GUARD = (
    "\n\nPERHATIAN — HALAMAN KUIS: Siswa sedang di halaman kuis/latihan. DILARANG "
    "KERAS memberi jawaban langsung atas soal (memilih opsi, menyebut jawaban akhir, "
    "atau menyelesaikan soal untuk siswa). TAPI kamu WAJIB tetap MEMBANTU siswa "
    "memahami KONSEP yang relevan dari materi dan mengarahkannya menemukan jawaban "
    "sendiri. Jika siswa meminta jawaban langsung, tolak dengan ramah lalu tawarkan "
    "penjelasan konsepnya."
)


def _instruction_suffix(is_quiz: bool) -> str:
    """Rakit imbuhan instruksi untuk system prompt (bahasa, brevity, guard kuis, bubble)."""
    suffix = _LANGUAGE_INSTRUCTION + _BREVITY_INSTRUCTION
    if is_quiz:
        suffix += _QUIZ_GUARD
    suffix += _BUBBLE_INSTRUCTION
    return suffix


def _log_session(session_id: str | None, user_msg: str, reply: str, image: str | None = None) -> None:
    """Catat 1 giliran (user + assistant) ke Redis session store (fire-and-forget)."""
    if not session_id:
        return

    async def _do() -> None:
        try:
            store = await get_session_store()
            await store.log_interaction(session_id, "user", user_msg)
            await store.log_interaction(session_id, "assistant", reply, image=image)
        except Exception as exc:  # noqa: BLE001 - logging session tak boleh gagalkan chat
            logger.warning("session log failed", error=str(exc))

    asyncio.create_task(_do())


@router.post("")
async def chat_with_viona(body: ChatRequest) -> dict:
    """Chat dengan Viona: RAG (Qdrant) + LLM (Ollama native API)."""
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty")

    static_match = _match_static_qa(body.message, body.history)
    if static_match:
        logger.info("chat static match", keyword_groups=static_match["keyword_groups"])
        _log_session(body.session_id, body.message, static_match["answer"], image=static_match.get("image"))
        return {
            "response": static_match["answer"],
            "bubbles": static_match["bubbles"],
            "image": static_match.get("image"),
            "status": "ok",
            "timings_ms": None,
        }

    t_rag = perf_counter()
    context_current = body.lms_context.strip() if body.lms_context else ""
    context_rag = await _retrieve_context(body.message, body.material_id, body.version)
    rag_ms = (perf_counter() - t_rag) * 1000

    system_prompt = (
        "Anda adalah Viona, asisten virtual cerdas untuk LMS Bengkel Koding.\n"
        "Tugas utama Anda adalah membantu menjawab pertanyaan siswa MURNI BERDASARKAN "
        "materi pelajaran (baik yang sedang dibuka maupun dari silabus course).\n\n"
        "ATURAN KETAT (PENTING):\n"
        "1. Jika pertanyaan siswa berkaitan dengan materi di HALAMAN SAAT INI atau HASIL PENCARIAN, "
        "berikan jawaban yang jelas dan edukatif berdasarkan teks tersebut.\n"
        "2. Jika pertanyaan siswa berada di luar cakupan SILABUS KURSUS dan konteks yang diberikan, Anda DILARANG KERAS "
        "menggunakan pengetahuan umum untuk menjawab. Anda HARUS MENOLAK dengan ramah "
        "dan menyatakan bahwa pertanyaan tersebut berada di luar materi.\n"
        "3. JANGAN PERNAH memulai jawaban dengan sapaan seperti 'Halo' atau memperkenalkan diri.\n"
        "4. JANGAN menebak-nebak jawaban."
    )

    course_label = (
        f" COURSE ({body.course_title.strip()})"
        if body.course_title and body.course_title.strip()
        else ""
    )
    
    context_block = ""
    if body.syllabus and body.syllabus.strip():
        context_block += f"SILABUS{course_label}:\n{body.syllabus.strip()}\n\n"
    if context_current:
        context_block += f"KONTEKS HALAMAN SAAT INI:\n{context_current}\n\n"
    if context_rag:
        context_block += f"HASIL PENCARIAN MATERI LAIN (RAG):\n{context_rag}\n\n"

    system_prompt += _instruction_suffix(body.is_quiz)

    # Gunakan native Ollama API (/api/chat)
    ollama_url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"

    # Riwayat percakapan (giliran terakhir dari frontend) disisipkan sebelum
    # pesan user saat ini, supaya pertanyaan lanjutan yang merujuk jawaban
    # sebelumnya (tanpa mengulang kata kunci topik) tetap dipahami modelnya.
    history_messages = [
        {"role": turn.role, "content": turn.content}
        for turn in (body.history or [])
        if turn.role in ("user", "assistant") and turn.content.strip()
    ]

    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            *history_messages,
            {"role": "user", "content": f"{context_block}{body.message}"},
        ],
        "format": _RESPONSE_SCHEMA,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.7,
        },
    }

    headers = {}
    if settings.ollama_api_key:
        headers["Authorization"] = f"Bearer {settings.ollama_api_key}"

    t_llm = perf_counter()
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Tanpa try-except pelindung agar error asli (misal timeout/connection refused)
        # meledak ke terminal (HTTP 500) dan log dapat terlihat jelas untuk debugging!
        response = await client.post(ollama_url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        # /api/chat returns {"message": {"role": "assistant", "content": "..."}}
        msg = data.get("message", {})
        raw_content = msg.get("content", "").strip() if isinstance(msg, dict) else ""

    llm_wall_ms = (perf_counter() - t_llm) * 1000

    # `raw_content` seharusnya JSON sesuai _RESPONSE_SCHEMA: {"response": ..., "bubble": ...}.
    # Gagal-aman: kalau model tidak patuh (mis. model cloud yang tidak dukung structured
    # output), pakai raw_content apa adanya sebagai jawaban dan bubble ditiadakan.
    bubble: dict | None = None
    try:
        parsed = json.loads(_extract_json_obj(raw_content))
        reply = str(parsed.get("response", "")).strip()
        raw_bubble = parsed.get("bubble")
        if isinstance(raw_bubble, dict) and raw_bubble.get("type") in _BUBBLE_TYPES and raw_bubble.get("text"):
            bubble = {"type": raw_bubble["type"], "text": str(raw_bubble["text"]).strip()}
        if not reply:
            reply = raw_content
    except (json.JSONDecodeError, AttributeError, TypeError):
        logger.warning("gagal parse structured output, fallback ke teks mentah")
        reply = raw_content

    # Ollama /api/chat mengembalikan field timing dalam NANODETIK. Ini memisahkan
    # waktu generasi ASLI (eval_duration) dari pemrosesan prompt & overhead jaringan
    # (llm_wall_ms). eval_count = jumlah token output → tokens/sec. Lihat docs/TIMING.md.
    def _ms(ns: int | None) -> float | None:
        return round(ns / 1e6, 1) if ns else None

    gen_ms = _ms(data.get("eval_duration"))
    prompt_ms = _ms(data.get("prompt_eval_duration"))
    total_ms = _ms(data.get("total_duration"))
    out_tokens = data.get("eval_count")
    tok_per_s = (
        round(out_tokens / (data["eval_duration"] / 1e9), 1)
        if out_tokens and data.get("eval_duration")
        else None
    )
    # Cloud-routed models (e.g. *-cloud) return 0 for eval_duration/prompt_eval_duration,
    # so gen_ms/prompt_ms/tok_per_s are None. Effective throughput from wall-clock stays
    # meaningful for both cloud and local. See docs/TIMING.md.
    eff_tok_per_s = (
        round(out_tokens / (llm_wall_ms / 1000), 1) if out_tokens and llm_wall_ms else None
    )

    logger.info(
        "chat timing",
        rag_ms=round(rag_ms, 1),
        llm_wall_ms=round(llm_wall_ms, 1),
        gen_ms=gen_ms,
        prompt_ms=prompt_ms,
        tok_per_s=tok_per_s,
        eff_tok_per_s=eff_tok_per_s,
        out_tokens=out_tokens,
        out_chars=len(reply),
        has_context=bool(context_current),
        has_bubble=bool(bubble),
    )
    _log_session(body.session_id, body.message, reply)
    return {
        "response": reply,
        "bubbles": [bubble] if bubble else [],
        "image": None,
        "status": "ok",
        "timings_ms": {
            "rag": round(rag_ms, 1),
            "llm_wall": round(llm_wall_ms, 1),
            "llm_generation": gen_ms,
            "llm_prompt_eval": prompt_ms,
            "llm_total": total_ms,
            "tokens_per_sec": tok_per_s,
            "eff_tokens_per_sec": eff_tok_per_s,
        },
    }
