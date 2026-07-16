/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath: "/dashboard",
  output: "standalone",
  images: {
    unoptimized: true,
  },
  async rewrites() {
    const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    return [
      { source: "/api/:path*", destination: `${apiUrl}/api/:path*`, basePath: false },
      { source: "/health", destination: `${apiUrl}/health`, basePath: false },
      { source: "/ready", destination: `${apiUrl}/ready`, basePath: false },
      { source: "/docs", destination: `${apiUrl}/docs`, basePath: false },
      { source: "/docs/:path*", destination: `${apiUrl}/docs/:path*`, basePath: false },
      { source: "/openapi.json", destination: `${apiUrl}/openapi.json`, basePath: false },
      { source: "/sessions/:path*", destination: `${apiUrl}/sessions/:path*`, basePath: false },
      { source: "/ingest/:path*", destination: `${apiUrl}/ingest/:path*`, basePath: false },
      { source: "/chat", destination: `${apiUrl}/chat`, basePath: false },
      { source: "/telephony/:path*", destination: `${apiUrl}/telephony/:path*`, basePath: false },
      { source: "/metrics", destination: `${apiUrl}/metrics`, basePath: false },
    ]
  },
}

export default nextConfig
