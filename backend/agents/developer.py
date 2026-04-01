from __future__ import annotations
import json
from typing import Any

from .base import BaseAgent, AgentMessage, AgentTask, TaskStatus


DEVELOPER_SYSTEM = """You are the Developer agent in AgentForge, an autonomous multi-agent swarm.
Your role is to write high-quality code to solve assigned tasks.

Rules:
- Write clean, well-structured code
- Never include secrets, API keys, or credentials in code
- Handle edge cases properly
- Include inline comments for complex logic
- Follow best practices for the language

When given a task, respond with valid JSON:
{
  "language": "python|typescript|solidity",
  "files": [
    {
      "filename": "main.py",
      "content": "# code here...",
      "description": "What this file does"
    }
  ],
  "explanation": "Brief explanation of the implementation",
  "test_suggestions": ["Test case 1", "Test case 2"],
  "dependencies": ["package1", "package2"]
}"""


REVISION_SYSTEM = """You are the Developer agent in AgentForge. You received QA feedback on your code.
Fix the issues identified and return the revised code.

Respond with valid JSON:
{
  "files": [
    {
      "filename": "main.py",
      "content": "# revised code...",
      "description": "What changed"
    }
  ],
  "changes_made": ["Change 1", "Change 2"],
  "explanation": "What was fixed and why"
}"""


class DeveloperAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="AgentForge-Developer",
            role="developer",
            capabilities=["code_generation", "code_modification", "repository_management", "dependency_management"],
        )
        self.retry_count: dict[str, int] = {}

    async def process(self, task: AgentTask, context: dict[str, Any]) -> AgentMessage:
        """Write code for the given task."""
        task.status = TaskStatus.IN_PROGRESS
        self.log_event("decision", f"Starting implementation: {task.title}")

        prompt = f"""Implement the following task:

Title: {task.title}
Description: {task.description}

Parent plan context: {json.dumps(context.get('plan', {}), default=str)[:800]}

Write complete, working code. Respond ONLY with valid JSON."""

        response_text, tool_call = self.llm_call(DEVELOPER_SYSTEM, prompt, temperature=0.4)

        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                code_output = json.loads(response_text[start:end])
            else:
                code_output = {"files": [], "explanation": response_text}
        except json.JSONDecodeError:
            code_output = {"files": [], "explanation": response_text}

        task.artifacts["code"] = code_output
        task.status = TaskStatus.REVIEW

        self.log_event("tool_call", f"Generated {len(code_output.get('files', []))} files", {
            "tool": "code_generation",
            "file_count": len(code_output.get("files", [])),
            "language": code_output.get("language", "unknown"),
        })

        return AgentMessage(
            from_agent=self.name,
            to_agent="qa",
            message_type="code_submission",
            content={
                "task_id": task.task_id,
                "code": code_output,
            },
        )

    async def revise(self, task: AgentTask, feedback: dict[str, Any]) -> AgentMessage:
        """Revise code based on QA feedback."""
        task_id = task.task_id
        self.retry_count[task_id] = self.retry_count.get(task_id, 0) + 1

        if self.retry_count[task_id] > 3:
            self.log_event("escalation", f"Max retries exceeded for: {task.title}", {
                "retries": self.retry_count[task_id],
            })
            return AgentMessage(
                from_agent=self.name,
                to_agent="planner",
                message_type="escalation",
                content={"task_id": task_id, "reason": "Max retries exceeded", "feedback": feedback},
            )

        self.log_event("decision", f"Revising code (attempt {self.retry_count[task_id]}): {task.title}")

        original_code = json.dumps(task.artifacts.get("code", {}), default=str)[:2000]
        feedback_text = json.dumps(feedback, default=str)[:1000]

        prompt = f"""Revise this code based on QA feedback.

Original code:
{original_code}

QA Feedback:
{feedback_text}

Fix ALL issues identified. Respond ONLY with valid JSON."""

        response_text, tool_call = self.llm_call(REVISION_SYSTEM, prompt, temperature=0.3)

        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                revised = json.loads(response_text[start:end])
            else:
                revised = {"files": [], "explanation": response_text}
        except json.JSONDecodeError:
            revised = {"files": [], "explanation": response_text}

        task.artifacts["code"] = revised
        task.artifacts[f"revision_{self.retry_count[task_id]}"] = revised
        task.status = TaskStatus.REVIEW

        self.log_event("tool_call", f"Revised code (attempt {self.retry_count[task_id]})", {
            "tool": "code_revision",
            "retry_number": self.retry_count[task_id],
            "changes": revised.get("changes_made", []),
        })

        return AgentMessage(
            from_agent=self.name,
            to_agent="qa",
            message_type="code_submission",
            content={
                "task_id": task_id,
                "code": revised,
                "revision": self.retry_count[task_id],
            },
        )
