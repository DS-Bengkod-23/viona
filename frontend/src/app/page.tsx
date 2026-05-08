import dynamic from "next/dynamic";
import Link from "next/link";

// LiveKit uses browser APIs – must be client-only
const VoiceAgent = dynamic(() => import("@/components/VoiceAgent"), { ssr: false });

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Navbar */}
      <nav className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">🤖</span>
            <span className="font-bold text-white text-lg">Viona AI</span>
            <span className="px-2 py-0.5 bg-blue-600/20 text-blue-400 text-xs rounded-full border border-blue-600/30">
              Beta
            </span>
          </div>
          <Link
            href="/admin"
            className="text-sm text-slate-400 hover:text-slate-200 transition-colors"
          >
            Dashboard Admin →
          </Link>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 max-w-lg mx-auto w-full px-4 py-6 flex flex-col" style={{ minHeight: "calc(100vh - 3.5rem)" }}>
        <VoiceAgent />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-4 text-center text-slate-600 text-xs">
        Layanan AI 24/7 · Bahasa Indonesia · Powered by LiveKit + Ollama
      </footer>
    </div>
  );
}
