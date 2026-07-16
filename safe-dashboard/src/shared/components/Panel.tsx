import { ReactNode } from 'react';

interface PanelProps {
  children: ReactNode;
  className?: string;
}

export function Panel({ children, className = '' }: PanelProps) {
  return (
    <div className={`border border-border bg-surface-low ${className}`}>
      {children}
    </div>
  );
}
