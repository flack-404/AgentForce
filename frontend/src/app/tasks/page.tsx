"use client";
import { useState, useEffect } from "react";
import { getTasks } from "@/lib/api";

interface TaskInfo {
  task_id: string;
  title: string;
  description: string;
  status: string;
  assigned_to: string | null;
  subtasks: string[];
  review_count: number;
  has_artifacts: boolean;
}

const STATUS_STYLES: Record<string, { dot: string; tag: string; tagBg: string; tagBorder: string }> = {
  pending: { dot: "bg-[#ccc]", tag: "text-[#888]", tagBg: "bg-[#fafafa]", tagBorder: "border-[#e8e8e8]" },
  in_progress: { dot: "bg-blue-500 animate-pulse", tag: "text-blue-700", tagBg: "bg-blue-50", tagBorder: "border-blue-200" },
  review: { dot: "bg-amber-500", tag: "text-amber-700", tagBg: "bg-amber-50", tagBorder: "border-amber-200" },
  approved: { dot: "bg-emerald-500", tag: "text-emerald-700", tagBg: "bg-emerald-50", tagBorder: "border-emerald-200" },
  rejected: { dot: "bg-red-500", tag: "text-red-700", tagBg: "bg-red-50", tagBorder: "border-red-200" },
  deployed: { dot: "bg-blue-500", tag: "text-blue-700", tagBg: "bg-blue-50", tagBorder: "border-blue-200" },
  failed: { dot: "bg-red-500", tag: "text-red-700", tagBg: "bg-red-50", tagBorder: "border-red-200" },
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<Record<string, TaskInfo>>({});

  useEffect(() => {
    getTasks().then((d) => setTasks((d as { tasks: Record<string, TaskInfo> }).tasks || {})).catch(() => {});
    const interval = setInterval(() => {
      getTasks().then((d) => setTasks((d as { tasks: Record<string, TaskInfo> }).tasks || {})).catch(() => {});
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const taskList = Object.values(tasks);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="font-display text-[40px] leading-tight text-[#111]">Task Queue</h1>
        <p className="text-[14px] text-[#888] mt-1">Decomposed tasks and their execution status</p>
      </div>

      <div className="space-y-3">
        {taskList.map((task) => {
          const s = STATUS_STYLES[task.status] || STATUS_STYLES.pending;
          return (
            <div key={task.task_id} className="rounded-2xl border-[1.5px] border-[#e8e8e8] bg-white p-5 transition-all hover:-translate-y-0.5 hover:shadow-[0_4px_20px_rgba(0,0,0,0.06)]">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-[15px] text-[#111]">{task.title}</h3>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${s.dot}`} />
                  <span className={`text-[11px] px-2.5 py-0.5 rounded-full border ${s.tagBorder} ${s.tagBg} ${s.tag} font-medium capitalize`}>
                    {task.status.replace("_", " ")}
                  </span>
                </div>
              </div>
              <p className="text-[13px] text-[#888] mb-3 line-clamp-2">{task.description}</p>
              <div className="flex items-center gap-3 text-[12px] text-[#bbb]">
                {task.assigned_to && (
                  <span className="px-2 py-0.5 rounded-full bg-[#fafafa] border border-[#e8e8e8] text-[#666] capitalize">{task.assigned_to}</span>
                )}
                {task.review_count > 0 && <span>{task.review_count} reviews</span>}
                {task.has_artifacts && <span className="text-blue-600">Has artifacts</span>}
                {task.subtasks.length > 0 && <span>{task.subtasks.length} subtasks</span>}
                <span className="font-mono text-[#ccc]">{task.task_id.slice(0, 8)}</span>
              </div>
            </div>
          );
        })}
      </div>

      {taskList.length === 0 && (
        <div className="text-center py-20 text-[#ccc] text-[14px]">
          No tasks yet. Launch a challenge from the dashboard.
        </div>
      )}
    </div>
  );
}
