import { Sparkles, ChevronDown, Settings2, Plus, Menu } from 'lucide-react';
import { Agent } from '../../lib/api';

interface ChatHeaderProps {
  agents: Agent[];
  selectedAgentName: string;
  onChooseAgent: (agentName: string) => void;
  onOpenSettings: () => void;
  onNewConversation: () => void;
}

export default function ChatHeader({
  agents,
  selectedAgentName,
  onChooseAgent,
  onOpenSettings,
  onNewConversation
}: ChatHeaderProps) {
  
  const handleMenuClick = () => {
    window.dispatchEvent(new Event('hermes:toggle-sidebar'));
  };

  return (
    <header className="chat-header">
      <div className="chat-header-left">
        <button 
          className="mobile-menu-button" 
          onClick={handleMenuClick}
          aria-label="Ouvrir le menu"
        >
          <Menu size={20} />
        </button>
        <div className="chat-title">
          <label className="agent-picker">
            <span className="sr-only">Agent actif</span>
            <select 
              value={selectedAgentName} 
              onChange={(event) => onChooseAgent(event.target.value)}
            >
              <option value="">Hermes Core</option>
              {agents.map((agent) => (
                <option key={agent.name} value={agent.name}>{agent.name}</option>
              ))}
            </select>
            <ChevronDown size={16} className="text-muted" />
          </label>
        </div>
      </div>
      
      <div className="chat-header-actions">
        <button 
          className="ghost-button" 
          onClick={onOpenSettings}
        >
          <Settings2 size={18} />
          <span className="sr-only">Paramètres</span>
        </button>
        <button 
          className="icon-button mobile-new-chat" 
          onClick={onNewConversation} 
          aria-label="Nouvelle conversation"
        >
          <Plus size={20} />
        </button>
      </div>
    </header>
  );
}
