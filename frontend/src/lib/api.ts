export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export function apiUrl(path: string): string {
  const base = API_BASE.endsWith("/") ? API_BASE.slice(0, -1) : API_BASE;
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${cleanPath}`;
}