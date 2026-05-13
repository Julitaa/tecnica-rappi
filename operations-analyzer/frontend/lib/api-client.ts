import type { ChatEvent } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function* streamChat(
  sessionId: string,
  message: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    buf = buf.replaceAll("\r\n", "\n").replaceAll("\r", "\n");
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      const payload = line.slice(6);
      try {
        yield JSON.parse(payload) as ChatEvent;
      } catch { /* ignore malformed */ }
    }
  }
}

export async function resetSession(sessionId: string): Promise<void> {
  await fetch(`${API}/chat/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function fetchReportMarkdown(): Promise<string> {
  const res = await fetch(`${API}/report?format=markdown`, { method: "POST" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.text();
}

export function reportPdfUrl(): string {
  return `${API}/report`;
}
