import SidebarHeader from './SidebarHeader';
import SidebarSearch from './SidebarSearch';
import ConversationList, { Conversation } from './ConversationList';
import SidebarFooter from './SidebarFooter';

interface SidebarProps {
  isOpen: boolean;
  toggleSidebar: () => void;
  query: string;
  setQuery: (q: string) => void;
  conversations: Conversation[];
  activeId: string;
  theme: string;
  toggleTheme: () => void;
}

export default function Sidebar({
  isOpen,
  toggleSidebar,
  query,
  setQuery,
  conversations,
  activeId,
  theme,
  toggleTheme,
}: SidebarProps) {
  return (
    <>
      <div className={`mobile-backdrop ${isOpen ? 'open' : ''}`} onClick={toggleSidebar} />
      <div className={`sidebar-container ${isOpen ? 'open' : ''}`}>
        <SidebarHeader toggleSidebar={toggleSidebar} />
        <SidebarSearch query={query} setQuery={setQuery} />
        <ConversationList conversations={conversations} activeId={activeId} />
        <SidebarFooter theme={theme} toggleTheme={toggleTheme} />
      </div>
    </>
  );
}
