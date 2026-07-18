import './globals.css';
import 'katex/dist/katex.min.css';
import type { Metadata, Viewport } from 'next';
import WorkspaceShell from './components/WorkspaceShell';
import ServiceWorkerRegistrar from './components/ServiceWorkerRegistrar';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://hermes.smartefp.com';

export const metadata: Metadata = {
  title: {
    default: 'Hermes Studio',
    template: '%s · Hermes Studio',
  },
  description: 'Interface d\'orchestration multi-agents propulsée par Hermes.',
  applicationName: 'Hermes Studio',
  keywords: ['Hermes', 'IA', 'agents', 'MCP', 'orchestration', 'MiniMax', 'productivité'],
  authors: [{ name: 'Younes', url: SITE_URL }],
  creator: 'Younes',
  publisher: 'Hermes',
  metadataBase: new URL(SITE_URL),
  alternates: { canonical: '/' },
  manifest: '/manifest.json',
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any', type: 'image/x-icon' },
      { url: '/icon.svg', type: 'image/svg+xml', sizes: 'any' },
      { url: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: [{ url: '/apple-icon.png', sizes: '180x180', type: 'image/png' }],
    shortcut: ['/favicon.ico'],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Hermes',
    startupImage: ['/icons/icon-512.png'],
  },
  formatDetection: { telephone: false, email: false, address: false },
  openGraph: {
    type: 'website',
    locale: 'fr_FR',
    url: SITE_URL,
    siteName: 'Hermes Studio',
    title: 'Hermes Studio — Orchestration multi-agents',
    description: 'Créez des agents IA, explorez les outils MCP et conversez avec Hermes.',
    images: [{ url: '/icons/icon-512.png', width: 512, height: 512, alt: 'Hermes Studio' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Hermes Studio',
    description: 'Orchestration multi-agents propulsée par Hermes.',
    images: ['/icons/icon-512.png'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, 'max-image-preview': 'large', 'max-snippet': -1 },
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  minimumScale: 1,
  userScalable: true,
  viewportFit: 'cover',
  interactiveWidget: 'resizes-content',
  themeColor: [
    { media: '(prefers-color-scheme: dark)', color: '#0a0a0f' },
    { media: '(prefers-color-scheme: light)', color: '#f3f6fb' },
  ],
  colorScheme: 'dark light',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <head>
        {/* PWA — install prompt */}
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#0a0a0f" media="(prefers-color-scheme: dark)" />
        <meta name="theme-color" content="#f3f6fb" media="(prefers-color-scheme: light)" />

        {/* iOS PWA */}
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="Hermes" />
        <link rel="apple-touch-icon" href="/apple-icon.png" />
        <link rel="apple-touch-startup-image" href="/icons/icon-512.png" />

        {/* Android / Chrome PWA */}
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="application-name" content="Hermes Studio" />
        <meta name="msapplication-TileColor" content="#8b5cf6" />
        <meta name="msapplication-TileImage" content="/icons/icon-512.png" />
        <meta name="msapplication-config" content="none" />

        {/* Mobile UX niceties */}
        <meta name="HandheldFriendly" content="true" />
        <meta name="MobileOptimized" content="width" />
      </head>
      <body>
        <WorkspaceShell>{children}</WorkspaceShell>
        <ServiceWorkerRegistrar />
      </body>
    </html>
  );
}
