/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  output: 'export',  // Static export for standalone mode
  trailingSlash: true,  // Outputs analyze/index.html instead of analyze.html for static server compatibility
  distDir: 'out',
  images: {
    unoptimized: true,  // Required for static export
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
  },
  // Note: rewrites are not supported in static export
  // API calls should use NEXT_PUBLIC_API_URL directly
};

export default nextConfig;
