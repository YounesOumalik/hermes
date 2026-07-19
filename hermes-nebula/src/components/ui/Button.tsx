"use client";

import { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
  fullWidth?: boolean;
}

/**
 * Bouton réutilisable du design system AgentAI.
 * Variantes : primary, secondary, ghost, danger
 * Tailles : sm (28px), md (40px), lg (48px)
 */
export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  fullWidth = false,
  children,
  className = "",
  disabled,
  ...rest
}: ButtonProps) {
  const classes = [
    "btn",
    `btn-${variant}`,
    `btn-size-${size}`,
    fullWidth ? "btn-full" : "",
    loading || disabled ? "btn-disabled" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading}
      {...rest}
    >
      {loading ? (
        <Loader2 size={size === "sm" ? 14 : 16} className="btn-spinner" />
      ) : (
        icon
      )}
      {children && <span className="btn-label">{children}</span>}
    </button>
  );
}

export default Button;
