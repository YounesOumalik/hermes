/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_DAEMON_URL: process.env.NEXT_PUBLIC_DAEMON_URL || 'http://169.58.30.70:8001',
  },
};

module.exports = nextConfig;
