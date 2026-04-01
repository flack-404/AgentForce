const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api";
const WS = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/api/ws";

export async function fetchAPI<T = unknown>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function runChallenge(challenge: {
  title: string;
  description: string;
  source?: string;
  type?: string;
}) {
  return fetchAPI("/run", {
    method: "POST",
    body: JSON.stringify(challenge),
  });
}

export function connectWebSocket(onEvent: (event: unknown) => void): WebSocket {
  const ws = new WebSocket(WS);
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent(data);
    } catch {
      // ignore parse errors
    }
  };
  return ws;
}

export async function getStatus() { return fetchAPI("/status"); }
export async function getAgents() { return fetchAPI("/agents"); }
export async function getAgent(role: string) { return fetchAPI(`/agents/${role}`); }
export async function getEvents() { return fetchAPI("/events"); }
export async function getTasks() { return fetchAPI("/tasks"); }
export async function getLogs() { return fetchAPI("/logs"); }
export async function getManifest() { return fetchAPI("/manifest"); }
export async function getBudget() { return fetchAPI("/budget"); }
export async function getStorage() { return fetchAPI("/storage"); }
export async function getHistory() { return fetchAPI("/history"); }
