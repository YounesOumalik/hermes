"use client";

import { ReactNode } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  retryLabel?: string;
  icon?: ReactNode;
  className?: string;
}

/**
 * Error state réutilisable (erreur réseau, 500, etc.)
 */
export function ErrorState({
  title = "Something went wrong",
  message = "An unexpected error occurred. Please try again.",
  onRetry,
  retryLabel = "Retry",
  icon,
  className = "",
}: ErrorStateProps) {
  return (
    <div className={`error-state ${className}`} role="alert">
      <div className="error-state-icon">
        {icon || <AlertCircle size={48} />}
      </div>
      <h3 className="error-state-title">{title}</h3>
      <p className="error-state-message">{message}</p>
      {onRetry && (
        <button
          type="button"
          className="btn btn-secondary btn-size-md"
          onClick={onRetry}
        >
          <RefreshCw size={14} />
          {retryLabel}
        </button>
      )}
    </div>
  );
}

export default ErrorState;
