import './globals.css';
import type { Metadata } from 'next';
import WorkspaceShell from './components/WorkspaceShell';

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
        <WorkspaceShell>{children}</WorkspaceShell>
      </body>
    </html>
  );
}
