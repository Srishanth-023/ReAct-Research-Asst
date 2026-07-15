const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

export async function fetchPapers() {
  const resp = await fetch(`${API_BASE_URL}/papers`);
  if (!resp.ok) throw new Error("Failed to fetch papers list");
  return resp.json();
}

export async function fetchQueries() {
  const resp = await fetch(`${API_BASE_URL}/queries`);
  if (!resp.ok) throw new Error("Failed to fetch query history");
  return resp.json();
}

export async function fetchQueryDetails(queryId) {
  const resp = await fetch(`${API_BASE_URL}/queries/${queryId}`);
  if (!resp.ok) throw new Error("Failed to fetch query details");
  return resp.json();
}

export async function fetchPaperChunks(paperId) {
  const resp = await fetch(`${API_BASE_URL}/papers/${encodeURIComponent(paperId)}/chunks`);
  if (!resp.ok) throw new Error("Failed to fetch paper chunks");
  return resp.json();
}

/**
 * Stream a ReAct query using POST and ReadableStream reading
 * to parse Server-Sent Events (SSE) incrementally.
 */
export async function streamQuery({ query, mode, onEvent, onError, onClose }) {
  try {
    const response = await fetch(`${API_BASE_URL}/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, mode }),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errText || response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      // Keep incomplete trailing line inside buffer
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const jsonStr = line.substring(6).strip?.() || line.substring(6).trim();
          if (jsonStr) {
            try {
              const parsed = JSON.parse(jsonStr);
              onEvent(parsed);
            } catch (e) {
              console.warn("Failed to parse SSE line:", line, e);
            }
          }
        }
      }
    }

    if (onClose) onClose();
  } catch (err) {
    if (onError) onError(err);
  }
}
