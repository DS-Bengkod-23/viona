# Profil Konfigurasi: Dev (CPU) vs Prod (GPU)

Viona menjalankan model berat (FasterWhisper STT, VoxCPM2 TTS) yang **butuh GPU**
di produksi, tetapi mesin dev (Mac M2 / laptop tanpa CUDA) tidak punya GPU. Satu
`.env` **tidak boleh** dipakai untuk keduanya — nilai `cuda`/`float16` yang benar
untuk prod akan **crash** di dev.

Karena semua file `.env*` di-*gitignore* (mengandung rahasia), profil di sini
disajikan sebagai **blok copy-paste**, bukan file template. Salin blok yang sesuai
ke `.env` kamu, lalu isi rahasianya (LiveKit/Ollama).

> **Default kode sudah dev-safe.** `config.py` dan fallback `docker-compose.yml`
> memakai nilai CPU (`voxcpm2_device=cpu`, `whisper_compute_type=int8`,
> `VOXCPM2_ENABLED=false`). **Prod harus opt-in GPU secara eksplisit** lewat blok
> di bawah.

## Beda kunci dev vs prod

| Var | Dev (CPU/Mac) | Prod (GPU) | Kenapa |
|-----|---------------|-----------|--------|
| `VOXCPM2_ENABLED` | `false` | `true` | VoxCPM2 tak bisa jalan tanpa GPU di dev |
| `VOXCPM2_DEVICE` | `cpu` | `cuda` | Metal/MPS tak tersedia di dalam kontainer Linux |
| `WHISPER_DEVICE` | `auto` | `cuda` | `auto` memilih CPU saat tak ada CUDA |
| `WHISPER_COMPUTE_TYPE` | `int8` | `float16` | **`float16` INVALID di CPU** (faster-whisper raise) |
| `WHISPER_MODEL_SIZE` | `large-v3`* | `large-v3` | *dev boleh turunkan (mis. `small`) demi kecepatan iterasi (lihat task G) |

Rahasia (`LIVEKIT_*`, `OLLAMA_*`, dll.) sama di kedua profil.

## Blok DEV (`.env` untuk laptop / Mac M2)

```dotenv
# ── Model: DEV / CPU ──────────────────────────────────────────────
VOXCPM2_ENABLED=false
VOXCPM2_DEVICE=cpu
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=int8
WHISPER_MODEL_SIZE=large-v3      # boleh 'small' untuk iterasi lebih cepat
```

Catatan: dengan `VOXCPM2_ENABLED=false`, jika bot Pipecat sempat spawn di dev,
`_build_tts()` akan **gagal dengan pesan jelas** (bukan crash torchaudio kriptik).
Jalur suara penuh (Jalur B) memang tak bisa divalidasi end-to-end di dev tanpa GPU.

## Blok PROD (`.env` untuk host GPU)

```dotenv
# ── Model: PROD / GPU ─────────────────────────────────────────────
VOXCPM2_ENABLED=true
VOXCPM2_DEVICE=cuda
VOXCPM2_REFERENCE_AUDIO=/app/assets/voice_reference_processed.wav
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
WHISPER_MODEL_SIZE=large-v3
```

## Akar masalah `torchaudio` gagal load di dev

Kontainer dev = **`aarch64 Linux`** (Docker Desktop di Mac M2). `torchaudio`
gagal memuat native extension-nya:

```
OSError: Could not load this library:
  .../torchaudio/lib/_torchaudio.abi3.so
```

Ini **isu native-extension ARM64**, **terpisah** dari ketiadaan GPU. Strateginya:

1. **Dev:** jangan load VoxCPM2/torchaudio sama sekali — `VOXCPM2_ENABLED=false`
   memastikan `_build_tts()` tak pernah mengimpor `voxcpm` (impor-nya *lazy* di
   dalam `_load_model()`), jadi torchaudio tak pernah tersentuh.
2. **Prod (GPU):** pin `torch`+`torchaudio` build CUDA yang cocok (versi ABI
   sepasang) untuk arsitektur target. Bila target prod tetap ARM64, pin wheel
   `aarch64` yang native-lib-nya utuh; bila x86_64+CUDA, gunakan index CUDA resmi.

> Iterasi TTS di dev sebaiknya via jalur non-Pipecat (uji `normalize_for_tts` +
> unit test) atau di mesin GPU — bukan memaksa VoxCPM2 jalan di kontainer ARM CPU.
