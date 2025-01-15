/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/auth/:path*',
        destination: '/api/auth/:path*', // Keep auth routes local
      },
      {
        source: '/api/:path*',
        destination: 'http://localhost:3001/api/:path*' // Backend API URL
      }
    ]
  }
}

module.exports = nextConfig 