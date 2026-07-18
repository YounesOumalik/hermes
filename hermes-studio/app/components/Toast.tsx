'use client';

import { CheckCircle2, X, XCircle } from 'lucide-react';
import { type ReactNode, useEffect, useState } from 'react';

type ToastKind = 'success' | 'error' | 'info';

type ToastData = {
  id: number;
  kind: ToastKind;
  message: ReactNode;
};

let _counter = 0;
const listeners = new Set<() => void>();

function notify() { listeners.forEach((fn) => fn()); }

export function showToast(kind: ToastKind, message: ReactNode) {
  _counter += 1;
  const id = _counter;
  const key = 'hermes-toasts';
  const raw = window.localStorage.getItem(key);
  const toasts: ToastData[] = raw ? JSON.parse(raw) : [];
  toasts.push({ id, kind, message });
  window.localStorage.setItem(key, JSON.stringify(toasts.slice(-5)));
  notify();
  window.setTimeout(() => {
    dismissToast(id);
  }, 5000);
  return id;
}

export function dismissToast(id: number) {
  const key = 'hermes-toasts';
  const raw = window.localStorage.getItem(key);
  if (!raw) return;
  const toasts: ToastData[] = JSON.parse(raw);
  const filtered = toasts.filter((t) => t.id !== id);
  window.localStorage.setItem(key, JSON.stringify(filtered));
  notify();
}

export function clearToasts() {
  window.localStorage.removeItem('hermes-toasts');
  notify();
}

export default function ToastContainer() {
  const [, setTick] = useState(0);

  useEffect(() => {
    const cb = () => setTick((t) => t + 1);
    listeners.add(cb);
    return () => { listeners.delete(cb); };
  }, []);

  let toasts: ToastData[] = [];
  try { toasts = JSON.parse(window.localStorage.getItem('hermes-toasts') || '[]'); } catch { /* noop */ }

  if (!toasts.length) return null;

  return (
    <div className="toast-container" aria-live="polite">
      {toasts.map((toast) => {
        const Icon = toast.kind === 'success' ? CheckCircle2 : toast.kind === 'error' ? XCircle : CheckCircle2;
        return (
          <div key={toast.id} className={`toast toast-${toast.kind}`}>
            <span className="toast-icon"><Icon size={15} /></span>
            <span className="toast-message">{toast.message}</span>
            <button
              className="toast-dismiss"
              onClick={() => dismissToast(toast.id)}
              aria-label="Fermer"
              type="button"
            >
              <X size={13} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
