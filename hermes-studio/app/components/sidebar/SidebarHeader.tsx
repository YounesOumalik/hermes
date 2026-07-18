import Link from 'next/link';
import { Plus, Sparkles, PanelLeftClose } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function SidebarHeader({ toggleSidebar }: { toggleSidebar?: () => void }) {
  const router = useRouter();
  return (
    <div className="sidebar-header">
      <Link href="/chat" className="sidebar-brand">
        <Sparkles size={20} color="var(--accent)" />
        <span>Hermes</span>
      </Link>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button onClick={() => router.push('/chat')} className="new-chat-btn" title="New Chat">
          <Plus size={16} /> <span>New</span>
        </button>
        {toggleSidebar && (
          <button onClick={toggleSidebar} className="icon-btn mobile-menu-btn" style={{ display: 'none' /* handled by media query usually, but inline for now */ }} title="Close Sidebar">
            <PanelLeftClose size={18} />
          </button>
        )}
      </div>
    </div>
  );
}
