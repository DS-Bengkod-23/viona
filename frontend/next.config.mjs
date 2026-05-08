/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      // Proxy all /api/* requests to the FastAPI backend
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://api:8000"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
