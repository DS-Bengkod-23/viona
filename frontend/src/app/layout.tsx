import type { Metadata } from 'next'
import { Poppins, Geist_Mono } from 'next/font/google'
import { ThemeProvider } from '@/components/theme-provider'
import 'katex/dist/katex.min.css'
import './globals.css'

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-poppins",
})
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: 'Viona',
  description: 'Asisten suara pendamping belajar LMS',
  icons: {
    icon: [
      { url: '/dashboard/viona-logo-new.png', type: 'image/png' },
    ],
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="id" suppressHydrationWarning className={`${poppins.variable} ${geistMono.variable}`}>
      <body className="font-sans antialiased bg-transparent">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange={false}
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
