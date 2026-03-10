export type StreamEventType = "meta" | "delta" | "artifact" | "done" | "error";

export type StreamPayload = {
  type: StreamEventType;
  data: unknown;
};

function parseData(raw: string): unknown {
  const trimmed = raw.trim();
  if (!trimmed) {
    return "";
  }

  try {
    return JSON.parse(trimmed);
  } catch {
    return trimmed;
  }
}

function emitChunk(
  chunk: string,
  onEvent: (payload: StreamPayload) => void,
): void {
  const lines = chunk.replace(/\r\n/g, "\n").split("\n");
  let eventType: StreamEventType = "delta";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      const candidate = line.slice(6).trim();
      if (
        candidate === "meta" ||
        candidate === "delta" ||
        candidate === "artifact" ||
        candidate === "done" ||
        candidate === "error"
      ) {
        eventType = candidate;
      }
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  onEvent({
    type: eventType,
    data: parseData(dataLines.join("\n")),
  });
}

export async function streamWorkbenchRun(
  path: string,
  body: Record<string, unknown>,
  signal: AbortSignal,
  onEvent: (payload: StreamPayload) => void,
): Promise<void> {
  const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok || !response.body) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const messages = buffer.replace(/\r\n/g, "\n").split("\n\n");
    buffer = messages.pop() ?? "";

    for (const message of messages) {
      const trimmed = message.trim();
      if (trimmed) {
        emitChunk(trimmed, onEvent);
      }
    }
  }

  const tail = buffer.trim();
  if (tail) {
    emitChunk(tail, onEvent);
  }
}
