/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    HERMES_DAEMON_URL: process.env.HERMES_DAEMON_URL || 'http://hermes-daemon:8001',
  },
};

module.exports = nextConfig;
