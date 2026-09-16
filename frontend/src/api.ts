import type { FolderBrowseResponse, Format } from './types';

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

export function normalizeCodes(input: string): string[] {
  const seen = new Set<string>();
  return input
    .split(/[\n,;\t ]+/)
    .map((x) => x.trim())
    .filter(Boolean)
    .filter((x) => {
      if (seen.has(x)) return false;
      seen.add(x);
      return true;
    });
}

export async function searchFiles(format: Format, codes: string[], folderPath?: string) {
  return api('/api/peek/search', {
    method: 'POST',
    body: JSON.stringify({ format, codes, folder_path: folderPath || null })
  });
}

export async function browseFolder(path?: string) {
  const query = path ? `?path=${encodeURIComponent(path)}` : '';
  return api<FolderBrowseResponse>(`/api/folders/browse${query}`);
}
