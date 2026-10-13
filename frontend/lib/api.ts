/**
 * DriveLens AI - Frontend API Client
 * Interfaces with FastAPI backend. Strictly avoids exposing any tokens or secrets.
 */

// In unified single-link mode, relative paths "/api/..." route directly to the current origin
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export interface AuthStatus {
  is_authenticated: boolean;
  user_email?: string | null;
  user_name?: string | null;
  scope?: string | null;
  read_only_enforced: boolean;
}

export interface DocumentMetadata {
  id: string;
  name: string;
  mime_type: string;
  modified_time: string;
  size_bytes?: number | null;
  is_supported: boolean;
  unsupported_reason?: string | null;
  web_view_link?: string | null;
}

export interface AnalysisResponse {
  document_id: string;
  document_title: string;
  mime_type: string;
  last_modified: string;
  key_facts: string[];
  one_line_summary: string;
  source_evidence: string[];
  limitations: string[];
  read_only_notice: string;
}

export interface RevokeResponse {
  status: string;
  message: string;
}

export async function fetchAuthStatus(): Promise<AuthStatus> {
  const res = await fetch(`${API_BASE}/api/auth/status`, {
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch auth status: ${res.statusText}`);
  }
  return res.json();
}

export function getGoogleLoginUrl(): string {
  return `${API_BASE}/api/auth/login`;
}

export async function disconnectDrive(): Promise<RevokeResponse> {
  const res = await fetch(`${API_BASE}/api/auth/disconnect`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(`Failed to disconnect: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRecentDocuments(): Promise<DocumentMetadata[]> {
  const res = await fetch(`${API_BASE}/api/drive/recent`, {
    credentials: "include",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || "Failed to retrieve documents");
  }
  return res.json();
}

export async function analyzeDocument(documentId?: string): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE}/api/drive/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify({ document_id: documentId || null }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `Analysis failed (${res.status})`);
  }
  return res.json();
}
