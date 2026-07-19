"use client";

import { ReactNode, useEffect } from "react";
import { X } from "lucide-react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg";
  closeOnBackdrop?: boolean;
}

/**
 * Modal réutilisable avec backdrop glassmorphism.
 * - Ferme sur Escape
 * - Ferme sur clic backdrop (si closeOnBackdrop)
 * - Lock le scroll body quand ouvert
 */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = "md",
  closeOnBackdrop = true,
}: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleEscape);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (closeOnBackdrop && e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? "modal-title" : undefined}
    >
      <div className={`modal-container modal-size-${size}`}>
        {(title || description) && (
          <div className="modal-header">
            {title && (
              <h2 id="modal-title" className="modal-title">
                {title}
              </h2>
            )}
            {description && <p className="modal-description">{description}</p>}
            <button
              onClick={onClose}
              className="modal-close"
              aria-label="Fermer"
              type="button"
            >
              <X size={18} />
            </button>
          </div>
        )}
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}

export default Modal;
