"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { runChallenge, getStatus, getHistory, connectWebSocket } from "@/lib/api";

interface AgentInfo {
  name: string;
  role: string;
  trust_score: number;
  reputation_score: number;
  budget_used: number;
  budget_limit: number;
  tasks_completed: number;
  tasks_failed: number;
  tool_calls_count: number;
}

interface SwarmEvent {
  timestamp: number;
  agent: string;
  event_type: string;
  description: string;
}

interface GitHubIssue {
  title: string;
  body: string;
  html_url: string;
  labels: { name: string }[];
}

interface HistoryRun {
  session_id: string;
  outcome: string;
  total_cost_usd: number;
  started_at: number;
  ended_at: number;
}

const AGENT_TAGS: Record<string, { color: string; bg: string; border: string }> = {
  planner: { color: "text-violet-700", bg: "bg-violet-50", border: "border-violet-200" },
  developer: { color: "text-blue-700", bg: "bg-blue-50", border: "border-blue-200" },
  qa: { color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200" },
  deployer: { color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200" },
  orchestrator: { color: "text-gray-600", bg: "bg-gray-50", border: "border-gray-200" },
};

const AGENT_ICONS: Record<string, string> = {
  planner: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
  developer: "M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4",
  qa: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
  deployer: "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12",
};

export default function Dashboard() {
  const [status, setStatus] = useState<string>("idle");
  const [agents, setAgents] = useState<Record<string, AgentInfo>>({});
  const [events, setEvents] = useState<SwarmEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [discovering, setDiscovering] = useState(false);
  const [discoveredIssues, setDiscoveredIssues] = useState<GitHubIssue[]>([]);
  const [history, setHistory] = useState<HistoryRun[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [result, setResult] = useState<Record<string, any> | null>(null);
  const eventRef = useRef<HTMLDivElement>(null);

  const addEvent = useCallback((ev: SwarmEvent) => {
    setEvents((prev) => [...prev, ev]);
  }, []);

  useEffect(() => {
    getStatus().then((raw) => {
      const data = raw as Record<string, unknown>;
      setStatus(data.status as string || "idle");
      if (data.agents) setAgents(data.agents as Record<string, AgentInfo>);
    }).catch(() => {});

    getHistory().then((raw) => {
      const data = raw as { runs: HistoryRun[] };
      setHistory(data.runs || []);
    }).catch(() => {});

    const ws = connectWebSocket((msg: unknown) => {
      const m = msg as { type: string; data: SwarmEvent & Record<string, unknown> };
      if (m.type === "event") {
        addEvent(m.data as SwarmEvent);
      } else if (m.type === "state") {
        setStatus(m.data.status as string || "idle");
        if (m.data.agents) setAgents(m.data.agents as Record<string, AgentInfo>);
      }
    });

    return () => ws.close();
  }, [addEvent]);

  useEffect(() => {
    if (eventRef.current) {
      eventRef.current.scrollTop = eventRef.current.scrollHeight;
    }
  }, [events]);

  const discoverFromGitHub = async () => {
    setDiscovering(true);
    setDiscoveredIssues([]);
    try {
      const res = await fetch(
        "https://api.github.com/search/issues?q=label:%22good+first+issue%22+state:open+language:python&sort=created&order=desc&per_page=5",
        { headers: { Accept: "application/vnd.github.v3+json" } }
      );
      const data = await res.json();
      setDiscoveredIssues(
        (data.items || []).map((item: GitHubIssue) => ({
          title: item.title,
          body: (item.body || "").slice(0, 500),
          html_url: item.html_url,
          labels: item.labels || [],
        }))
      );
    } catch {
      setDiscoveredIssues([]);
    }
    setDiscovering(false);
  };

  const handleRun = async () => {
    if (!title.trim() || !description.trim()) return;
    setRunning(true);
    setEvents([]);
    setResult(null);
    try {
      const res = await runChallenge({ title, description }) as Record<string, unknown>;
      setResult(res);
      setStatus("completed");
      if (res.agents) setAgents(res.agents as Record<string, AgentInfo>);
      getHistory().then((raw) => {
        setHistory((raw as { runs: HistoryRun[] }).runs || []);
      }).catch(() => {});
    } catch (e) {
      setResult({ error: String(e) });
      setStatus("failed");
    }
    setRunning(false);
  };

  const statusDot = status === "running" ? "bg-emerald-500 animate-pulse-glow" :
    status === "completed" ? "bg-emerald-500" :
    status === "failed" ? "bg-red-400" : "bg-[#ccc]";

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-[40px] leading-tight text-[#111]">Agent Observatory</h1>
          <p className="text-[14px] text-[#888] mt-1">Real-time autonomous swarm monitoring</p>
        </div>
        <div className="flex items-center gap-2.5">
          <div className={`w-2.5 h-2.5 rounded-full ${statusDot}`} />
          <span className="text-[13px] font-medium text-[#666] capitalize">{status}</span>
        </div>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-4 gap-4">
        {["planner", "developer", "qa", "deployer"].map((role) => {
          const agent = agents[role];
          const tag = AGENT_TAGS[role];
          return (
            <div key={role} className="rounded-2xl border-[1.5px] border-[#e8e8e8] bg-white p-5 transition-all hover:-translate-y-0.5 hover:shadow-[0_4px_20px_rgba(0,0,0,0.06)]">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-[#111] flex items-center justify-center">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d={AGENT_ICONS[role]} />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-[15px] text-[#111] capitalize">{role}</h3>
                  <p className="text-[11px] text-[#aaa]">
                    Trust: {agent?.trust_score ?? "--"} | Rep: {agent?.reputation_score ?? "--"}
                  </p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-[12px] text-[#888]">
                  <span>Budget</span>
                  <span>{agent ? `$${agent.budget_used.toFixed(4)} / $${agent.budget_limit}` : "No data yet"}</span>
                </div>
                <div className="h-1.5 bg-[#f0f0f0] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${tag.bg.replace("bg-", "bg-")}`}
                    style={{
                      width: `${agent ? (agent.budget_used / agent.budget_limit * 100) : 0}%`,
                      backgroundColor: role === "planner" ? "#8b5cf6" : role === "developer" ? "#3b82f6" : role === "qa" ? "#10b981" : "#f59e0b"
                    }}
                  />
                </div>
                <div className="flex justify-between text-[11px] text-[#bbb]">
                  <span>{agent?.tasks_completed ?? 0} completed</span>
                  <span>{agent?.tool_calls_count ?? 0} calls</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Run Challenge + Event Feed */}
      <div className="grid grid-cols-2 gap-6">
        <div className="rounded-2xl border-[1.5px] border-[#e8e8e8] bg-white p-7">
          <h2 className="font-display text-[20px] text-[#111] mb-5">Launch Challenge</h2>

          {/* Discover from GitHub */}
          <button onClick={discoverFromGitHub} disabled={discovering}
            className="w-full mb-4 py-2.5 border-[1.5px] border-[#e0e0e0] text-[#666] text-[13px] font-medium rounded-full transition-all hover:border-[#111] hover:text-[#111] flex items-center justify-center gap-2">
            {discovering ? (
              <><svg className="animate-spin h-3 w-3" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg> Discovering...</>
            ) : (
              <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.009-.866-.013-1.7-2.782.603-3.369-1.341-3.369-1.341-.454-1.155-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.268 2.75 1.026A9.578 9.578 0 0112 6.836a9.59 9.59 0 012.504.337c1.909-1.294 2.747-1.026 2.747-1.026.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.163 22 16.418 22 12c0-5.523-4.477-10-10-10z" /></svg> Discover from GitHub</>
            )}
          </button>

          {discoveredIssues.length > 0 && (
            <div className="space-y-2 mb-4 max-h-48 overflow-y-auto">
              {discoveredIssues.map((issue, i) => (
                <button key={i} onClick={() => { setTitle(issue.title); setDescription(issue.body); setDiscoveredIssues([]); }}
                  className="w-full text-left p-3 rounded-xl border-[1.5px] border-[#e8e8e8] bg-white hover:border-[#111] transition">
                  <div className="font-medium text-[13px] text-[#111] truncate">{issue.title}</div>
                  <div className="text-[12px] text-[#888] mt-1 line-clamp-2">{issue.body}</div>
                  <div className="flex gap-1 mt-1.5">
                    {issue.labels.slice(0, 3).map((l, j) => (
                      <span key={j} className="text-[10px] px-2 py-0.5 rounded-full border border-blue-200 bg-blue-50 text-blue-700">{l.name}</span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Custom input */}
          <div className="space-y-3 mb-5">
            <input value={title} onChange={(e) => setTitle(e.target.value)}
              placeholder="Challenge title..."
              className="w-full px-4 py-2.5 border-[1.5px] border-[#e8e8e8] rounded-xl text-[14px] text-[#111] placeholder-[#ccc] focus:border-[#111] focus:outline-none transition" />
            <textarea value={description} onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the challenge in detail..." rows={4}
              className="w-full px-4 py-2.5 border-[1.5px] border-[#e8e8e8] rounded-xl text-[14px] text-[#111] placeholder-[#ccc] focus:border-[#111] focus:outline-none resize-none transition" />
          </div>

          <button onClick={handleRun} disabled={running || !title.trim() || !description.trim()}
            className="w-full py-3 bg-[#111] hover:bg-[#333] disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium text-[14px] rounded-full transition flex items-center justify-center gap-2">
            {running ? (
              <><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg> Swarm Running...</>
            ) : "Launch Autonomous Swarm"}
          </button>

          {result && (
            <div className="mt-5 p-4 rounded-xl border-[1.5px] border-[#e8e8e8] bg-[#fafafa]">
              <div className="flex items-center gap-2 mb-1">
                <div className={`w-2 h-2 rounded-full ${result.outcome === "success" ? "bg-emerald-500" : result.error ? "bg-red-400" : "bg-amber-400"}`} />
                <span className="text-[13px] font-semibold text-[#111] capitalize">{result.error ? "Error" : String(result.outcome)}</span>
              </div>
              {result.error ? (
                <p className="text-[12px] text-red-500">{String(result.error).slice(0, 200)}</p>
              ) : (
                <>
                  <p className="text-[12px] text-[#888]">Cost: ${String(result.total_cost_usd)} | Events: {String(result.event_count)}</p>
                  {result.storage && (
                    <p className="text-[12px] text-blue-600 mt-1">
                      Filecoin CID: {String(result.storage?.execution_log?.cid || "").slice(0, 30)}...
                    </p>
                  )}
                  {result.onchain?.tx_hashes && (
                    <p className="text-[12px] text-emerald-600 mt-1">
                      {result.onchain.tx_hashes.length} on-chain transactions confirmed
                    </p>
                  )}
                </>
              )}
            </div>
          )}

          {/* Run History */}
          {history.length > 0 && (
            <div className="mt-5 border-t border-[#f0f0f0] pt-4">
              <h3 className="text-[11px] text-[#aaa] mb-2 font-medium uppercase tracking-wide">Run History</h3>
              <div className="space-y-1">
                {history.map((run) => (
                  <div key={run.session_id} className="flex items-center justify-between text-[12px] py-1.5">
                    <div className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${run.outcome === "success" ? "bg-emerald-500" : "bg-amber-400"}`} />
                      <span className="text-[#888] font-mono">{run.session_id.slice(0, 8)}</span>
                    </div>
                    <span className="text-[#bbb]">${run.total_cost_usd}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Live Event Feed */}
        <div className="rounded-2xl border-[1.5px] border-[#e8e8e8] bg-white p-7">
          <h2 className="font-display text-[20px] text-[#111] mb-5">Live Event Feed</h2>
          <div ref={eventRef} className="h-[500px] overflow-y-auto space-y-2 pr-2">
            {events.length === 0 ? (
              <div className="flex items-center justify-center h-full text-[#ccc] text-[14px]">
                Launch a challenge to see real-time events
              </div>
            ) : events.map((ev, i) => {
              const agentRole = ev.agent?.split("-").pop()?.toLowerCase() || "orchestrator";
              const tag = AGENT_TAGS[agentRole] || AGENT_TAGS.orchestrator;
              return (
                <div key={i} className="animate-slide-in flex gap-3 p-3 rounded-xl border border-[#f0f0f0] hover:border-[#e0e0e0] transition">
                  <div className="w-1 rounded-full flex-shrink-0" style={{
                    backgroundColor: agentRole === "planner" ? "#8b5cf6" : agentRole === "developer" ? "#3b82f6" : agentRole === "qa" ? "#10b981" : agentRole === "deployer" ? "#f59e0b" : "#999"
                  }} />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[12px] font-medium text-[#444]">{ev.agent}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border ${tag.border} ${tag.bg} ${tag.color}`}>{ev.event_type}</span>
                    </div>
                    <p className="text-[12px] text-[#888] mt-0.5 truncate">{ev.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
