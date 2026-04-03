'use client';

import { useState } from 'react';
import { useSystemState } from '@/store/useSystemState';

export default function AuthModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const { authPassword } = useSystemState();
  const [password, setPassword] = useState('');
  const [error, setError] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const result = authPassword(password);
    if (result) {
      setSuccess(true);
      setError(false);
      setTimeout(() => {
        setPassword('');
        setSuccess(false);
        onClose();
      }, 800);
    } else {
      setError(true);
      setPassword('');
      setTimeout(() => setError(false), 2000);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Modal */}
      <div className="glass-modal relative z-10 p-8 max-w-md w-full mx-4 animate-[fade-in_0.3s_ease-out]">
        <div className="text-center">
          <span
            className={`material-symbols-outlined text-5xl mb-4 block transition-colors ${
              success ? 'text-green-500' : error ? 'text-red-500 animate-[blink_0.3s_2]' : 'text-safe-red'
            }`}
          >
            {success ? 'lock_open' : 'lock'}
          </span>
          <h2 className="font-[family-name:var(--font-space-grotesk)] text-xl font-bold text-on-surface mb-1 tracking-tight">
            AUTHORIZATION REQUIRED
          </h2>
          <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted mb-6 tracking-[0.2em] uppercase">
            {success
              ? 'ACCESS GRANTED — MANUAL MODE ACTIVE'
              : error
              ? 'ACCESS DENIED — INVALID CREDENTIALS'
              : 'Enter maintenance password to unlock manual controls'}
          </p>
          {!success && (
            <form onSubmit={handleSubmit}>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className={`w-full bg-surface-container-lowest border ${
                  error ? 'border-red-500' : 'border-outline-variant'
                } text-on-surface font-[family-name:var(--font-jetbrains-mono)] text-center text-lg py-3 px-4 mb-4 focus:outline-none focus:border-safe-red transition-colors`}
                autoFocus
              />
              <div className="flex gap-4 justify-center">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-8 py-3 bg-surface-container-high text-secondary font-[family-name:var(--font-space-grotesk)] font-bold text-sm tracking-[0.2em] uppercase hover:bg-surface-container-highest transition-colors"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  className="px-8 py-3 bg-safe-red text-white font-[family-name:var(--font-space-grotesk)] font-bold text-sm tracking-[0.2em] uppercase hover:opacity-90 transition-all"
                >
                  AUTHORIZE
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
