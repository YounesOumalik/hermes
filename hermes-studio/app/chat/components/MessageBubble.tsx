import { Copy, RotateCcw, UserRound, Sparkles, Paperclip } from 'lucide-react';
import Markdown from './Markdown';
import { ConversationMessage } from '../../lib/api';

type ChatMessage = ConversationMessage;

interface MessageProps {
  message: ChatMessage;
  index: number;
  onCopy: (index: number, content: string) => void;
  onRegenerate: () => void;
  copied: boolean;
}

export default function MessageBubble({ message, index, onCopy, onRegenerate, copied }: MessageProps) {
  const user = message.role === 'user';
  const isInterrupted = message.time === 'interrompu';
  
  return (
    <div className={`message ${user ? 'user-message' : 'assistant-message'} ${isInterrupted ? 'is-interrupted' : ''}`}>
      <span className={`message-avatar ${user ? 'user-avatar' : 'hermes-avatar'}`}>
        {user ? <UserRound size={15} /> : <Sparkles size={15} />}
      </span>
      <div className="message-content">
        <div className="message-meta">
          <strong>{user ? 'Vous' : 'Hermes'}</strong>
          <span>{message.time}</span>
        </div>
        
        {message.attachments && message.attachments.length > 0 && (
          <div className="message-attachments">
            {message.attachments.map((attachment) => (
              <span className="attachment-chip" key={attachment.id}>
                <Paperclip size={13} /> {attachment.name}
              </span>
            ))}
          </div>
        )}
        
        <div className="message-text">
          {user ? message.content : <Markdown>{message.content}</Markdown>}
        </div>
        
        {!user && !isInterrupted && (
          <div className="message-actions">
            <button onClick={() => onCopy(index, message.content)}>
              <Copy size={13} /> {copied ? 'Copié' : 'Copier'}
            </button>
            <button onClick={onRegenerate}>
              <RotateCcw size={13} /> Régénérer
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
