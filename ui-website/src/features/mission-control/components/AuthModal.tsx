import { useState } from 'react';

import { AppButton } from '@/shared/components/AppButton';

interface AuthModalProps {
  visible: boolean;
  onClose: () => void;
  onSubmit: (password: string) => boolean;
}

export function AuthModal({ visible, onClose, onSubmit }: AuthModalProps) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState(false);

  function handleSubmit() {
    const success = onSubmit(password);
    if (success) {
      setPassword('');
      setError(false);
      onClose();
      return;
    }

    setPassword('');
    setError(true);
  }

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-6">
      {/* Backdrop */}
      <div className="absolute inset-0" onClick={onClose} />

      {/* Modal Content */}
      <div className="relative z-10 w-full max-w-sm border border-border bg-surface p-6">
        <p className="mb-4 text-center font-mono text-sm font-black tracking-[3px] text-danger">
          LOCK
        </p>
        <p className="text-center text-lg font-black tracking-wider text-foreground">
          AUTHORIZATION REQUIRED
        </p>
        <p
          className={`mb-4 mt-2 text-center font-mono text-[10px] tracking-[1.4px] ${
            error ? 'text-danger-soft' : 'text-muted'
          }`}
        >
          {error ? 'ACCESS DENIED' : 'Enter maintenance password'}
        </p>

        <input
          type="password"
          autoComplete="off"
          className={`mb-4 w-full border bg-transparent px-4 py-3 text-center font-mono text-base uppercase tracking-[2px] text-foreground outline-none placeholder:text-muted ${
            error ? 'border-danger' : 'border-border'
          }`}
          placeholder="PASSWORD"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            setError(false);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSubmit();
          }}
        />

        <div className="flex flex-row gap-3">
          <AppButton className="flex-1" label="CANCEL" variant="secondary" onPress={onClose} />
          <AppButton className="flex-1" label="AUTHORIZE" onPress={handleSubmit} />
        </div>
      </div>
    </div>
  );
}
