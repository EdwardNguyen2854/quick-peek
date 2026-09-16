export type Format = 'step' | 'pdf' | 'dxf' | 'doc' | 'xls' | 'ppt' | 'md' | 'txt' | 'html';

export type FileItem = {
  file_id: number;
  filename: string;
  extension: string;
  size_bytes: number;
  modified_at: number;
  preview_kind: 'pdf' | 'svg' | 'glb' | 'step' | 'unknown' | 'html' | 'txt' | 'md' | 'doc' | 'xls' | 'ppt';
  preview_ready: boolean;
  message?: string | null;
  preview_url: string;
  raw_url: string;
};

export type SearchResult = {
  code: string;
  status: 'found' | 'multiple_matches' | 'not_found';
  matches_count: number;
  files: FileItem[];
};

export type FolderItem = {
  name: string;
  path: string;
};

export type FolderBrowseResponse = {
  path: string;
  parent?: string | null;
  roots: string[];
  items: FolderItem[];
};
