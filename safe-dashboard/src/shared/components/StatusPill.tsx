interface StatusPillProps {
  label: string;
  tone?: 'active' | 'idle' | 'danger';
  isPulsing?: boolean;
}

export function StatusPill({ label, tone = 'idle', isPulsing = false }: StatusPillProps) {
  const dotColor = {
    active: 'bg-success',
    idle: 'bg-muted',
    danger: 'bg-danger',
  }[tone];

  return (
    <div className="flex flex-row items-center gap-2">
      <div className={`h-2 w-2 rounded ${dotColor} ${isPulsing ? 'animate-pulse' : ''}`} />
      <span className="font-mono text-[10px] font-bold tracking-[1.8px] text-foreground">
        {label}
      </span>
    </div>
  );
}
