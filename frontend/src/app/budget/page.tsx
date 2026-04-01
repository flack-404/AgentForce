"use client";
import { useState, useEffect } from "react";
import { getBudget } from "@/lib/api";

interface BudgetAgent {
  budget_limit: number;
  budget_used: number;
  budget_remaining: number;
  budget_pct: number;
}

interface BudgetData {
  total_budget: number;
  total_used: number;
  agents: Record<string, BudgetAgent>;
}

const COLORS: Record<string, { bar: string; tag: string; tagBg: string; tagBorder: string }> = {
  planner: { bar: "#8b5cf6", tag: "text-violet-700", tagBg: "bg-violet-50", tagBorder: "border-violet-200" },
  developer: { bar: "#3b82f6", tag: "text-blue-700", tagBg: "bg-blue-50", tagBorder: "border-blue-200" },
  qa: { bar: "#10b981", tag: "text-emerald-700", tagBg: "bg-emerald-50", tagBorder: "border-emerald-200" },
  deployer: { bar: "#f59e0b", tag: "text-amber-700", tagBg: "bg-amber-50", tagBorder: "border-amber-200" },
};

export default function BudgetPage() {
  const [budget, setBudget] = useState<BudgetData | null>(null);

  useEffect(() => {
    getBudget().then((d) => setBudget(d as BudgetData)).catch(() => {});
    const interval = setInterval(() => {
      getBudget().then((d) => setBudget(d as BudgetData)).catch(() => {});
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const totalPct = budget ? (budget.total_used / budget.total_budget * 100) : 0;

  return (
    <div className="space-y-10">
      <div>
        <h1 className="font-display text-[40px] leading-tight text-[#111]">Compute Budget</h1>
        <p className="text-[14px] text-[#888] mt-1">Real-time spending and budget enforcement</p>
      </div>

      {/* Total Budget */}
      <div className="rounded-2xl border-[1.5px] border-[#e8e8e8] bg-white p-7">
        <div className="flex justify-between items-end mb-5">
          <div>
            <div className="text-[13px] text-[#888]">Total Budget Utilization</div>
            <div className="text-[42px] font-bold text-[#111] leading-tight">${budget?.total_used?.toFixed(4) || "0.0000"}</div>
          </div>
          <div className="text-right">
            <div className="text-[13px] text-[#888]">of ${budget?.total_budget || 50}.00</div>
            <div className={`text-[28px] font-bold leading-tight ${totalPct > 80 ? "text-red-500" : totalPct > 50 ? "text-amber-500" : "text-emerald-600"}`}>
              {totalPct.toFixed(1)}%
            </div>
          </div>
        </div>
        <div className="h-3 bg-[#f0f0f0] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(totalPct, 100)}%`,
              backgroundColor: totalPct > 80 ? "#ef4444" : totalPct > 50 ? "#f59e0b" : "#10b981"
            }}
          />
        </div>
        <div className="flex justify-between mt-2.5 text-[11px] text-[#bbb]">
          <span>$0</span>
          <span className="text-amber-500">Warning: $40</span>
          <span className="text-red-500">Hard Stop: $50</span>
        </div>
      </div>

      {/* Per-Agent Breakdown */}
      <div className="grid grid-cols-2 gap-5">
        {Object.entries(budget?.agents || {}).map(([role, agent]) => {
          const c = COLORS[role] || COLORS.planner;
          return (
            <div key={role} className="rounded-2xl border-[1.5px] border-[#e8e8e8] bg-white p-6 transition-all hover:-translate-y-0.5 hover:shadow-[0_4px_20px_rgba(0,0,0,0.06)]">
              <div className="flex justify-between items-center mb-4">
                <h3 className={`font-semibold text-[15px] capitalize ${c.tag}`}>{role}</h3>
                <span className={`text-[11px] px-2.5 py-0.5 rounded-full border ${c.tagBorder} ${c.tagBg} ${c.tag} font-medium`}>
                  {agent.budget_pct.toFixed(1)}%
                </span>
              </div>
              <div className="text-[28px] font-bold text-[#111] mb-1">${agent.budget_used.toFixed(4)}</div>
              <div className="text-[12px] text-[#aaa] mb-4">of ${agent.budget_limit.toFixed(2)} limit</div>
              <div className="h-2 bg-[#f0f0f0] rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(agent.budget_pct, 100)}%`, backgroundColor: c.bar }} />
              </div>
              <div className="text-[12px] text-[#bbb] mt-2.5">
                ${agent.budget_remaining.toFixed(4)} remaining
              </div>
            </div>
          );
        })}
      </div>

      {!budget?.agents || Object.keys(budget.agents).length === 0 ? (
        <div className="text-center py-10 text-[#ccc] text-[14px]">
          Budget tracking starts when you launch a challenge.
        </div>
      ) : null}
    </div>
  );
}
