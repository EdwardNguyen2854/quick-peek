export type FileFormat = 'step' | 'pdf' | 'dxf' | 'doc' | 'xls' | 'ppt' | 'md' | 'txt' | 'html';
export type Format = 'all' | FileFormat;
export type MatchType = 'exact' | 'exact_normalized' | 'token' | 'variant' | 'partial';

export type FileItem = {
  file_id: number;
  filename: string;
  extension: string;
  format: FileFormat;
  size_bytes: number;
  modified_at: number;
  preview_kind: 'pdf' | 'svg' | 'step' | 'unknown' | 'html' | 'txt' | 'md' | 'doc' | 'xls' | 'ppt';
  preview_ready: boolean;
  message?: string | null;
  preview_url: string;
  raw_url: string;
  match_type?: MatchType | null;
  match_reason?: string | null;
  revision?: string | null;
  folder_class?: string | null;
  full_path?: string | null;
};

export type SearchSuggestion = {
  file_id: number;
  filename: string;
  extension: string;
  distance: number;
  reason: string;
  revision?: string | null;
  folder_class?: string | null;
};

export type SearchResult = {
  code: string;
  normalized_code: string;
  status: 'found' | 'multiple_matches' | 'suggested' | 'not_found';
  matches_count: number;
  match_type?: MatchType | null;
  match_reason?: string | null;
  recommended_file?: FileItem | null;
  files: FileItem[];
  suggestions: SearchSuggestion[];
};

export type IndexRootState = {
  id?: number;
  root_path: string;
  status: 'idle' | 'indexing' | 'ready' | 'error' | string;
  last_started_at?: string | null;
  last_completed_at?: string | null;
  files_count: number;
  last_error?: string | null;
};

export type IndexState = {
  status: 'idle' | 'indexing' | 'ready' | 'error' | string;
  phase?: string | null;
  last_started_at?: string | null;
  last_completed_at?: string | null;
  files_count: number;
  roots_count: number;
  current_root?: string | null;
  files_indexed?: number;
  elapsed_seconds?: number;
  last_error?: string | null;
  roots?: IndexRootState[];
};

export type SearchResponse = {
  format: Format;
  codes_count: number;
  files_found: number;
  folder_path?: string | null;
  index: IndexState;
  results: SearchResult[];
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
