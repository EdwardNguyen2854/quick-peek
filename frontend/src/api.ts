import type { FolderBrowseResponse, FolderPreset, Format } from './types';

const defaultApiBase = typeof window !== 'undefined' ? `http://${window.location.hostname}:5175` : 'http://127.0.0.1:5175';
export const API_BASE = import.meta.env.VITE_API_BASE ?? defaultApiBase;

export function getToken(): string | null {
  return localStorage.getItem('quickpeek_token');
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem('quickpeek_token', token);
  else localStorage.removeItem('quickpeek_token');
}

export function withToken(path: string): string {
  const token = getToken();
  const url = path.startsWith('http') ? new URL(path) : new URL(API_BASE + path);
  if (token) url.searchParams.set('access_token', token);
  return url.toString();
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined)
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(API_BASE + path, { ...options, headers });
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

export async function listFolderPresets() {
  return api<{ presets: FolderPreset[] }>('/api/folders/presets');
}

export async function saveFolderPreset(name: string, path: string) {
  return api<{ preset: FolderPreset }>('/api/folders/presets', {
    method: 'POST',
    body: JSON.stringify({ name, path })
  });
}

export async function deleteFolderPreset(id: number) {
  return api<{ ok: boolean }>(`/api/folders/presets/${id}`, { method: 'DELETE' });
}
