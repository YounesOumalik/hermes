/**
 * Wrapper fetch centralisé pour l'API AgentAI.
 *
 * Responsabilités :
 * - Injecte le `Authorization: Bearer <token>` depuis localStorage
 * - Gère le refresh automatique en cas de 401 (single-flight)
 * - Redirige vers /login si le refresh échoue
 * - Lance une erreur typée pour faciliter la gestion côté composant
 *
 * Usage :
 *   import { apiFetch, ApiError } from "@/lib/api";
 *
 *   try {
 *     const res = await apiFetch("/workspaces");
 *     if (!res.ok) throw new ApiError(res.status, await res.text());
 *     const workspaces = await res.json();
 *   } catch (e) {
 *     if (e instanceof ApiError) { ... }
 *   }
 */

const API_BASE = "/api";
const TOKEN_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// --- Single-flight refresh ------------------------------------------------
let refreshPromise: Promise<boolean> | null = null;

async function refreshToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise; // déjà en cours

  refreshPromise = (async () => {
    const refreshTokenValue = localStorage.getItem(REFRESH_KEY);
    if (!refreshTokenValue) return false;

    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshTokenValue }),
      });
      if (!res.ok) return false;

      const data = await res.json();
      if (!data.access_token) return false;

      localStorage.setItem(TOKEN_KEY, data.access_token);
      if (data.refresh_token) {
        localStorage.setItem(REFRESH_KEY, data.refresh_token);
      }
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export function clearSessionAndRedirect() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

// --- Main fetch wrapper ---------------------------------------------------
export interface ApiFetchOptions extends RequestInit {
  /** Skip auth header (for public endpoints like /auth/google). */
  skipAuth?: boolean;
  /** Skip automatic refresh retry on 401. */
  skipRefresh?: boolean;
}

export async function apiFetch(
  path: string,
  options: ApiFetchOptions = {}
): Promise<Response> {
  const { skipAuth = false, skipRefresh = false, headers, ...rest } = options;

  const token = skipAuth ? null : localStorage.getItem(TOKEN_KEY);

  const finalHeaders: Record<string, string> = {
    ...(headers as Record<string, string>),
  };
  if (token) {
    finalHeaders.Authorization = `Bearer ${token}`;
  }
  // Set Content-Type for POST/PUT/PATCH with body if not already set
  if (
    rest.body &&
    typeof rest.body === "string" &&
    !finalHeaders["Content-Type"]
  ) {
    finalHeaders["Content-Type"] = "application/json";
  }

  const url = path.startsWith("http") || path.startsWith(API_BASE)
    ? path
    : `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;

  const res = await fetch(url, { ...rest, headers: finalHeaders });

  // 401 → try refresh then retry once
  if (res.status === 401 && !skipAuth && !skipRefresh) {
    const refreshed = await refreshToken();
    if (refreshed) {
      const newToken = localStorage.getItem(TOKEN_KEY);
      if (newToken) {
        finalHeaders.Authorization = `Bearer ${newToken}`;
      }
      return fetch(url, { ...rest, headers: finalHeaders });
    }
    clearSessionAndRedirect();
    throw new ApiError(401, "Session expired");
  }

  return res;
}

/**
 * Helper pour GET + JSON parsing avec gestion d'erreur typée.
 */
export async function apiGet<T>(path: string): Promise<T> {
  const res = await apiFetch(path);
  if (!res.ok) {
    throw new ApiError(res.status, `GET ${path} failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

/**
 * Helper pour POST + JSON parsing avec gestion d'erreur typée.
 */
export async function apiPost<T>(
  path: string,
  body?: unknown
): Promise<T> {
  const res = await apiFetch(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let details: unknown;
    try { details = await res.json(); } catch { /* ignore */ }
    throw new ApiError(res.status, `POST ${path} failed (${res.status})`, details);
  }
  return res.json() as Promise<T>;
}

/**
 * Helper pour PATCH + JSON parsing avec gestion d'erreur typée.
 */
export async function apiPatch<T>(
  path: string,
  body: unknown
): Promise<T> {
  const res = await apiFetch(path, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new ApiError(res.status, `PATCH ${path} failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

/**
 * Helper pour DELETE.
 */
export async function apiDelete(path: string): Promise<void> {
  const res = await apiFetch(path, { method: "DELETE" });
  if (!res.ok) {
    throw new ApiError(res.status, `DELETE ${path} failed (${res.status})`);
  }
}

// --- Token management utilities ------------------------------------------
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken?: string): void {
  localStorage.setItem(TOKEN_KEY, accessToken);
  if (refreshToken) {
    localStorage.setItem(REFRESH_KEY, refreshToken);
  }
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}
