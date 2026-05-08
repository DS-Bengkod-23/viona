import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "@livekit/components-styles";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Viona – Layanan Pelanggan AI",
  description: "Asisten layanan pelanggan AI berbahasa Indonesia 24/7",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
