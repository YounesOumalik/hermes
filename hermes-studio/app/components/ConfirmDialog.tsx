'use client';

import Dialog from './Dialog';

type ConfirmDialogProps = {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  variant?: 'danger' | 'warning' | 'info';
  confirmLabel?: string;
  cancelLabel?: string;
  loading?: boolean;
};

export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  variant = 'info',
  confirmLabel = 'Confirmer',
  cancelLabel = 'Annuler',
  loading,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} title={title} description={message}>
      <div className="modal-actions">
        <button
          type="button"
          className="button button-secondary"
          onClick={onClose}
          disabled={loading}
        >
          {cancelLabel}
        </button>
        <button
          type="button"
          className={`button ${variant === 'danger' ? 'button-danger' : 'button-primary'}`}
          onClick={onConfirm}
          disabled={loading}
        >
          {loading ? 'En cours…' : confirmLabel}
        </button>
      </div>
    </Dialog>
  );
}
