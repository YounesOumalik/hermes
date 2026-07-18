import Link from 'next/link';

export default function ConversationItem({ id, title, isActive }: { id: string; title: string; isActive: boolean }) {
  return (
    <Link
      href={`/chat?conversation=${id}`}
      className={`conversation-item ${isActive ? 'active' : ''}`}
      title={title}
    >
      {title || 'Nouvelle conversation'}
    </Link>
  );
}
