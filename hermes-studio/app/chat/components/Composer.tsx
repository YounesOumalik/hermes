import { ArrowUp, Paperclip, Square, X } from 'lucide-react';
import { RefObject, KeyboardEvent, DragEvent } from 'react';
import { Attachment } from '../../lib/api';

interface ComposerProps {
  input: string;
  setInput: (value: string) => void;
  isLoading: boolean;
  canSend: boolean;
  onSend: () => void;
  onStop: () => void;
  composerRef: RefObject<HTMLTextAreaElement>;
  fileInputRef: RefObject<HTMLInputElement>;
  pendingAttachments: Attachment[];
  uploading: boolean;
  uploadError: string;
  onUpload: (files: FileList | File[]) => void;
  onRemoveAttachment: (id: string) => void;
  activeName: string;
}

export default function Composer({
  input,
  setInput,
  isLoading,
  canSend,
  onSend,
  onStop,
  composerRef,
  fileInputRef,
  pendingAttachments,
  uploading,
  uploadError,
  onUpload,
  onRemoveAttachment,
  activeName
}: ComposerProps) {
  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    onSend();
  };

  const handleDragOver = (event: DragEvent<HTMLFormElement>) => {
    event.preventDefault();
  };

  const handleDrop = (event: DragEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (event.dataTransfer.files) {
      onUpload(event.dataTransfer.files);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  return (
    <div className="composer-wrap">
      <form
        className="composer"
        onSubmit={handleSubmit}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          className="sr-only"
          type="file"
          multiple
          accept=".txt,.md,.markdown,.csv,.json,.log,.yaml,.yml,.xml,.html,.css,.js,.ts,.py,.sql,.pdf,.docx,.png,.jpg,.jpeg,.webp"
          onChange={(event) => {
            if (event.target.files) onUpload(event.target.files);
          }}
        />

        {/* Attachments Area */}
        <div className="attachment-strip">
          {pendingAttachments.map((attachment) => (
            <span className="attachment-chip" key={attachment.id}>
              <Paperclip size={13} />
              <span>{attachment.name}</span>
              <button
                type="button"
                onClick={() => onRemoveAttachment(attachment.id)}
                aria-label={`Supprimer ${attachment.name}`}
              >
                <X size={13} />
              </button>
            </span>
          ))}
          {uploading && <span className="attachment-uploading">Téléversement…</span>}
          {uploadError && <span className="attachment-error">{uploadError}</span>}
        </div>

        <textarea
          ref={composerRef}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Envoyer un message à ${activeName}…`}
          rows={1}
          aria-label="Message à Hermes"
        />

        <div className="composer-toolbar">
          <button
            type="button"
            className="icon-button"
            aria-label="Joindre un fichier"
            title="Joindre un fichier ou déposer ici"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <Paperclip size={17} />
          </button>
          
          <button
            className={`send-button ${canSend ? 'ready' : ''}`}
            type={isLoading ? 'button' : 'submit'}
            onClick={isLoading ? onStop : undefined}
            disabled={!canSend && !isLoading}
            aria-label={isLoading ? 'Arrêter' : 'Envoyer'}
          >
            {isLoading ? <Square size={15} fill="currentColor" /> : <ArrowUp size={17} />}
          </button>
        </div>
      </form>
      <p className="composer-disclaimer">
        L'IA peut faire des erreurs. Vérifiez toujours les informations critiques.
      </p>
    </div>
  );
}
