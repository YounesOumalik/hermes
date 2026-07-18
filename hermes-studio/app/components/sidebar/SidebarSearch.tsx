import { Search } from 'lucide-react';

export default function SidebarSearch({ query, setQuery }: { query: string; setQuery: (q: string) => void }) {
  return (
    <div className="sidebar-search-container">
      <div className="sidebar-search">
        <Search size={16} color="var(--text-muted)" />
        <input
          type="text"
          placeholder="Search..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ width: '100%', backgroundColor: 'transparent', outline: 'none', border: 'none', color: 'inherit' }}
        />
      </div>
    </div>
  );
}
