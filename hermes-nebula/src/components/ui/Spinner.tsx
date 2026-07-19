"use client";

import { Loader2 } from "lucide-react";

interface SpinnerProps {
  size?: number;
  label?: string;
  fullscreen?: boolean;
  className?: string;
}

/**
 * Spinner réutilisable (loading indicator).
 * - fullscreen : recouvre tout l'écran
 * - size : taille en px (default 24)
 * - label : texte affiché à côté
 */
export function Spinner({
  size = 24,
  label,
  fullscreen = false,
  className = "",
}: SpinnerProps) {
  if (fullscreen) {
    return (
      <div className={`spinner-fullscreen ${className}`}>
        <Loader2 size={size} className="spinner-icon" />
        {label && <p className="spinner-label">{label}</p>}
      </div>
    );
  }
  return (
    <span className={`spinner-inline ${className}`} role="status">
      <Loader2 size={size} className="spinner-icon" />
      {label && <span className="spinner-label">{label}</span>}
    </span>
  );
}

export default Spinner;
