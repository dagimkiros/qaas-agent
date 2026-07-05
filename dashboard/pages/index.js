import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function Home() {
  const [url, setUrl] = useState("");
  const [runKey, setRunKey] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  async function startScan(e) {
    e.preventDefault();
    setLoading(true);
    const res = await fetch(`${API_BASE}/scans`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ site_url: url }),
    });
    const data = await res.json();
    setRunKey(data.run_key);
    pollStatus(data.run_key);
  }

  async function pollStatus(key) {
    const interval = setInterval(async () => {
      const res = await fetch(`${API_BASE}/scans/${key}`);
      const data = await res.json();
      setStatus(data);
      if (data.status === "completed" || data.status === "error") {
        clearInterval(interval);
        setLoading(false);
      }
    }, 3000);
  }

  return (
    <main style={{ maxWidth: 640, margin: "60px auto", fontFamily: "sans-serif" }}>
      <h1>QA-as-a-Service</h1>
      <p>Submit a URL to run a free QA scan.</p>

      <form onSubmit={startScan} style={{ display: "flex", gap: 8 }}>
        <input
          type="url"
          placeholder="https://yoursite.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
          style={{ flex: 1, padding: 8 }}
        />
        <button type="submit" disabled={loading} style={{ padding: "8px 16px" }}>
          {loading ? "Scanning..." : "Run Scan"}
        </button>
      </form>

      {status && (
        <div style={{ marginTop: 24 }}>
          <p>Status: <strong>{status.status}</strong></p>
          {status.summary && (
            <ul>
              <li>Total: {status.summary.total}</li>
              <li>Passed: {status.summary.passed}</li>
              <li>Self-healed: {status.summary.self_healed_count}</li>
            </ul>
          )}
          {status.status === "completed" && (
            <a href={`${API_BASE}/scans/${runKey}/report`} target="_blank" rel="noreferrer">
              View full report
            </a>
          )}
        </div>
      )}
    </main>
  );
}