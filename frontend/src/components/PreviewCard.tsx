import { AlertCircle, Check, CircleHelp, Copy, Expand } from 'lucide-react';
import { apiUrl } from '../api';
import type { FileItem, Format, SearchResult } from '../types';
import { StepCardViewer } from './viewers/StepViewer';

function sizeLabel(bytes: number) {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

function statusCopy(result: SearchResult) {
  if (result.status === 'not_found') return 'No match';
  if (result.status === 'suggested') return 'Possible match only';
  return result.match_reason || `${result.matches_count} match${result.matches_count === 1 ? '' : 'es'}`;
}

export default function PreviewCard({
  result,
  searchFormat,
  cardHeight,
  pauseStepPreview,
  onOpen
}: {
  result: SearchResult;
  searchFormat: Format;
  cardHeight: number;
  pauseStepPreview: boolean;
  onOpen: (file: FileItem) => void;
}) {
  const file = result.recommended_file || result.files[0];
  const missing = result.status === 'not_found';
  const suggested = result.status === 'suggested';
  const multiple = result.status === 'multiple_matches';

  return (
    <article className={`preview-card ${missing ? 'missing' : ''} ${suggested ? 'suggested' : ''}`} style={{ height: cardHeight }}>
      <div className="card-heading">
        <div className="card-code">
          <span className={`status-dot ${missing ? 'missing' : suggested ? 'suggested' : 'found'}`} />
          <div>
            <h3>{result.code}</h3>
            <p>{statusCopy(result)}</p>
          </div>
        </div>
        {missing ? <AlertCircle size={18} /> : suggested ? <CircleHelp size={18} /> : <Check size={18} />}
      </div>

      <div className="preview-frame">
        {file ? (
          file.preview_kind === 'step' ? (
            <StepCardViewer url={apiUrl(file.preview_url)} label={file.filename} suspended={pauseStepPreview} />
          ) : file.preview_kind === 'pdf' ? (
            <iframe
              className="preview-pdf-card"
              src={`${apiUrl(file.preview_url)}#toolbar=0&navpanes=0&scrollbar=0&page=1&view=FitH`}
              title={`${result.code} PDF preview`}
            />
          ) : file.preview_kind === 'html' || file.preview_kind === 'txt' ? (
            <iframe className="preview-document-card" src={apiUrl(file.preview_url)} title={`${result.code} document preview`} />
          ) : file.preview_kind === 'svg' ? (
            <img src={apiUrl(file.preview_url)} alt={`${result.code} preview`} />
          ) : (
            <div className="empty-preview">{file.message || 'Preview unavailable'}</div>
          )
        ) : suggested ? (
          <div className="suggestion-panel">
            <span className="suggestion-title">Did you mean?</span>
            {result.suggestions.map((suggestion) => (
              <div className="suggestion-item" key={suggestion.file_id}>
                <strong>{suggestion.filename}</strong>
                <span>{suggestion.reason}{suggestion.revision ? ` · Rev ${suggestion.revision}` : ''}</span>
              </div>
            ))}
            <em>Suggestions are never selected automatically.</em>
          </div>
        ) : (
          <div className="empty-preview">No indexed {searchFormat === 'all' ? 'file' : searchFormat.toUpperCase() + ' file'} matched this code.</div>
        )}

        {file && (
          <button className="preview-open" onClick={() => onOpen(file)} title="Open large preview" type="button">
            <Expand size={15} />
            Open
          </button>
        )}
      </div>

      <div className="card-footer">
        {file ? (
          <>
            <div className="file-meta">
              <strong title={file.filename}>{file.filename}</strong>
              <span>{sizeLabel(file.size_bytes)} · {file.format.toUpperCase()}</span>
              <div className="match-context">
                {file.match_reason && <span>{file.match_reason}</span>}
                {file.revision && <span>Rev {file.revision}</span>}
                {file.folder_class && file.folder_class !== 'normal' && <span>{file.folder_class}</span>}
              </div>
            </div>
            {multiple && result.matches_count > 1 && (
              <span className="match-badge" title="Alternative strong matches">
                <Copy size={12} /> +{result.matches_count - 1}
              </span>
            )}
          </>
        ) : suggested ? (
          <span className="missing-copy">{result.suggestions.length} nearby filename suggestion{result.suggestions.length === 1 ? '' : 's'}</span>
        ) : (
          <span className="missing-copy">Try refreshing the index or checking the identifier.</span>
        )}
      </div>
    </article>
  );
}
