/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  images: {
    unoptimized: true,
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    return [
      { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
      { source: "/health", destination: `${apiUrl}/health` },
      { source: "/ready", destination: `${apiUrl}/ready` },
      { source: "/docs", destination: `${apiUrl}/docs` },
      { source: "/docs/:path*", destination: `${apiUrl}/docs/:path*` },
      { source: "/openapi.json", destination: `${apiUrl}/openapi.json` },
      { source: "/sessions/:path*", destination: `${apiUrl}/sessions/:path*` },
      { source: "/ingest/:path*", destination: `${apiUrl}/ingest/:path*` },
      { source: "/chat", destination: `${apiUrl}/chat` },
      { source: "/telephony/:path*", destination: `${apiUrl}/telephony/:path*` },
      { source: "/metrics", destination: `${apiUrl}/metrics` },
    ]
  },
}

export default nextConfig
