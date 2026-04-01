"use client";
import { useState, useEffect } from "react";
import { getLogs } from "@/lib/api";

interface LogEvent {
  timestamp: string;
  agent: string;
  event_type: string;
  description: string;
  details: Record<string, unknown>;
}

interface AgentLog {
  session_id: string;
  started_at: string;
  ended_at: string;
  total_cost_usd: number;
  outcome: string;
  task_summary: string;
  events: LogEvent[];
}

export default function LogsPage() {
  const [log, setLog] = useState<AgentLog | null>(null);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    getLogs().then((d) => {
      if ((d as AgentLog).session_id) setLog(d as AgentLog);
    }).catch(() => {});
  }, []);

  const filteredEvents = log?.events?.filter((e) =>
    filter === "all" || e.agent.toLowerCase().includes(filter) || e.event_type === filter
  ) || [];

  return (
    <div className="space-y-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-[40px] leading-tight text-[#111]">Execution Logs</h1>
          <p className="text-[14px] text-[#888] mt-1">DevSpot-compatible structured execution log</p>
        </div>
        {log && (
          <button
            onClick={() => {
              const blob = new Blob([JSON.stringify(log, null, 2)], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = "agent_log.json";
              a.click();
            }}
            className="px-5 py-2.5 bg-[#111] hover:bg-[#333] text-white text-[13px] font-medium rounded-full transition"
          >
            Export agent_log.json
          </button>
        )}
      </div>

      {log && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Session", value: log.session_id.slice(0, 12) + "...", mono: true },
            { label: "Outcome", value: log.outcome, color: log.outcome === "completed" ? "text-emerald-600" : "text-amber-600" },
            { label: "Total Cost", value: `$${log.total_cost_usd}` },
            { label: "Events", value: String(log.events?.length || 0) },
          ].map((item) => (
            <div key={item.label} className="rounded-xl border border-[#e8e8e8] bg-[#fafafa] p-4">
              <div className="text-[11px] text-[#aaa] uppercase tracking-wide">{item.label}</div>
              <div className={`text-[14px] font-semibold mt-1 capitalize ${item.color || "text-[#111]"} ${item.mono ? "font-mono" : ""}`}>{item.value}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        {["all", "planner", "developer", "qa", "deployer", "decision", "tool_call", "review", "deployment"].map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3.5 py-1.5 rounded-full text-[12px] font-medium border transition ${
              filter === f
                ? "bg-[#111] text-white border-[#111]"
                : "bg-white text-[#888] border-[#e8e8e8] hover:border-[#111] hover:text-[#111]"
            }`}>
            {f}
          </button>
        ))}
      </div>

      <div className="space-y-1">
        {filteredEvents.map((ev, i) => (
          <div key={i} className="flex gap-4 p-3 rounded-xl border border-[#f0f0f0] hover:border-[#e0e0e0] transition text-[13px]">
            <div className="text-[11px] text-[#bbb] font-mono w-20 flex-shrink-0">
              {ev.timestamp.split("T")[1]?.replace(".000Z", "") || ev.timestamp}
            </div>
            <div className="w-36 flex-shrink-0">
              <span className="text-[12px] font-medium text-[#444]">{ev.agent}</span>
            </div>
            <div className="w-24 flex-shrink-0">
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#fafafa] border border-[#e8e8e8] text-[#888]">{ev.event_type}</span>
            </div>
            <div className="text-[#888] text-[12px] flex-1 truncate">{ev.description}</div>
          </div>
        ))}
      </div>

      {!log && (
        <div className="text-center py-20 text-[#ccc] text-[14px]">
          No execution logs yet. Run a challenge first.
        </div>
      )}
    </div>
  );
}
