import './globals.css';
import 'katex/dist/katex.min.css';
import type { Metadata, Viewport } from 'next';
import WorkspaceShell from './components/WorkspaceShell';

export const metadata: Metadata = {
  title: 'Hermes Studio',
  description: 'Interface d\'orchestration multi-agents',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: dark)', color: '#080b12' },
    { media: '(prefers-color-scheme: light)', color: '#f3f6fb' },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body>
        <WorkspaceShell>{children}</WorkspaceShell>
      </body>
    </html>
  );
}
