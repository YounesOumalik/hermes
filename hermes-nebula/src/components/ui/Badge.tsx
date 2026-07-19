"use client";

import { ReactNode } from "react";

export type BadgeVariant =
  | "default"
  | "active"
  | "pending"
  | "error"
  | "success"
  | "superadmin"
  | "info";

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
}

const variantMap: Record<BadgeVariant, string> = {
  default: "badge-default",
  active: "badge-active",
  pending: "badge-pending",
  error: "badge-error",
  success: "badge-success",
  superadmin: "badge-superadmin",
  info: "badge-info",
};

/**
 * Badge réutilisable (status, role, tag).
 */
export function Badge({
  variant = "default",
  children,
  icon,
  className = "",
}: BadgeProps) {
  return (
    <span className={`badge ${variantMap[variant]} ${className}`}>
      {icon && <span className="badge-icon">{icon}</span>}
      {children}
    </span>
  );
}

export default Badge;
