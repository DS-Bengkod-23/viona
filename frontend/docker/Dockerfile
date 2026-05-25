# ── Stage 1: deps ─────────────────────────────────────────────────────────────
# Hanya install deps — layer ini di-cache selama package.json tidak berubah.
FROM node:20-alpine AS deps
WORKDIR /app

# Copy manifes terlebih dahulu sehingga layer deps hanya rebuild jika deps berubah
COPY package.json package-lock.json ./

# Pakai npm ci (deterministik, menggunakan package-lock.json)
RUN npm ci

# ── Stage 2: build ────────────────────────────────────────────────────────────
# Rebuild Next.js setiap kali source code berubah (karena seluruh src di-COPY).
# Docker akan otomatis invalidate cache stage ini ketika ada perubahan di src/.
FROM node:20-alpine AS builder
WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

# Salin node_modules dari stage deps
COPY --from=deps /app/node_modules ./node_modules

# Gunakan ARG CACHE_BUST untuk memaksa rebuild secara eksplisit jika perlu.
# Contoh: docker compose build --build-arg CACHE_BUST=$(Get-Date -UFormat %s) frontend
ARG CACHE_BUST=1

# Salin seluruh source (.next lokal sudah dikecualikan via .dockerignore)
COPY . .

# Build Next.js (standalone output dikonfigurasi di next.config.mjs)
RUN npm run build

# ── Stage 3: runtime ──────────────────────────────────────────────────────────
# Image ringan hanya berisi output standalone — tidak ada node_modules penuh.
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

# Salin hanya artefak build yang dibutuhkan runtime
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=3 \
    CMD wget -qO- http://127.0.0.1:3000/ || exit 1

CMD ["node", "server.js"]
