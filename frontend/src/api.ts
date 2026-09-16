import type { FolderBrowseResponse, Format, IndexState, SearchResponse } from './types';

export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '');

export function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE}${path}`;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined)
  };
  const res = await fetch(apiUrl(path), { ...options, headers });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const err = await res.json();
      message = err.detail || JSON.stringify(err);
    } catch {}
    throw new Error(message);
  }
  return res.json();
}

function cleanCode(value: string) {
  let cleaned = value.trim().replace(/^["']|["']$/g, '');
  cleaned = cleaned.replace(/\.(?:stp|step|pdf|dxf|docx?|xlsx?|pptx?|md|txt|html?)$/i, '');
  if (/^\d+\.0$/.test(cleaned)) cleaned = cleaned.slice(0, -2);
  return cleaned.trim();
}

function codeKey(value: string) {
  return value.toUpperCase().replace(/[\s._-]+/g, '');
}

export function normalizeCodes(input: string): string[] {
  const values: string[] = [];

  for (const rawLine of input.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;

    if (line.includes('\t')) {
      const firstCell = cleanCode(line.split('\t', 1)[0]);
      if (firstCell) values.push(firstCell);
      continue;
    }

    const cells = line.split(/[;,]/);
    for (const cell of cells) {
      const value = cleanCode(cell);
      if (value) values.push(value);
    }
  }

  const seen = new Set<string>();
  return values.filter((value) => {
    const key = codeKey(value);
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export async function searchFiles(format: Format, codes: string[], folderPath?: string) {
  return api<SearchResponse>('/api/peek/search', {
    method: 'POST',
    body: JSON.stringify({ format, codes, folder_path: folderPath || null })
  });
}

export async function getIndexStatus() {
  return api<IndexState>('/api/index/status');
}

export async function refreshIndex(folderPath?: string) {
  return api<{ indexed: number; files_count: number; roots: number; folder_path?: string | null; index: IndexState }>('/api/index/refresh', {
    method: 'POST',
    body: JSON.stringify({ folder_path: folderPath || null })
  });
}

export async function browseFolder(path?: string) {
  const query = path ? `?path=${encodeURIComponent(path)}` : '';
  return api<FolderBrowseResponse>(`/api/folders/browse${query}`);
}
