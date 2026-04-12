import { useEffect, useRef, useState } from "react";
import { streamWorkbenchRun, type StreamPayload } from "./lib/stream";
import { apiUrl } from "./lib/api";

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
  imageBase64?: string;
  status?: Status;
};

type SessionMeta = {
  id: string;
  prompt: string;
  mode: string;
  timestamp: string;
};

const modeLabels: Record<Mode, { title: string; subtitle: string }> = {
  inference: {
    title: "Chat",
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
    const value = candidate.text ?? candidate.delta ?? candidate.message ?? candidate.content ?? candidate.result;
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
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  
  const [pendingImage, setPendingImage] = useState<string | null>(null);
  const [showCamera, setShowCamera] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const cameraStreamRef = useRef<MediaStream | null>(null);

  const chatListRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  function stopCameraStream() {
    const stream = cameraStreamRef.current;
    if (!stream) return;
    stream.getTracks().forEach((track) => track.stop());
    cameraStreamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }

  async function handleOpenCamera() {
    try {
      stopCameraStream();
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
      cameraStreamRef.current = stream;
      setShowCamera(true);
    } catch (e) {
      console.error("Camera access denied:", e);
      setStatusDetail("Camera access denied.");
    }
  }

  async function handleCapture() {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.drawImage(video, 0, 0);
        const dataUrl = canvas.toDataURL("image/png");
        setPendingImage(dataUrl.slice(22)); // remove "data:image/png;base64,"
        handleCloseCamera();
      }
    }
  }

  function handleRetake() {
    handleOpenCamera();
  }

  function handleRemoveImage() {
    setPendingImage(null);
  }

  function handleCloseCamera() {
    stopCameraStream();
    setShowCamera(false);
  }

  async function fetchSessions() {
    try {
      const res = await fetch(apiUrl("/api/sessions"));
      const data = await res.json();
      setSessions(data);
    } catch (e) {
      console.error("Failed to fetch sessions:", e);
    }
  }

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    if (chatListRef.current) {
      chatListRef.current.scrollTop = chatListRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (showCamera && videoRef.current && cameraStreamRef.current) {
      videoRef.current.srcObject = cameraStreamRef.current;
    }
  }, [showCamera]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      stopCameraStream();
    };
  }, []);

  async function handleRun() {
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const userMessageId = Math.random().toString(36).slice(2);
    const assistantMessageId = Math.random().toString(36).slice(2);

    const userMessage: Message = { id: userMessageId, role: "user", content: trimmedPrompt };
    if (pendingImage && mode === "inference") {
      userMessage.imageBase64 = pendingImage;
    }
    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantMessageId, role: "assistant", content: "", status: "running" }
    ]);
    
    setPrompt("");
    setPendingImage(null);
    setStatus("running");
    setStatusDetail("Streaming response...");
    setResolvedBackend(null);

    const path = mode === "inference" ? "/api/infer/stream" : "/api/fs-agent/stream";
    const body = mode === "inference" 
      ? { prompt: trimmedPrompt, session_id: sessionId || undefined, image_base64: pendingImage || undefined }
      : { prompt: trimmedPrompt, cwd: cwd.trim() || undefined, backend: fsBackend, session_id: sessionId || undefined };

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
      fetchSessions();
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
      fetchSessions();
    }
  }

  function handleClear() {
    abortRef.current?.abort();
    setPrompt("");
    setPendingImage(null);
    handleCloseCamera();
    setMessages([]);
    setArtifacts([]);
    setSessionId(null);
    setStatus("idle");
    setStatusDetail("Workbench cleared.");
    setResolvedBackend(null);
  }

  async function handleNewChat() {
    abortRef.current?.abort();
    try {
      const res = await fetch(apiUrl("/api/sessions/new"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      if (!res.ok) throw new Error("Failed to reserve new session");
      const data = await res.json();
      setPrompt("");
      setMessages([]);
      setArtifacts([]);
      setSessionId(data.id);
      setStatus("idle");
      setStatusDetail("New chat ready.");
      setResolvedBackend(null);
      await fetchSessions();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Request failed.";
      setStatus("error");
      setStatusDetail(message);
    }
  }

  async function handleLoadSession(id: string) {
    if (isRunning) return;
    abortRef.current?.abort();
    handleClear();
    
    try {
      const res = await fetch(apiUrl(`/api/sessions/${id}`));
      if (!res.ok) throw new Error("Failed to load session");
      const data = await res.json();
      
      const userPrompt = data.meta.prompt || "Loaded session";
      const userMessage: Message = { 
        id: `user-${id}`, 
        role: "user", 
        content: userPrompt,
        imageBase64: data.image_base64 || undefined,
      };
      
      let assistantContent = "";
      let finalStatus: Status = "idle";
      const newArtifacts: Artifact[] = [];
      
      for (const ev of data.events) {
        if (ev.type === "delta") {
          const text = readText(ev.data);
          if (text) assistantContent += text;
        }
        if (ev.type === "artifact") {
          const artifact = readArtifact(ev.data);
          if (artifact) newArtifacts.push(artifact);
        }
        if (ev.type === "done") finalStatus = "done";
        if (ev.type === "error") finalStatus = "error";
      }
      
      const assistantMessage: Message = { 
        id: `assistant-${id}`, 
        role: "assistant", 
        content: assistantContent, 
        status: finalStatus === "idle" ? "done" : finalStatus 
      };
      
      setMessages([userMessage, assistantMessage]);
      setArtifacts(newArtifacts);
      setSessionId(id);
      setMode(data.meta.mode === "fs-agent" ? "fs-agent" : "inference");
      setStatus("idle");
      setStatusDetail("Session loaded.");
    } catch (error) {
      console.error(error);
      setStatus("error");
      setStatusDetail("Failed to load session.");
    }
  }

  const isRunning = status === "running";

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>A.L.F.R.E.D.</h1>
          <button 
            className="new-chat-button" 
            onClick={handleNewChat}
            title="New Chat"
            aria-label="New Chat"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
        </div>

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
          <h2>Current Session</h2>
          {sessionId && <div className="session-chip">{sessionId}</div>}
          
          {artifacts.length > 0 && (
            <ul className="artifact-list" style={{ marginBottom: '2rem' }}>
              {artifacts.map((artifact, index) => (
                <li key={`${artifact.label}-${index}`} className="artifact-list__item">
                  <span>{artifact.label}</span>
                  <small>{artifact.path ?? artifact.url ?? "pending"}</small>
                </li>
              ))}
            </ul>
          )}

          <h2>History</h2>
          <div className="history-list">
            {sessions.map(session => (
              <button 
                key={session.id} 
                className={`history-item ${sessionId === session.id ? 'is-active' : ''}`}
                onClick={() => handleLoadSession(session.id)}
              >
                <div className="history-item__prompt">{session.prompt || "Empty prompt"}</div>
                <div className="history-item__meta">
                  {session.mode} • {session.timestamp}
                </div>
              </button>
            ))}
          </div>
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
                    {msg.role === "user" && msg.imageBase64 && (
                      <img src={`data:image/png;base64,${msg.imageBase64}`} alt="Attached" className="message-image" />
                    )}
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
            <div className="chat-input-main">
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
              {pendingImage && (
                <div className="pending-image-preview">
                  <img src={`data:image/png;base64,${pendingImage}`} alt="Preview" />
                  <button type="button" onClick={handleRemoveImage} className="pending-image-remove" title="Remove">×</button>
                </div>
              )}
            </div>
            <div className="chat-input-actions">
              {mode === "inference" && (
                <button 
                  type="button" 
                  className="button button--ghost camera-button" 
                  onClick={handleOpenCamera}
                  title="Take a photo"
                  style={{ padding: '0.4rem 0.8rem' }}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                    <circle cx="12" cy="13" r="4"/>
                  </svg>
                </button>
              )}
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

        {showCamera && (
          <div className="camera-modal">
            <div className="camera-modal-content">
              <video ref={videoRef} autoPlay playsInline muted />
              <canvas ref={canvasRef} style={{ display: "none" }} />
              <div className="camera-modal-actions">
                <button type="button" className="button button--ghost" onClick={handleCloseCamera}>Cancel</button>
                <button type="button" className="button button--primary" onClick={handleCapture}>Capture</button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
