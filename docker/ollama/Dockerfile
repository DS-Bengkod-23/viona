# Ollama ramping untuk Viona — buang runner GPU (CUDA), pertahankan runner CPU.
#
# Di Viona container ollama TIDAK pernah inferensi GPU: LLM = cloud (gemma4:31b-cloud,
# hanya di-proxy) dan embedding (qwen3-embedding) dipanggil via /api/embed = CPU murni.
# Maka ~4.5GB library CUDA (cuda_v12/v13/jetpack5/6) 100% nganggur.
#
# Catatan: `RUN rm` di image turunan TIDAK mengecilkan image (file GPU tetap di layer
# base, rm hanya whiteout). Karena itu kita FLATTEN: salin rootfs (sesudah rm) ke satu
# layer bersih via `FROM scratch`.

# Tahap 1: buang runner GPU dari image resmi
FROM ollama/ollama:0.13.1-rc0 AS trim
RUN rm -rf /usr/lib/ollama/cuda_*
# Sisakan: libggml-base.so + libggml-cpu.so (runner CPU untuk embedding & routing).

# Tahap 2: flatten — rootfs tanpa GPU jadi satu layer
FROM scratch
COPY --from=trim / /

# Metadata hilang saat FROM scratch → re-deklarasi. NVIDIA_* dibuang (tak ada GPU).
ENV OLLAMA_HOST=0.0.0.0:11434 \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LD_LIBRARY_PATH=/usr/lib/ollama

EXPOSE 11434
ENTRYPOINT ["/bin/ollama"]
CMD ["serve"]
