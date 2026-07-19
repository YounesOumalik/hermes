"use client";

import { useState, useRef, DragEvent, ChangeEvent } from "react";
import { Upload, X, File as FileIcon, AlertCircle } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";

interface FileUploaderProps {
  /** Appelé avec l'ID du fichier uploadé, à inclure dans le payload du message. */
  onUploaded?: (fileId: string, filename: string) => void;
  /** Désactive l'uploader (pendant streaming par ex.). */
  disabled?: boolean;
  /** Taille max en Mo (default 10). */
  maxSizeMb?: number;
}

interface UploadingFile {
  id: string;
  filename: string;
  size: number;
  progress: number;
  error?: string;
  uploadedFileId?: string;
}

const MAX_SIZE_MB_DEFAULT = 10;

/**
 * Zone de drag & drop pour upload de fichiers.
 * POST /api/files/upload (multipart/form-data).
 */
export function FileUploader({
  onUploaded,
  disabled = false,
  maxSizeMb = MAX_SIZE_MB_DEFAULT,
}: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<UploadingFile[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const maxBytes = maxSizeMb * 1024 * 1024;

  const uploadFile = async (file: File) => {
    const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const entry: UploadingFile = {
      id: tempId,
      filename: file.name,
      size: file.size,
      progress: 0,
    };
    setFiles((prev) => [...prev, entry]);

    if (file.size > maxBytes) {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === tempId ? { ...f, error: `File exceeds ${maxSizeMb}MB limit` } : f
        )
      );
      return;
    }

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await apiFetch("/files/upload", {
        method: "POST",
        body: formData,
        // NE PAS définir Content-Type : le navigateur le fait avec boundary
      });

      if (!res.ok) {
        throw new ApiError(res.status, await res.text());
      }

      const data = await res.json();
      const fileId = data.id || data.file_id;
      setFiles((prev) =>
        prev.map((f) =>
          f.id === tempId ? { ...f, progress: 100, uploadedFileId: fileId } : f
        )
      );
      onUploaded?.(fileId, file.name);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Upload failed";
      setFiles((prev) =>
        prev.map((f) => (f.id === tempId ? { ...f, error: message } : f))
      );
    }
  };

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList || disabled) return;
    Array.from(fileList).forEach(uploadFile);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    handleFiles(e.dataTransfer.files);
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
    // Reset pour permettre de re-sélectionner le même fichier
    if (inputRef.current) inputRef.current.value = "";
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const openPicker = () => {
    if (!disabled) inputRef.current?.click();
  };

  return (
    <div className="file-uploader">
      <div
        className={`file-uploader-dropzone ${isDragging ? "dropzone-active" : ""} ${
          disabled ? "dropzone-disabled" : ""
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={openPicker}
        role="button"
        tabIndex={0}
        aria-label="Upload files"
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          onChange={handleInputChange}
          disabled={disabled}
          style={{ display: "none" }}
        />
        <Upload size={20} />
        <span className="file-uploader-text">
          {isDragging ? "Drop files here" : "Drag & drop or click to upload"}
        </span>
        <span className="file-uploader-hint">Max {maxSizeMb}MB per file</span>
      </div>

      {files.length > 0 && (
        <ul className="file-uploader-list">
          {files.map((f) => (
            <li
              key={f.id}
              className={`file-uploader-item ${f.error ? "item-error" : ""} ${
                f.uploadedFileId ? "item-success" : ""
              }`}
            >
              <FileIcon size={14} />
              <div className="file-uploader-item-info">
                <span className="file-uploader-item-name">{f.filename}</span>
                {f.error ? (
                  <span className="file-uploader-item-error">
                    <AlertCircle size={10} /> {f.error}
                  </span>
                ) : f.uploadedFileId ? (
                  <span className="file-uploader-item-success">Uploaded ✓</span>
                ) : (
                  <span className="file-uploader-item-progress">
                    Uploading... {f.progress}%
                  </span>
                )}
              </div>
              <button
                type="button"
                className="file-uploader-item-remove"
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(f.id);
                }}
                aria-label={`Remove ${f.filename}`}
              >
                <X size={12} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default FileUploader;
