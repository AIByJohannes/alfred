"use client";

import { useState, useEffect } from "react";
import { aiClient, AIResponse } from "@/lib/api/ai";
import { backendClient, Job } from "@/lib/api/backend";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [token, setToken] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [history, setHistory] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load history if token exists
  useEffect(() => {
    if (token) {
      loadHistory();
    }
  }, [token]);

  const loadHistory = async () => {
    try {
      const data = await backendClient.getHistory(token);
      setHistory(data);
    } catch (err: any) {
      console.error("Failed to load history", err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await aiClient.runAgent(prompt, token);
      setResult(response.result);
      // Refresh history after a new job is created
      if (token) loadHistory();
    } catch (err: any) {
      setError(err.message || "Failed to execute AI agent");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen p-8 font-sans">
      <main className="max-w-4xl mx-auto space-y-12">
        <header>
          <h1 className="text-4xl font-bold tracking-tight">Alfred</h1>
          <p className="text-zinc-500 mt-2">Polyglot AI Task Orchestrator</p>
        </header>

        {/* Auth Section (Simulated for now) */}
        <section className="bg-zinc-50 p-6 rounded-xl border border-zinc-200">
          <h2 className="text-lg font-semibold mb-4">Authentication</h2>
          <div className="flex flex-col gap-2">
            <label className="text-sm text-zinc-600">JWT Token (Manual for testing):</label>
            <input
              type="text"
              className="p-2 border rounded bg-white w-full font-mono text-xs"
              placeholder="Paste your JWT here..."
              value={token}
              onChange={(e) => setToken(e.target.value)}
            />
          </div>
        </section>

        {/* AI Execution Section */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold">Execute AI Agent</h2>
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              className="flex-1 p-3 border rounded-lg focus:ring-2 focus:ring-black outline-none"
              placeholder="Ask Alfred anything..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-black text-white px-6 py-3 rounded-lg font-medium hover:bg-zinc-800 disabled:bg-zinc-400 transition-colors"
            >
              {loading ? "Running..." : "Run"}
            </button>
          </form>

          {error && (
            <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-100">
              {error}
            </div>
          )}

          {result && (
            <div className="p-6 bg-zinc-900 text-zinc-100 rounded-xl shadow-inner">
              <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-500 mb-2">Result</h3>
              <pre className="whitespace-pre-wrap font-mono text-sm">{result}</pre>
            </div>
          )}
        </section>

        {/* History Section */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold">Recent Jobs</h2>
          {!token ? (
            <p className="text-zinc-500 italic">Provide a JWT token to view history from Spring Boot.</p>
          ) : history.length === 0 ? (
            <p className="text-zinc-500 italic">No jobs found in history.</p>
          ) : (
            <div className="grid gap-4">
              {history.map((job) => (
                <div key={job.id} className="p-4 border rounded-lg hover:bg-zinc-50 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-medium text-sm text-zinc-600">{job.prompt}</span>
                    <span className="text-[10px] font-mono bg-zinc-100 px-2 py-1 rounded text-zinc-500 uppercase">
                      {job.status}
                    </span>
                  </div>
                  <p className="text-sm line-clamp-2 text-zinc-400 font-mono italic">
                    {job.result}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}