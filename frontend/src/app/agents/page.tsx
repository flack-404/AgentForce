"use client";
import { useState, useEffect } from "react";
import { getAgents } from "@/lib/api";

interface AgentDetail {
  agent_id: string;
  name: string;
  role: string;
  capabilities: string[];
  trust_score: number;
  reputation_score: number;
  tasks_completed: number;
  tasks_failed: number;
  budget_used: number;
  budget_limit: number;
  budget_remaining: number;
  tool_calls_count: number;
}

const ROLE_COLORS: Record<string, { accent: string; tag: string; tagBg: string; tagBorder: string }> = {
  planner: { accent: "#8b5cf6", tag: "text-violet-700", tagBg: "bg-violet-50", tagBorder: "border-violet-200" },
  developer: { accent: "#3b82f6", tag: "text-blue-700", tagBg: "bg-blue-50", tagBorder: "border-blue-200" },
  qa: { accent: "#10b981", tag: "text-emerald-700", tagBg: "bg-emerald-50", tagBorder: "border-emerald-200" },
  deployer: { accent: "#f59e0b", tag: "text-amber-700", tagBg: "bg-amber-50", tagBorder: "border-amber-200" },
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<Record<string, AgentDetail>>({});

  useEffect(() => {
    getAgents().then((d) => setAgents((d as { agents: Record<string, AgentDetail> }).agents || {})).catch(() => {});
    const interval = setInterval(() => {
      getAgents().then((d) => setAgents((d as { agents: Record<string, AgentDetail> }).agents || {})).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="font-display text-[40px] leading-tight text-[#111]">Agent Registry</h1>
        <p className="text-[14px] text-[#888] mt-1">ERC-8004 registered autonomous agents</p>
      </div>

      <div className="grid grid-cols-2 gap-5">
        {Object.entries(agents).map(([role, agent]) => {
          const c = ROLE_COLORS[role] || ROLE_COLORS.planner;
          return (
            <div key={role} className="rounded-2xl border-[1.5px] border-[#e8e8e8] bg-white p-7 transition-all hover:-translate-y-0.5 hover:shadow-[0_4px_20px_rgba(0,0,0,0.06)]">
              <div className="flex justify-between items-start mb-5">
                <div>
                  <h2 className="text-[18px] font-semibold text-[#111]">{agent.name}</h2>
                  <p className="text-[11px] text-[#bbb] font-mono mt-1">ID: {agent.agent_id.slice(0, 16)}...</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-[11px] font-semibold border ${c.tagBorder} ${c.tagBg} ${c.tag} capitalize`}>{role}</span>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-5">
                <div className="bg-[#fafafa] rounded-xl p-4 border border-[#f0f0f0]">
                  <div className="text-[24px] font-bold text-[#111]">{agent.trust_score}</div>
                  <div className="text-[11px] text-[#aaa]">Trust Score</div>
                </div>
                <div className="bg-[#fafafa] rounded-xl p-4 border border-[#f0f0f0]">
                  <div className="text-[24px] font-bold text-[#111]">{agent.reputation_score}</div>
                  <div className="text-[11px] text-[#aaa]">Reputation</div>
                </div>
              </div>

              <div className="space-y-2.5 mb-5">
                <div className="flex justify-between text-[13px]">
                  <span className="text-[#888]">Tasks</span>
                  <span className="text-[#333]">{agent.tasks_completed} done / {agent.tasks_failed} failed</span>
                </div>
                <div className="flex justify-between text-[13px]">
                  <span className="text-[#888]">Budget</span>
                  <span className="text-[#333]">${agent.budget_used.toFixed(4)} / ${agent.budget_limit}</span>
                </div>
                <div className="flex justify-between text-[13px]">
                  <span className="text-[#888]">Tool Calls</span>
                  <span className="text-[#333]">{agent.tool_calls_count}</span>
                </div>
              </div>

              <div>
                <div className="text-[11px] text-[#aaa] mb-2 uppercase tracking-wide">Capabilities</div>
                <div className="flex flex-wrap gap-1.5">
                  {agent.capabilities.map((c) => (
                    <span key={c} className="px-2.5 py-0.5 rounded-full text-[11px] bg-[#fafafa] border border-[#e8e8e8] text-[#666]">{c}</span>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {Object.keys(agents).length === 0 && (
        <div className="text-center py-20 text-[#ccc] text-[14px]">
          No agents registered yet. Run a challenge to initialize the swarm.
        </div>
      )}
    </div>
  );
}
