"use client";

import { HTMLAttributes, ReactNode } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "glass" | "flat" | "elevated";
  hoverable?: boolean;
  padding?: "sm" | "md" | "lg";
  children: ReactNode;
}

/**
 * Card réutilisable (glassmorphism par défaut).
 */
export function Card({
  variant = "glass",
  hoverable = false,
  padding = "md",
  children,
  className = "",
  ...rest
}: CardProps) {
  const classes = [
    "card",
    `card-${variant}`,
    `card-padding-${padding}`,
    hoverable ? "card-hover" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  );
}

export default Card;
