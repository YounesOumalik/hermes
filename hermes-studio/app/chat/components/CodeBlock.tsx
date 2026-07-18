'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { Check, Copy } from 'lucide-react';

type CodeBlockProps = {
  language?: string;
  children: ReactNode;
  raw?: string;
};

export default function CodeBlock({ language, children, raw }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 1500);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function handleCopy() {
    const text = raw ?? extractText(children);
    if (!text) return;
    try {
      await navigator.clipboard?.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="code-block">
      <div className="code-block-header">
        <span className="code-block-lang">{language || 'code'}</span>
        <button
          type="button"
          className="code-block-copy"
          onClick={handleCopy}
          aria-label={copied ? 'Copié' : 'Copier le code'}
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? 'Copié' : 'Copier'}
        </button>
      </div>
      <pre className="code-block-pre">
        <code className={language ? `language-${language}` : undefined}>{children}</code>
      </pre>
    </div>
  );
}

function extractText(node: ReactNode): string {
  if (node === null || node === undefined || node === false) return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(extractText).join('');
  if (typeof node === 'object' && 'props' in node) {
    return extractText((node as { props: { children?: ReactNode } }).props?.children);
  }
  return '';
}
