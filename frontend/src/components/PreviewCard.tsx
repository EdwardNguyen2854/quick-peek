import { AlertCircle, CheckCircle2, Copy, Layers, Maximize2 } from 'lucide-react';
import { withToken } from '../api';
import type { FileItem, Format, SearchResult } from '../types';

function sizeLabel(bytes: number) {
  if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes > 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

export default function PreviewCard({ result, format, onOpen }: { result: SearchResult; format: Format; onOpen: (file: FileItem) => void }) {
  const file = result.files[0];
  const missing = result.status === 'not_found';
  const multiple = result.status === 'multiple_matches';

  return (
    <article className={`preview-card ${missing ? 'missing' : ''}`}>
      <header>
        <div>
          <h3>{result.code}</h3>
          <p>{format.toUpperCase()} · {missing ? 'No file found' : `${result.matches_count} match${result.matches_count > 1 ? 'es' : ''}`}</p>
        </div>
        {missing ? <AlertCircle size={20} /> : <CheckCircle2 size={20} />}
      </header>

      <div className="preview-frame">
        {file ? (
          (file.preview_kind === 'glb' || file.preview_kind === 'obj') ? (
            <div className="step-mini">
              <Layers size={34} />
              <span>{file.preview_kind === 'obj' ? 'OBJ preview ready' : '3D preview ready'}</span>
            </div>
          ) : file.preview_kind === 'pdf' ? (
            <iframe
              className="preview-pdf-card"
              src={`${withToken(file.preview_url)}#toolbar=0&navpanes=0&scrollbar=0&page=1&view=FitH`}
              title={`${result.code} PDF preview`}
            />
          ) : (
            <img src={withToken(file.preview_url)} alt={`${result.code} preview`} />
          )
        ) : (
          <div className="empty-preview">No preview</div>
        )}
      </div>

      {file && (
        <footer>
          <div className="file-meta">
            <strong title={file.filename}>{file.filename}</strong>
            <span>{sizeLabel(file.size_bytes)} · {file.preview_kind.toUpperCase()}</span>
            {file.message && <em>{file.message}</em>}
          </div>
          <button className="icon-button" onClick={() => onOpen(file)} title="Open bigger view">
            <Maximize2 size={18} />
          </button>
        </footer>
      )}
      {multiple && <div className="badge"><Copy size={13} /> Multiple matches; showing newest first</div>}
    </article>
  );
}
