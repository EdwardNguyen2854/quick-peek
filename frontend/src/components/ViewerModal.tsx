import { Download, X } from 'lucide-react';
import { apiUrl } from '../api';
import type { FileFormat, FileItem } from '../types';
import StepViewer from './viewers/StepViewer';
import DxfVectorViewer from './viewers/DxfVectorViewer';
import DocViewer from './viewers/DocViewer';
import MarkdownViewer from './viewers/MarkdownViewer';
import TextViewer from './viewers/TextViewer';
import HtmlViewer from './viewers/HtmlViewer';

export default function ViewerModal({ code, format, file, onClose }: { code: string; format: FileFormat; file: FileItem; onClose: () => void }) {
  const previewUrl = apiUrl(file.preview_url);
  const rawUrl = apiUrl(file.raw_url);
  const pdfViewUrl = `${previewUrl}#toolbar=1&navpanes=0&scrollbar=1&page=1&view=FitH`;

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="viewer-modal" onMouseDown={(event) => event.stopPropagation()}>
        <header className="viewer-header">
          <div className="viewer-title">
            <span>{code}</span>
            <h2>{file.filename}</h2>
            <p>{format.toUpperCase()} preview</p>
          </div>
          <div className="viewer-actions">
            <a href={rawUrl} className="button subtle"><Download size={16} /> Download</a>
            <button className="icon-button" onClick={onClose} aria-label="Close preview"><X size={19} /></button>
          </div>
        </header>

        <div className="viewer-body">
          {format === 'step' && <StepViewer url={previewUrl} />}
          {format === 'pdf' && <iframe className="pdf-frame" src={pdfViewUrl} title={file.filename} />}
          {format === 'dxf' && <DxfVectorViewer url={previewUrl} label="DXF preview" />}
          {(format === 'doc' || format === 'xls' || format === 'ppt') && <DocViewer url={previewUrl} />}
          {format === 'md' && <MarkdownViewer url={previewUrl} />}
          {format === 'txt' && <TextViewer url={previewUrl} />}
          {format === 'html' && <HtmlViewer url={previewUrl} />}
        </div>
      </div>
    </div>
  );
}
