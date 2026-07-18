import ConversationItem from './ConversationItem';

export type Conversation = {
  id: string;
  title: string;
  updatedAt?: string;
  created_at?: string;
  updated_at?: string;
};

export default function ConversationList({ 
  conversations, 
  activeId 
}: { 
  conversations: Conversation[]; 
  activeId: string;
}) {
  // We can group them by date later if needed, for now just a flat list for simplicity
  return (
    <div className="conversation-list">
      <div className="conversation-group-title">Recent</div>
      {conversations.map(c => (
        <ConversationItem key={c.id} id={c.id} title={c.title} isActive={c.id === activeId} />
      ))}
      {conversations.length === 0 && (
        <div style={{ padding: '8px 12px', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          Aucune conversation
        </div>
      )}
    </div>
  );
}
