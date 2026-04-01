"use client";
import { useState, useEffect } from "react";
import { getAgents } from "@/lib/api";

interface AgentTrust {
  name: string;
  role: string;
  trust_score: number;
  reputation_score: number;
  tasks_completed: number;
  tasks_failed: number;
  agent_id: string;
}

const NODE_COLORS = ["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b"];

export default function TrustPage() {
  const [agents, setAgents] = useState<Record<string, AgentTrust>>({});

  useEffect(() => {
    getAgents().then((d) => setAgents((d as { agents: Record<string, AgentTrust> }).agents || {})).catch(() => {});
    const interval = setInterval(() => {
      getAgents().then((d) => setAgents((d as { agents: Record<string, AgentTrust> }).agents || {})).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const agentList = Object.values(agents);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="font-display text-[40px] leading-tight text-[#111]">Trust Network</h1>
        <p className="text-[14px] text-[#888] mt-1">ERC-8004 trust scores and reputation graph</p>
      </div>

      {/* Trust Network Visualization */}
      <div className="rounded-2xl border-[1.5px] border-[#e8e8e8] bg-white p-8">
        <div className="relative h-80 flex items-center justify-center">
          {/* Central hub */}
          <div className="absolute w-16 h-16 rounded-full bg-[#111] flex items-center justify-center z-10 shadow-lg">
            <span className="text-[11px] font-bold text-white tracking-wide">SWARM</span>
          </div>

          {/* Agent nodes */}
          {agentList.map((agent, i) => {
            const angle = (i * 360) / agentList.length - 90;
            const rad = (angle * Math.PI) / 180;
            const x = Math.cos(rad) * 130;
            const y = Math.sin(rad) * 130;

            return (
              <div key={agent.role} className="absolute" style={{ transform: `translate(${x}px, ${y}px)` }}>
                <svg className="absolute" style={{ left: -x, top: -y, width: Math.abs(x) * 2 + 1, height: Math.abs(y) * 2 + 1, pointerEvents: "none" }}>
                  <line
                    x1={x > 0 ? 0 : Math.abs(x) * 2}
                    y1={y > 0 ? 0 : Math.abs(y) * 2}
                    x2={x > 0 ? Math.abs(x) * 2 : 0}
                    y2={y > 0 ? Math.abs(y) * 2 : 0}
                    stroke={agent.trust_score >= 60 ? "#10b981" : "#ef4444"}
                    strokeWidth="1.5"
                    strokeDasharray={agent.trust_score >= 60 ? "none" : "4 4"}
                    opacity="0.3"
                  />
                </svg>
                <div className="w-24 h-24 rounded-2xl border-[2px] bg-white flex flex-col items-center justify-center shadow-sm" style={{ borderColor: NODE_COLORS[i] }}>
                  <span className="text-[11px] font-semibold text-[#111] capitalize">{agent.role}</span>
                  <span className="text-[22px] font-bold text-[#111]">{agent.trust_score}</span>
                  <span className="text-[10px] text-[#bbb]">trust</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Trust Details Table */}
      <div className="rounded-2xl border-[1.5px] border-[#e8e8e8] bg-white overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#f0f0f0]">
              {["Agent", "Trust Score", "Reputation", "Success Rate", "ERC-8004 ID", "Status"].map((h) => (
                <th key={h} className="text-left text-[11px] text-[#aaa] p-4 uppercase tracking-wide font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {agentList.map((agent, i) => {
              const total = agent.tasks_completed + agent.tasks_failed;
              const rate = total > 0 ? Math.round((agent.tasks_completed / total) * 100) : 0;
              return (
                <tr key={agent.role} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] transition">
                  <td className="p-4">
                    <div className="font-medium text-[14px] text-[#111]">{agent.name}</div>
                    <div className="text-[11px] text-[#bbb] capitalize">{agent.role}</div>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-[#f0f0f0] rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{
                          width: `${agent.trust_score}%`,
                          backgroundColor: NODE_COLORS[i]
                        }} />
                      </div>
                      <span className="text-[13px] text-[#111] font-semibold">{agent.trust_score}</span>
                    </div>
                  </td>
                  <td className="p-4 text-[13px] text-[#333]">{agent.reputation_score}</td>
                  <td className="p-4 text-[13px] text-[#333]">{rate}%</td>
                  <td className="p-4 text-[11px] font-mono text-[#bbb]">{agent.agent_id.slice(0, 12)}...</td>
                  <td className="p-4">
                    <span className={`px-2.5 py-1 text-[11px] font-medium rounded-full border ${
                      agent.trust_score >= 60
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : "bg-red-50 text-red-700 border-red-200"
                    }`}>
                      {agent.trust_score >= 60 ? "Trusted" : "Untrusted"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {agentList.length === 0 && (
        <div className="text-center py-20 text-[#ccc] text-[14px]">
          No agents registered. Run a challenge to initialize trust scores.
        </div>
      )}
    </div>
  );
}
