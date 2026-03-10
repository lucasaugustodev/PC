const BASE = "/api";
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  const token = localStorage.getItem("hiveclip.token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init?.body && typeof init.body === "string") headers.set("Content-Type", "application/json");
  const res = await fetch(`${BASE}${path}`, { headers, ...init });
  if (!res.ok) { const err = await res.json().catch(() => ({ error: res.statusText })); throw new Error(err.error || res.statusText); }
  if (res.status === 204) return undefined as T;
  return res.json();
}
export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
