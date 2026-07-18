import type { ReactNode } from 'react';

type SkeletonProps = {
  className?: string;
  children?: ReactNode;
};

export function Skeleton({ className, children }: SkeletonProps) {
  return (
    <div className={`skeleton ${className || ''}`} aria-hidden="true">
      {children}
    </div>
  );
}

export function SkeletonLine({ width = '100%' }: { width?: string }) {
  return <div className="skeleton skeleton-line" style={{ width }} />;
}

export function SkeletonCard() {
  return (
    <div className="skeleton skeleton-card">
      <div className="skeleton-avatar" />
      <div className="skeleton-lines">
        <SkeletonLine width="60%" />
        <SkeletonLine width="80%" />
      </div>
    </div>
  );
}

export function SkeletonMessage() {
  return (
    <div className="skeleton skeleton-message">
      <div className="skeleton-avatar small" />
      <div className="skeleton-lines">
        <SkeletonLine width="45%" />
        <SkeletonLine width="90%" />
        <SkeletonLine width="70%" />
      </div>
    </div>
  );
}
