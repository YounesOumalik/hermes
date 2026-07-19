"use client";

import { ReactNode, useState } from "react";

interface TabItem {
  id: string;
  label: string;
  icon?: ReactNode;
  content: ReactNode;
}

interface TabsProps {
  items: TabItem[];
  defaultTab?: string;
  onChange?: (tabId: string) => void;
  className?: string;
}

/**
 * Tabs contrôlés (interne) avec indicateur actif.
 */
export function Tabs({
  items,
  defaultTab,
  onChange,
  className = "",
}: TabsProps) {
  const [active, setActive] = useState(defaultTab || items[0]?.id);

  const handleTabChange = (tabId: string) => {
    setActive(tabId);
    onChange?.(tabId);
  };

  const activeItem = items.find((i) => i.id === active) || items[0];

  return (
    <div className={`tabs ${className}`}>
      <div className="tabs-header" role="tablist">
        {items.map((item) => (
          <button
            key={item.id}
            role="tab"
            aria-selected={active === item.id}
            className={`tab-button ${active === item.id ? "tab-active" : ""}`}
            onClick={() => handleTabChange(item.id)}
            type="button"
          >
            {item.icon && <span className="tab-icon">{item.icon}</span>}
            {item.label}
          </button>
        ))}
      </div>
      <div className="tabs-content" role="tabpanel">
        {activeItem?.content}
      </div>
    </div>
  );
}

export default Tabs;
