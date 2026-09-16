import { AlertCircle, Check, Copy, Expand } from 'lucide-react';
import { apiUrl } from '../api';
import type { FileItem, Format, SearchResult } from '../types';
import { StepThumbnail } from './viewers/StepViewer';

function sizeLabel(bytes: number) {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

export default function PreviewCard({
  result,
  format,
  onOpen
}: {
  result: SearchResult;
  format: Format;
  onOpen: (file: FileItem) => void;
}) {
  const file = result.files[0];
  const missing = result.status === 'not_found';
  const multiple = result.status === 'multiple_matches';

  return (
    <article className={`preview-card ${missing ? 'missing' : ''}`}>
      <div className="card-heading">
        <div className="card-code">
          <span className={`status-dot ${missing ? 'missing' : 'found'}`} />
          <div>
            <h3>{result.code}</h3>
            <p>{missing ? 'No match' : `${result.matches_count} match${result.matches_count === 1 ? '' : 'es'}`}</p>
          </div>
        </div>
        {missing ? <AlertCircle size={18} /> : <Check size={18} />}
      </div>

      <div className="preview-frame">
        {file ? (
          file.preview_kind === 'step' ? (
            <StepThumbnail url={apiUrl(file.preview_url)} label={file.filename} />
          ) : file.preview_kind === 'pdf' ? (
            <iframe
              className="preview-pdf-card"
              src={`${apiUrl(file.preview_url)}#toolbar=0&navpanes=0&scrollbar=0&page=1&view=FitH`}
              title={`${result.code} PDF preview`}
            />
          ) : file.preview_kind === 'html' || file.preview_kind === 'txt' ? (
            <iframe
              className="preview-document-card"
              src={apiUrl(file.preview_url)}
              title={`${result.code} document preview`}
            />
          ) : file.preview_kind === 'svg' ? (
            <img src={apiUrl(file.preview_url)} alt={`${result.code} preview`} />
          ) : (
            <div className="empty-preview">{file.message || 'Preview unavailable'}</div>
          )
        ) : (
          <div className="empty-preview">No preview available</div>
        )}

        {file && (
          <button className="preview-open" onClick={() => onOpen(file)} title="Open large preview" type="button">
            <Expand size={16} />
            Open
          </button>
        )}
      </div>

      <div className="card-footer">
        {file ? (
          <>
            <div className="file-meta">
              <strong title={file.filename}>{file.filename}</strong>
              <span>{sizeLabel(file.size_bytes)} · {format.toUpperCase()}</span>
            </div>
            {multiple && <span className="match-badge"><Copy size={12} /> {result.matches_count}</span>}
          </>
        ) : (
          <span className="missing-copy">No {format.toUpperCase()} file matched this code.</span>
        )}
      </div>
    </article>
  );
}
