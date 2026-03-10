import { useEffect, useRef, useState } from "react";

import { streamWorkbenchRun, type StreamPayload } from "./lib/stream";

type Mode = "inference" | "fs-agent";

type Artifact = {
  label: string;
  path?: string;
  url?: string;
};

type Status = "idle" | "running" | "done" | "error";

const modeLabels: Record<Mode, { title: string; subtitle: string }> = {
  inference: {
    title: "Inference",
    subtitle: "Python inference only. No filesystem meddling. Civilized, mostly.",
  },
  "fs-agent": {
    title: "Filesystem Agent",
    subtitle: "Delegates to the Rust `alfred` binary for repo-aware execution.",
  },
};

function readText(data: unknown): string {
  if (typeof data === "string") {
    return data;
  }

  if (data && typeof data === "object") {
    const candidate = data as Record<string, unknown>;
    const value = candidate.text ?? candidate.delta ?? candidate.message ?? candidate.content;
    if (typeof value === "string") {
      return value;
    }
  }

  return "";
}

function readArtifact(data: unknown): Artifact | null {
  if (!data || typeof data !== "object") {
    return null;
  }

  const candidate = data as Record<string, unknown>;
  const label =
    typeof candidate.label === "string"
      ? candidate.label
      : typeof candidate.name === "string"
        ? candidate.name
        : typeof candidate.path === "string"
          ? candidate.path
          : "artifact";

  return {
    label,
    path: typeof candidate.path === "string" ? candidate.path : undefined,
    url: typeof candidate.url === "string" ? candidate.url : undefined,
  };
}

function readSessionId(data: unknown): string | null {
  if (!data || typeof data !== "object") {
    return null;
  }

  const candidate = data as Record<string, unknown>;
  const sessionId = candidate.session_id ?? candidate.sessionId;
  return typeof sessionId === "string" ? sessionId : null;
}

export default function App() {
  const [mode, setMode] = useState<Mode>("inference");
  const [prompt, setPrompt] = useState("");
  const [cwd, setCwd] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [statusDetail, setStatusDetail] = useState("Standing by.");
  const [output, setOutput] = useState("");
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const outputRef = useRef<HTMLPreElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const outputNode = outputRef.current;
    if (outputNode) {
      outputNode.scrollTop = outputNode.scrollHeight;
    }
  }, [output]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  async function handleRun() {
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt) {
      setStatus("error");
      setStatusDetail("A prompt helps. Telepathy remains underfunded.");
      setErrorMessage("Prompt is required.");
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setStatus("running");
    setStatusDetail("Streaming response...");
    setOutput("");
    setArtifacts([]);
    setSessionId(null);
    setErrorMessage(null);

    const path = mode === "inference" ? "/api/infer/stream" : "/api/fs-agent/stream";
    const body =
      mode === "inference"
        ? { prompt: trimmedPrompt }
        : { prompt: trimmedPrompt, cwd: cwd.trim() || undefined };

    try {
      await streamWorkbenchRun(path, body, controller.signal, (payload: StreamPayload) => {
        if (payload.type === "meta") {
          const maybeSessionId = readSessionId(payload.data);
          if (maybeSessionId) {
            setSessionId(maybeSessionId);
          }
          setStatusDetail("Run initialized.");
          return;
        }

        if (payload.type === "delta") {
          const text = readText(payload.data);
          if (text) {
            setOutput((current) => current + text);
          }
          return;
        }

        if (payload.type === "artifact") {
          const artifact = readArtifact(payload.data);
          if (artifact) {
            setArtifacts((current) => [...current, artifact]);
          }
          return;
        }

        if (payload.type === "done") {
          const message = readText(payload.data);
          setStatus("done");
          setStatusDetail(message || "Run complete.");
          return;
        }

        if (payload.type === "error") {
          const message = readText(payload.data) || "The run failed.";
          setStatus("error");
          setStatusDetail(message);
          setErrorMessage(message);
        }
      });

      setStatus((current) => (current === "running" ? "done" : current));
      setStatusDetail((current) =>
        current === "Streaming response..." ? "Run complete." : current,
      );
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        setStatus("idle");
        setStatusDetail("Run cancelled.");
        return;
      }

      const message = error instanceof Error ? error.message : "Request failed.";
      setStatus("error");
      setStatusDetail(message);
      setErrorMessage(message);
    }
  }

  function handleClear() {
    abortRef.current?.abort();
    setPrompt("");
    setCwd("");
    setOutput("");
    setArtifacts([]);
    setSessionId(null);
    setErrorMessage(null);
    setStatus("idle");
    setStatusDetail("Workbench cleared.");
  }

  const isRunning = status === "running";

  return (
    <div className="shell">
      <div className="shell__glow shell__glow--left" />
      <div className="shell__glow shell__glow--right" />

      <main className="workbench">
        <section className="hero">
          <div>
            <p className="eyebrow">A.L.F.R.E.D. Workbench</p>
            <h1>Thin bridge. Sharp edges. No illusions.</h1>
          </div>
          <div className={`status-pill status-pill--${status}`}>
            <span className="status-pill__dot" />
            {statusDetail}
          </div>
        </section>

        <section className="panel panel--controls">
          <div className="panel__header">
            <div>
              <p className="panel__eyebrow">Execution Mode</p>
              <h2>{modeLabels[mode].title}</h2>
            </div>
            {sessionId ? <code className="session-chip">{sessionId}</code> : null}
          </div>

          <p className="panel__copy">{modeLabels[mode].subtitle}</p>

          <div className="mode-switch" role="tablist" aria-label="Execution mode">
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

          <label className="field">
            <span className="field__label">Prompt</span>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="Describe the task. Alfred will do its level best to appear inevitable."
              rows={8}
            />
          </label>

          {mode === "fs-agent" ? (
            <label className="field">
              <span className="field__label">Working Directory</span>
              <input
                value={cwd}
                onChange={(event) => setCwd(event.target.value)}
                placeholder="/path/to/repo"
                type="text"
              />
            </label>
          ) : null}

          <div className="actions">
            <button type="button" className="button button--primary" onClick={handleRun} disabled={isRunning}>
              {isRunning ? "Running..." : "Run"}
            </button>
            <button type="button" className="button button--ghost" onClick={handleClear}>
              Clear
            </button>
          </div>
        </section>

        <section className="grid">
          <article className="panel panel--stream">
            <div className="panel__header">
              <div>
                <p className="panel__eyebrow">Stream</p>
                <h2>Live Output</h2>
              </div>
            </div>
            <pre ref={outputRef} className="stream-output">
              {output || "No output yet. Silence is either composure or a bug."}
            </pre>
            {errorMessage ? <p className="error-callout">{errorMessage}</p> : null}
          </article>

          <article className="panel panel--artifacts">
            <div className="panel__header">
              <div>
                <p className="panel__eyebrow">Session</p>
                <h2>Artifacts</h2>
              </div>
            </div>
            {artifacts.length > 0 ? (
              <ul className="artifact-list">
                {artifacts.map((artifact, index) => (
                  <li key={`${artifact.label}-${index}`} className="artifact-list__item">
                    <span>{artifact.label}</span>
                    <small>{artifact.path ?? artifact.url ?? "pending"}</small>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="artifact-empty">
                Nothing tangible yet. Either the run has not produced artifacts, or entropy is ahead on points.
              </p>
            )}
          </article>
        </section>
      </main>
    </div>
  );
}

