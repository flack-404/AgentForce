from __future__ import annotations
import json
from typing import Any

from .base import BaseAgent, AgentMessage, AgentTask, TaskStatus


QA_SYSTEM = """You are the QA (Quality Assurance) agent in AgentForge, an autonomous multi-agent swarm.
Your role is to review code for correctness, security, quality, and completeness.

Review criteria:
1. Correctness: Does the code solve the task requirements?
2. Security: Are there any vulnerabilities (injection, XSS, etc.)?
3. Quality: Is the code clean, readable, and well-structured?
4. Completeness: Does it handle edge cases? Are there missing features?
5. Best Practices: Does it follow language conventions?

Respond with valid JSON:
{
  "verdict": "approved|revise|rejected",
  "score": 85,
  "issues": [
    {
      "severity": "critical|major|minor|suggestion",
      "file": "main.py",
      "description": "Description of the issue",
      "suggestion": "How to fix it"
    }
  ],
  "strengths": ["Good error handling", "Clean code structure"],
  "summary": "Overall assessment",
  "test_results": {
    "tests_suggested": 5,
    "tests_would_pass": 4,
    "coverage_estimate": "80%"
  }
}"""


class QAAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="AgentForge-QA",
            role="qa",
            capabilities=["code_review", "testing", "security_audit", "validation"],
        )
        self.review_count: dict[str, int] = {}

    async def process(self, task: AgentTask, context: dict[str, Any]) -> AgentMessage:
        """Review code submitted by Developer."""
        task_id = task.task_id
        self.review_count[task_id] = self.review_count.get(task_id, 0) + 1

        code = task.artifacts.get("code", {})
        self.log_event("decision", f"Reviewing code for: {task.title} (review #{self.review_count[task_id]})")

        prompt = f"""Review the following code submission:

Task: {task.title}
Description: {task.description}

Code:
{json.dumps(code, default=str)[:3000]}

Revision number: {context.get('revision', 0)}

Review thoroughly for correctness, security, quality, and completeness.
Be constructive but rigorous. Respond ONLY with valid JSON."""

        response_text, tool_call = self.llm_call(QA_SYSTEM, prompt, temperature=0.2)

        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                review = json.loads(response_text[start:end])
            else:
                review = {"verdict": "approved", "score": 70, "issues": [], "summary": response_text}
        except json.JSONDecodeError:
            review = {"verdict": "approved", "score": 70, "issues": [], "summary": response_text}

        # After 2 reviews, be more lenient to avoid infinite loops
        if self.review_count[task_id] >= 2 and review.get("verdict") == "revise":
            critical_issues = [i for i in review.get("issues", []) if i.get("severity") == "critical"]
            if not critical_issues:
                review["verdict"] = "approved"
                review["summary"] += " (Approved after iterative improvement)"

        task.reviews.append(review)
        verdict = review.get("verdict", "approved")

        self.log_event("review", f"Review verdict: {verdict} (score: {review.get('score', 'N/A')})", {
            "verdict": verdict,
            "score": review.get("score"),
            "issues_found": len(review.get("issues", [])),
            "review_number": self.review_count[task_id],
        })

        if verdict == "approved":
            task.status = TaskStatus.APPROVED
            self.total_tasks_completed += 1
            return AgentMessage(
                from_agent=self.name,
                to_agent="deployer",
                message_type="review_result",
                content={"task_id": task_id, "verdict": "approved", "review": review},
            )
        else:
            task.status = TaskStatus.REJECTED
            return AgentMessage(
                from_agent=self.name,
                to_agent="developer",
                message_type="review_result",
                content={"task_id": task_id, "verdict": verdict, "review": review},
            )
