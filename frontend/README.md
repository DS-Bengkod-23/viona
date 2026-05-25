# Viona - Voice-Enabled AI Assistant

Viona adalah aplikasi web interaktif yang memungkinkan pengguna untuk berkomunikasi dengan AI assistant melalui percakapan berbasis suara dan teks. Aplikasi ini menyediakan pengalaman pengguna yang modern dengan visualisasi audio real-time, chat history, dan antarmuka yang responsif.

## 🎯 Fitur Utama

- **Assistive Voice Communication** - Berkomunikasi dengan AI assistant menggunakan suara atau teks
- **Real-time Audio Visualization** - Visualisasi dinamis audio dengan berbagai gaya (Aura, Bar, Wave)
- **Live Chat Interface** - Antarmuka percakapan real-time dengan chat history
- **Session Management** - Pengelolaan sesi dengan timer dan status koneksi
- **Dark/Light Theme** - Dukungan tema gelap dan terang untuk kenyamanan pengguna
- **User Feedback Widget** - Widget untuk mengumpulkan feedback pengguna
- **Responsive Design** - Desain responsif yang bekerja di semua ukuran layar
- **Audio Input Control** - Kontrol mute/unmute untuk input audio pengguna

## 🛠️ Tech Stack

### Frontend Framework
- **Next.js 16** - React framework untuk production
- **React 19** - UI library
- **TypeScript 5.7.3** - Type-safe JavaScript

### UI & Styling
- **Tailwind CSS 4** - Utility-first CSS framework
- **PostCSS 8** - CSS transformer
- **Radix UI** - Unstyled, accessible components library
- **Lucide React 0.564** - Icon library
- **Motion 12.38** - Animation library
- **Embla Carousel 8.6** - Carousel component

### Real-time Communication
- **LiveKit 2.19** - Platform untuk real-time audio/video
- **LiveKit Components React 2.9.21** - Pre-built LiveKit components

### Form & Validation
- **React Hook Form 7.54** - Form state management
- **Zod 3.24** - TypeScript-first schema validation
- **Hookform Resolvers 3.9** - Integration package

### Utilities & Libraries
- **Date-fns 4.1** - Date utility library
- **Recharts 2.15** - Charting library
- **Sonner 1.7** - Toast notification library
- **Next Themes 0.4** - Theme management
- **Class Variance Authority 0.7** - Variant management
- **CLSX 2.1** - Classname utility
- **Tailwind Merge 3.3** - Merge Tailwind classes
- **Input OTP 1.4** - OTP input component
- **React Resizable Panels 2.1** - Resizable panel layout
- **Vaul 1.1** - Drawer component
- **CMDk 1.1** - Command menu component
- **React Day Picker 9.13** - Date picker component

### Development Tools
- **ESLint** - Code linting
- **Autoprefixer 10.4** - CSS vendor prefix
- **Tailwind Animate CSS 1.3** - Animation utilities

## 📋 Prasyarat

Sebelum memulai, pastikan Anda telah menginstal:
- **Node.js** - Version 18 atau lebih tinggi
- **pnpm** - Package manager (recommended) atau npm/yarn

Untuk memeriksa versi Node.js:
```bash
node --version
```

## 🚀 Instalasi & Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd viona
```

### 2. Instalasi Dependencies
Menggunakan pnpm (recommended):
```bash
pnpm install
```

Atau menggunakan npm:
```bash
npm install
```

### 3. Konfigurasi Environment

Salin template environment:

```bash
cp .env.local.example .env.local
```

Isi untuk development lokal (frontend + backend terpisah):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Token LiveKit diambil otomatis dari backend (`GET /api/token`). Tidak perlu `NEXT_PUBLIC_LIVEKIT_*`.

Untuk Docker Compose (`http://localhost` via nginx), biarkan `NEXT_PUBLIC_API_URL` kosong.

### 4. Jalankan Development Server
```bash
pnpm dev
```

Aplikasi akan tersedia di `http://localhost:3000`

## 📂 Struktur Project

```
frontend/
├── src/
│   ├── app/                  # Next.js App Router
│   │   ├── layout.tsx        # Root layout
│   │   ├── page.tsx          # Home (LiveKit + backend)
│   │   ├── demo/page.tsx     # UI demo (browser TTS, tanpa backend)
│   │   └── admin/page.tsx    # Admin dashboard
│   ├── components/
│   ├── ui/                  # Reusable UI components (50+ components)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   └── ...
│   ├── voice-assistant/     # Voice assistant components
│   │   ├── voice-assistant.tsx
│   │   ├── audio-visualizer.tsx
│   │   ├── chat-message.tsx
│   │   ├── user-audio-input.tsx
│   │   ├── status-panel.tsx
│   │   ├── session-timer.tsx
│   │   └── feedback-widget.tsx
│   ├── agents-ui/           # Agent-specific UI components
│   │   ├── agent-audio-visualizer-aura.tsx
│   │   ├── agent-audio-visualizer-bar.tsx
│   │   └── agent-audio-visualizer-wave.tsx
│   └── theme-provider.tsx   # Theme configuration
├── hooks/                   # Custom React hooks
│   ├── use-mobile.ts
│   ├── use-toast.ts
│   └── agents-ui/
├── lib/
│   └── utils.ts
├── public/                  # Static assets
├── components.json
├── next.config.mjs
├── tailwind.config.mjs
├── postcss.config.mjs
├── tsconfig.json
└── package.json
```

## 🎮 Cara Menggunakan

### Memulai Percakapan
1. Buka aplikasi di browser (http://localhost:3000)
2. Klik tombol "Mulai" untuk menghubungkan ke voice assistant
3. Tunggu hingga status menunjukkan "Connected"

### Mengirim Pesan
**Dengan Suara:**
- Klik tombol microphone untuk memulai recording
- Berbicara ke microphone
- Klik tombol stop atau tunggu hingga deteksi suara selesai

**Dengan Teks:**
- Ketik pesan di input field
- Tekan Enter atau klik tombol Send

### Fitur Tambahan
- **Mute/Unmute** - Gunakan tombol mute untuk mengontrol input audio
- **Dark Mode** - Klik ikon matahari/bulan untuk mengganti tema
- **Feedback** - Berikan feedback tentang respons assistant
- **Session Timer** - Pantau durasi sesi Anda

## 💻 Development

### Scripts Tersedia

```bash
# Development server dengan hot reload
pnpm dev

# Build untuk production
pnpm build

# Start production server
pnpm start

# Run linting
pnpm lint
```

### Menambahkan UI Component Baru

Aplikasi menggunakan komponen dari Radix UI dan styling dengan Tailwind CSS:

```typescript
// components/ui/custom-component.tsx
import * as React from "react"
import { cn } from "@/lib/utils"

export interface CustomProps
  extends React.HTMLAttributes<HTMLDivElement> {}

const CustomComponent = React.forwardRef<HTMLDivElement, CustomProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("your-classes", className)}
      {...props}
    />
  )
)
CustomComponent.displayName = "CustomComponent"

export { CustomComponent }
```

### Menambahkan Custom Hook

```typescript
// hooks/use-custom-hook.ts
import { useState, useCallback } from "react"

export function useCustomHook() {
  const [state, setState] = useState(false)
  
  const toggle = useCallback(() => {
    setState(prev => !prev)
  }, [])
  
  return { state, toggle }
}
```

## 🔧 Troubleshooting

### Port 3000 Sudah Digunakan
```bash
# Gunakan port berbeda
pnpm dev -- -p 3001
```

### Build Error dengan TypeScript
```bash
# Clear cache dan rebuild
rm -rf .next
pnpm build
```

### Audio Tidak Bekerja
- Periksa izin akses microphone di browser
- Pastikan LiveKit configuration tersedia di `.env.local`
- Cek console untuk error messages

## 📚 Resources & Documentation

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Radix UI Components](https://www.radix-ui.com/docs/primitives/overview/introduction)
- [LiveKit Documentation](https://docs.livekit.io/)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)

## 🤝 Contributing

Kontribusi sangat diterima! Untuk berkontribusi:

1. Fork repository
2. Buat branch untuk feature baru (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push ke branch (`git push origin feature/amazing-feature`)
5. Buka Pull Request

## 📝 Lisensi

Project ini dilisensikan di bawah MIT License - lihat file LICENSE untuk detail.

## 💬 Support & Questions

Jika Anda memiliki pertanyaan atau menemukan issue:
- Buka issue di repository
- Diskusikan di discussion forum
- Hubungi tim development

---

**Dibuat dengan ❤️ untuk pengalaman voice assistant yang lebih baik**