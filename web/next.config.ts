import type { NextConfig } from "next";

const backend = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // The centre what-if rescored 50 cases twice and can take about a minute on a cold start.
  experimental: { proxyTimeout: 180_000 },
  // Same-origin /api: no CORS, and the family token never leaves our origin.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
