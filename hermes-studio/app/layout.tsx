import './globals.css';
import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Hermes Studio',
  description: 'Interface d\'orchestration multi-agents',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body>
        <nav className="topnav">
          <Link href="/">Hermes Studio</Link>
          <Link href="/chat">Chat</Link>
          <Link href="/agents">Agents</Link>
          <Link href="/tools">Tools</Link>
          <Link href="/settings">Settings</Link>
        </nav>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
