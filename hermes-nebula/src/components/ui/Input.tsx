"use client";

import {
  InputHTMLAttributes,
  TextareaHTMLAttributes,
  forwardRef,
  ReactNode,
} from "react";

/**
 * Input réutilisable (text, email, password, number...).
 * Variantes : default, error
 */
interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  icon?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, hint, icon, className = "", id, ...rest },
  ref
) {
  const inputId = id || rest.name;
  return (
    <div className="input-wrapper">
      {label && (
        <label htmlFor={inputId} className="input-label">
          {label}
        </label>
      )}
      <div className={`input-container ${error ? "input-error" : ""}`}>
        {icon && <span className="input-icon">{icon}</span>}
        <input
          ref={ref}
          id={inputId}
          className={`input-field ${icon ? "input-with-icon" : ""} ${className}`}
          {...rest}
        />
      </div>
      {error && <span className="input-message input-message-error">{error}</span>}
      {hint && !error && <span className="input-message">{hint}</span>}
    </div>
  );
});

/**
 * Textarea réutilisable.
 */
interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea({ label, error, hint, className = "", id, ...rest }, ref) {
    const textareaId = id || rest.name;
    return (
      <div className="input-wrapper">
        {label && (
          <label htmlFor={textareaId} className="input-label">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          className={`input-field input-textarea ${error ? "input-error" : ""} ${className}`}
          {...rest}
        />
        {error && <span className="input-message input-message-error">{error}</span>}
        {hint && !error && <span className="input-message">{hint}</span>}
      </div>
    );
  }
);

export default Input;
