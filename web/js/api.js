// JSON API client. Quest completions are queued in localStorage and retried until the server accepts them.
const QUEUE = "override:pending";

async function req(method, url, body) {
  const res = await fetch(url, {
    method, headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.detail || res.statusText), { status: res.status });
  return data;
}

export const api = {
  get: (u) => req("GET", u),
  post: (u, b) => req("POST", u, b || {}),
  put: (u, b) => req("PUT", u, b || {}),
};

const readQueue = () => { try { return JSON.parse(localStorage.getItem(QUEUE) || "[]"); } catch (_) { return []; } };
const writeQueue = (q) => localStorage.setItem(QUEUE, JSON.stringify(q));

export async function completeQuest(id, payload) {
  const q = readQueue().filter((x) => x.id !== id);
  q.push({ id, payload });
  writeQueue(q);
  for (let attempt = 0; attempt < 6; attempt++) {
    try {
      const report = await api.post(`/api/quests/${id}/complete`, payload);
      writeQueue(readQueue().filter((x) => x.id !== id));
      return report;
    } catch (e) {
      if (e.status && e.status < 500) { writeQueue(readQueue().filter((x) => x.id !== id)); throw e; }
      await new Promise((r) => setTimeout(r, Math.min(15000, 1000 * 2 ** attempt)));
    }
  }
  throw new Error("Serveur injoignable. La quête est gardée et sera renvoyée automatiquement.");
}

export async function flushQueue() {
  for (const item of readQueue()) {
    try {
      await api.post(`/api/quests/${item.id}/complete`, item.payload);
      writeQueue(readQueue().filter((x) => x.id !== item.id));
    } catch (e) {
      if (e.status && e.status < 500) writeQueue(readQueue().filter((x) => x.id !== item.id));
    }
  }
}
