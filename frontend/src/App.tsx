import { useEffect, useRef, useState } from "react";
import { streamWorkbenchRun, type StreamPayload } from "./lib/stream";

type Mode = "inference" | "fs-agent";
type BackendOption = "auto" | "alfred-cli" | "smolagents";

type Artifact = {
  label: string;
  path?: string;
  url?: string;
};

type Status = "idle" | "running" | "done" | "error";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: Status;
};

const modeLabels: Record<Mode, { title: string; subtitle: string }> = {
  inference: {
    title: "Inference",
    subtitle: "Python inference only. No filesystem meddling.",
  },
  "fs-agent": {
    title: "Filesystem Agent",
    subtitle: "Delegates to the Rust `alfred` binary.",
  },
};

function readText(data: unknown): string {
  if (typeof data === "string") return data;
  if (data && typeof data === "object") {
    const candidate = data as Record<string, unknown>;
    const value = candidate.text ?? candidate.delta ?? candidate.message ?? candidate.content;
    if (typeof value === "string") return value;
  }
  return "";
}

function readArtifact(data: unknown): Artifact | null {
  if (!data || typeof data !== "object") return null;
  const candidate = data as Record<string, unknown>;
  const label = typeof candidate.label === "string" ? candidate.label : typeof candidate.name === "string" ? candidate.name : typeof candidate.path === "string" ? candidate.path : "artifact";
  return {
    label,
    path: typeof candidate.path === "string" ? candidate.path : undefined,
    url: typeof candidate.url === "string" ? candidate.url : undefined,
  };
}

function readBackend(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;
  const candidate = data as Record<string, unknown>;
  return typeof candidate.backend === "string" ? candidate.backend : null;
}

function readSessionId(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;
  const candidate = data as Record<string, unknown>;
  const sessionId = candidate.session_id ?? candidate.sessionId;
  return typeof sessionId === "string" ? sessionId : null;
}

export default function App() {
  const [mode, setMode] = useState<Mode>("inference");
  const [prompt, setPrompt] = useState("");
  const [cwd, setCwd] = useState("");
  const [fsBackend, setFsBackend] = useState<BackendOption>("auto");
  const [resolvedBackend, setResolvedBackend] = useState<string | null>(null);
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [statusDetail, setStatusDetail] = useState("Standing by.");
  
  const chatListRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (chatListRef.current) {
      chatListRef.current.scrollTop = chatListRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  async function handleRun() {
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const userMessageId = Math.random().toString(36).slice(2);
    const assistantMessageId = Math.random().toString(36).slice(2);

    setMessages((prev) => [
      ...prev,
      { id: userMessageId, role: "user", content: trimmedPrompt },
      { id: assistantMessageId, role: "assistant", content: "", status: "running" }
    ]);
    
    setPrompt("");
    setStatus("running");
    setStatusDetail("Streaming response...");
    setResolvedBackend(null);

    const path = mode === "inference" ? "/api/infer/stream" : "/api/fs-agent/stream";
    const body = mode === "inference" 
      ? { prompt: trimmedPrompt }
      : { prompt: trimmedPrompt, cwd: cwd.trim() || undefined, backend: fsBackend };

    try {
      await streamWorkbenchRun(path, body, controller.signal, (payload: StreamPayload) => {
        if (payload.type === "meta") {
          const maybeSessionId = readSessionId(payload.data);
          if (maybeSessionId) setSessionId(maybeSessionId);
          const backend = readBackend(payload.data);
          if (backend) setResolvedBackend(backend);
          setStatusDetail("Run initialized.");
        }

        if (payload.type === "delta") {
          const text = readText(payload.data);
          if (text) {
            setMessages((prev) => prev.map(msg => 
              msg.id === assistantMessageId 
                ? { ...msg, content: msg.content + text } 
                : msg
            ));
          }
        }

        if (payload.type === "artifact") {
          const artifact = readArtifact(payload.data);
          if (artifact) setArtifacts((current) => [...current, artifact]);
        }

        if (payload.type === "done") {
          const message = readText(payload.data);
          setStatus("done");
          setStatusDetail(message || "Run complete.");
          setMessages((prev) => prev.map(msg => 
            msg.id === assistantMessageId ? { ...msg, status: "done" } : msg
          ));
        }

        if (payload.type === "error") {
          const message = readText(payload.data) || "The run failed.";
          setStatus("error");
          setStatusDetail(message);
          setMessages((prev) => prev.map(msg => 
            msg.id === assistantMessageId ? { ...msg, status: "error" } : msg
          ));
        }
      });

      setStatus((current) => (current === "running" ? "done" : current));
      setStatusDetail((current) => current === "Streaming response..." ? "Run complete." : current);
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        setStatus("idle");
        setStatusDetail("Run cancelled.");
        return;
      }
      const message = error instanceof Error ? error.message : "Request failed.";
      setStatus("error");
      setStatusDetail(message);
      setMessages((prev) => prev.map(msg => 
        msg.id === assistantMessageId ? { ...msg, status: "error", content: msg.content + "\n\nError: " + message } : msg
      ));
    }
  }

  function handleClear() {
    abortRef.current?.abort();
    setPrompt("");
    setMessages([]);
    setArtifacts([]);
    setSessionId(null);
    setStatus("idle");
    setStatusDetail("Workbench cleared.");
    setResolvedBackend(null);
  }

  const isRunning = status === "running";

  return (
    <div className="app-container">
      <aside className="sidebar">
        <h1>A.L.F.R.E.D.</h1>

        <div className="sidebar-section">
          <h2>Execution Mode</h2>
          <div className="mode-switch" role="tablist">
            <button
              type="button"
              className={mode === "inference" ? "mode-switch__item is-active" : "mode-switch__item"}
              onClick={() => setMode("inference")}
            >
              Inference
            </button>
            <button
              type="button"
              className={mode === "fs-agent" ? "mode-switch__item is-active" : "mode-switch__item"}
              onClick={() => setMode("fs-agent")}
            >
              Filesystem Agent
            </button>
          </div>
          {resolvedBackend ? (
            <p style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.5rem' }}>
              Backend: {resolvedBackend}
            </p>
          ) : null}
        </div>

        {mode === "fs-agent" && (
          <div className="sidebar-section">
            <h2>Agent Settings</h2>
            <label className="field">
              <span className="field__label">Working Directory</span>
              <input
                value={cwd}
                onChange={(event) => setCwd(event.target.value)}
                placeholder="/path/to/repo"
                type="text"
              />
            </label>
            <label className="field">
              <span className="field__label">Backend Fallback</span>
              <select value={fsBackend} onChange={(event) => setFsBackend(event.target.value as BackendOption)}>
                <option value="auto">Auto</option>
                <option value="alfred-cli">Alfred CLI</option>
                <option value="smolagents">Smolagents</option>
              </select>
            </label>
          </div>
        )}

        <div className="sidebar-section" style={{ flex: 1, overflowY: 'auto' }}>
          <h2>Session</h2>
          {sessionId && <div className="session-chip">{sessionId}</div>}
          
          {artifacts.length > 0 && (
            <ul className="artifact-list">
              {artifacts.map((artifact, index) => (
                <li key={`${artifact.label}-${index}`} className="artifact-list__item">
                  <span>{artifact.label}</span>
                  <small>{artifact.path ?? artifact.url ?? "pending"}</small>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="status-indicator">
          <div className={`status-dot ${status}`} />
          {statusDetail}
        </div>
      </aside>

      <main className="main-chat">
        <div className="chat-list" ref={chatListRef}>
          <div className="chat-list-inner">
            {messages.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--muted)', marginTop: '4rem' }}>
                <h2>Thin bridge. Sharp edges. No illusions.</h2>
                <p>Send a message to begin.</p>
              </div>
            ) : (
              messages.map(msg => (
                <div key={msg.id} className={`message ${msg.role} ${msg.status || ''}`}>
                  <div className="message-avatar">
                    {msg.role === "assistant" ? "A" : "U"}
                  </div>
                  <div className={`message-content ${msg.role}`}>
                    {msg.content}
                    {msg.status === "running" && <span style={{ opacity: 0.5 }}>...</span>}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="chat-input-container">
          <div className="chat-input-wrapper">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleRun();
                }
              }}
              placeholder="Message Alfred..."
              rows={1}
            />
            <div className="chat-input-actions">
              <button 
                type="button" 
                className="button button--ghost" 
                onClick={handleClear}
                style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
              >
                Clear
              </button>
              <button 
                type="button" 
                className="button button--primary" 
                onClick={handleRun} 
                disabled={isRunning || !prompt.trim()}
              >
                {isRunning ? "Running" : "Send"}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}