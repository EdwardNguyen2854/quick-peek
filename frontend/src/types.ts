export type Permission =
  | 'use_quick_peek'
  | 'view_step'
  | 'view_pdf'
  | 'view_dxf'
  | 'view_obj'
  | 'view_dashboard'
  | 'manage_users'
  | 'download_files'
  | 'view_doc'
  | 'view_xls'
  | 'view_ppt'
  | 'view_md'
  | 'view_txt'
  | 'view_html';

export type User = {
  id: number;
  username: string;
  role: 'admin' | 'user';
  permissions: Permission[];
  is_active: boolean;
  last_login_at?: string | null;
};

export type Format = 'step' | 'pdf' | 'dxf' | 'obj' | 'doc' | 'xls' | 'ppt' | 'md' | 'txt' | 'html';

export type FileItem = {
  file_id: number;
  filename: string;
  extension: string;
  size_bytes: number;
  modified_at: number;
  preview_kind: 'pdf' | 'svg' | 'glb' | 'step' | 'obj' | 'unknown' | 'html' | 'txt' | 'md' | 'doc' | 'xls' | 'ppt';
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

export type FolderPreset = {
  id: number;
  name: string;
  path: string;
  created_at: string;
  updated_at: string;
};
