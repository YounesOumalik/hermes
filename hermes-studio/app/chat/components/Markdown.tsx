'use client';

import { memo, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeHighlight from 'rehype-highlight';
import rehypeKatex from 'rehype-katex';
import type { Components } from 'react-markdown';
import CodeBlock from './CodeBlock';

type MarkdownProps = {
  children: string;
};

const components: Components = {
  a({ href, children }) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    );
  },
  table({ children }) {
    return (
      <div className="markdown-table-wrap">
        <table>{children}</table>
      </div>
    );
  },
  pre({ children }) {
    // On laisse <code> gérer le rendu via CodeBlock. react-markdown passe déjà
    // le code dans un <code className="language-xxx"> à l'intérieur du <pre>.
    return <>{children}</>;
  },
  code({ className, children, ...rest }) {
    const match = /language-(\w+)/.exec(className || '');
    const language = match?.[1];
    const isInline = !className && !String(children).includes('\n');
    if (isInline) {
      return (
        <code className="inline-code" {...rest}>
          {children}
        </code>
      );
    }
    return (
      <CodeBlock language={language} raw={String(children).replace(/\n$/, '')}>
        {children}
      </CodeBlock>
    );
  },
};

function MarkdownBase({ children }: MarkdownProps) {
  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }], rehypeKatex]}
        components={components}
        unwrapDisallowed
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}

const Markdown = memo(MarkdownBase);
export default Markdown;

export type { ReactNode };
