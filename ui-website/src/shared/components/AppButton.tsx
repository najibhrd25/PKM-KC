interface AppButtonProps {
  label: string;
  disabled?: boolean;
  variant?: 'primary' | 'secondary';
  className?: string;
  onPress: () => void;
}

export function AppButton({
  label,
  disabled = false,
  variant = 'primary',
  className = '',
  onPress,
}: AppButtonProps) {
  return (
    <button
      type="button"
      className={`flex min-h-12 items-center justify-center px-[18px] transition-all active:scale-[0.98] active:opacity-80 ${
        variant === 'primary' ? 'bg-danger' : 'bg-surface-high'
      } ${disabled ? 'pointer-events-none opacity-[0.45]' : 'cursor-pointer'} ${className}`}
      disabled={disabled}
      onClick={onPress}
    >
      <span
        className={`text-xs font-extrabold tracking-[2px] ${
          variant === 'secondary' ? 'text-foreground' : 'text-white'
        }`}
      >
        {label}
      </span>
    </button>
  );
}
