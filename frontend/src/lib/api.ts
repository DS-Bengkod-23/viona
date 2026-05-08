const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export interface TokenResponse {
  token: string;
  room: string;
  identity: string;
  livekit_url: string;
}

export interface SessionData {
  session_id: string;
  customer_phone?: string;
  customer_name?: string;
  status?: string;
  escalated?: boolean;
  complaints?: { ticket_id: string; description: string; category: string; status: string }[];
  history?: { role: string; text: string }[];
}

export interface IngestResult {
  filename?: string;
  source?: string;
  chunks: number;
  status: string;
}

export async function fetchToken(room?: string, identity?: string): Promise<TokenResponse> {
  const params = new URLSearchParams();
  if (room) params.set("room", room);
  if (identity) params.set("identity", identity);
  const res = await fetch(`${API_BASE}/api/token?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchSession(sessionId: string): Promise<SessionData> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchSessionHistory(sessionId: string): Promise<{ history: { role: string; text: string }[] }> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/history`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function ingestPDF(file: File, category = "faq"): Promise<IngestResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("category", category);
  const res = await fetch(`${API_BASE}/ingest/pdf`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function ingestText(text: string, source = "manual", category = "faq"): Promise<IngestResult> {
  const res = await fetch(`${API_BASE}/ingest/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, source, category }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
