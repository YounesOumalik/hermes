import { Settings, Moon, Sun } from 'lucide-react';
import Link from 'next/link';

export default function SidebarFooter({ theme, toggleTheme }: { theme: string; toggleTheme: () => void }) {
  return (
    <div className="sidebar-footer">
      <div className="user-profile">
        <div className="user-avatar">YO</div>
        <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>Younes</div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button onClick={toggleTheme} className="icon-btn" title="Toggle theme">
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <Link href="/settings" className="icon-btn" title="Settings">
          <Settings size={18} />
        </Link>
      </div>
    </div>
  );
}
