import type { NextConfig } from "next";

const backendUrl = (process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  allowedDevOrigins: process.env.DEV_ALLOWED_ORIGINS?.split(",").map(value => value.trim()).filter(Boolean),
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
      { source: "/audio/:path*", destination: `${backendUrl}/audio/:path*` },
    ];
  },
};

export default nextConfig;
