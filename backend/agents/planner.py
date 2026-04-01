from __future__ import annotations
import json
import uuid
from typing import Any

from .base import BaseAgent, AgentMessage, AgentTask, TaskStatus


PLANNER_SYSTEM = """You are the Planner agent in AgentForge, an autonomous multi-agent swarm.
Your role is to analyze problems, decompose them into subtasks, and delegate to specialist agents.

You have access to these specialist agents:
- Developer: Writes code in Python, TypeScript, Solidity. Can create repos, branches, PRs.
- QA: Reviews code for bugs, security issues, quality. Writes and runs tests.
- Deployer: Deploys applications and smart contracts. Runs health checks.

When given a challenge/task, you must:
1. Analyze the requirements
2. Create a step-by-step plan
3. Decompose into subtasks for each agent
4. Estimate complexity and compute budget

ALWAYS respond in valid JSON with this structure:
{
  "analysis": "Brief analysis of the problem",
  "plan": ["Step 1", "Step 2", ...],
  "subtasks": [
    {
      "title": "Subtask title",
      "description": "What needs to be done",
      "assign_to": "developer|qa|deployer",
      "priority": 1,
      "estimated_tokens": 5000
    }
  ],
  "estimated_total_cost_usd": 0.5,
  "risk_assessment": "Low|Medium|High",
  "notes": "Any additional notes"
}"""


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="AgentForge-Planner",
            role="planner",
            capabilities=["problem_discovery", "task_decomposition", "strategic_planning", "coordination"],
        )

    def discover_task(self, challenge: dict[str, Any]) -> AgentTask:
        """Analyze a challenge and create a root task."""
        self.log_event("decision", f"Discovered challenge: {challenge.get('title', 'Unknown')}", {
            "source": challenge.get("source", "manual"),
            "challenge_type": challenge.get("type", "coding"),
        })

        task = AgentTask(
            task_id=str(uuid.uuid4()),
            title=challenge.get("title", "Unnamed Task"),
            description=challenge.get("description", ""),
            assigned_to=self.name,
            status=TaskStatus.IN_PROGRESS,
        )
        return task

    async def process(self, task: AgentTask, context: dict[str, Any]) -> AgentMessage:
        """Analyze and decompose a task."""
        self.log_event("decision", f"Planning task: {task.title}")

        prompt = f"""Analyze this challenge and create a detailed execution plan:

Title: {task.title}
Description: {task.description}

Available context: {json.dumps(context.get('extra', {}), default=str)[:500]}

Create a plan with subtasks for the Developer, QA, and Deployer agents.
The Developer should write the actual code solution.
The QA agent should review and test it.
The Deployer should prepare the final output.

Respond ONLY with valid JSON."""

        response_text, tool_call = self.llm_call(PLANNER_SYSTEM, prompt, temperature=0.3)

        # Parse the plan
        try:
            # Extract JSON from response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                plan = json.loads(response_text[start:end])
            else:
                plan = {"analysis": response_text, "subtasks": [], "plan": []}
        except json.JSONDecodeError:
            plan = {"analysis": response_text, "subtasks": [], "plan": []}

        # Create subtasks
        subtasks = []
        for st in plan.get("subtasks", []):
            sub = AgentTask(
                task_id=str(uuid.uuid4()),
                title=st.get("title", "Unnamed subtask"),
                description=st.get("description", ""),
                assigned_to=st.get("assign_to", "developer"),
                parent_task_id=task.task_id,
                status=TaskStatus.PENDING,
            )
            subtasks.append(sub)
            task.subtasks.append(sub.task_id)

        self.log_event("delegation", f"Decomposed into {len(subtasks)} subtasks", {
            "subtask_count": len(subtasks),
            "plan_steps": len(plan.get("plan", [])),
            "risk": plan.get("risk_assessment", "unknown"),
        })

        task.artifacts["plan"] = plan
        task.artifacts["subtasks"] = [{"id": s.task_id, "title": s.title, "assign_to": s.assigned_to} for s in subtasks]

        return AgentMessage(
            from_agent=self.name,
            to_agent="orchestrator",
            message_type="plan_ready",
            content={
                "task_id": task.task_id,
                "plan": plan,
                "subtasks": subtasks,
            },
        )

    def evaluate_results(self, task: AgentTask, results: dict[str, Any]) -> AgentMessage:
        """Evaluate final results and decide if task is complete."""
        all_approved = all(
            r.get("status") == "approved"
            for r in results.get("reviews", [])
        )

        self.log_event("decision", f"Evaluating results for: {task.title}", {
            "all_approved": all_approved,
            "review_count": len(results.get("reviews", [])),
        })

        if all_approved:
            task.status = TaskStatus.APPROVED
            self.total_tasks_completed += 1
            self.trust_score = min(100, self.trust_score + 2)
        else:
            task.status = TaskStatus.REJECTED
            self.total_tasks_failed += 1
            self.trust_score = max(0, self.trust_score - 5)

        return AgentMessage(
            from_agent=self.name,
            to_agent="orchestrator",
            message_type="evaluation_complete",
            content={
                "task_id": task.task_id,
                "approved": all_approved,
                "final_status": task.status.value,
            },
        )
