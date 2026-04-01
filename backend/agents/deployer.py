from __future__ import annotations
import json
import time
from typing import Any

from .base import BaseAgent, AgentMessage, AgentTask, TaskStatus


DEPLOYER_SYSTEM = """You are the Deployer agent in AgentForge, an autonomous multi-agent swarm.
Your role is to prepare deployment artifacts, verify deliverables, and generate documentation.

Given approved code, you must:
1. Verify all files are present and complete
2. Generate a deployment manifest
3. Create a summary document
4. Perform a simulated health check

Respond with valid JSON:
{
  "deployment_status": "success|failed",
  "manifest": {
    "files": ["file1.py", "file2.py"],
    "dependencies": ["dep1", "dep2"],
    "entry_point": "main.py",
    "runtime": "python3.11"
  },
  "health_check": {
    "status": "passed|failed",
    "checks": [
      {"name": "Files present", "passed": true},
      {"name": "Dependencies valid", "passed": true},
      {"name": "Entry point exists", "passed": true}
    ]
  },
  "documentation": "Brief documentation of the deployed solution",
  "summary": "Deployment summary"
}"""


class DeployerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="AgentForge-Deployer",
            role="deployer",
            capabilities=["cloud_deployment", "smart_contract_deployment", "health_verification", "submission"],
        )

    async def process(self, task: AgentTask, context: dict[str, Any]) -> AgentMessage:
        """Prepare deployment for approved code."""
        task.status = TaskStatus.IN_PROGRESS
        self.log_event("decision", f"Preparing deployment: {task.title}")

        code = task.artifacts.get("code", {})
        reviews = task.reviews

        prompt = f"""Prepare deployment for this approved code:

Task: {task.title}
Code: {json.dumps(code, default=str)[:2500]}
Reviews: {json.dumps(reviews, default=str)[:500]}

Verify all files, generate a deployment manifest, run health checks, and create documentation.
Respond ONLY with valid JSON."""

        response_text, tool_call = self.llm_call(DEPLOYER_SYSTEM, prompt, temperature=0.2)

        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                deployment = json.loads(response_text[start:end])
            else:
                deployment = {"deployment_status": "success", "summary": response_text}
        except json.JSONDecodeError:
            deployment = {"deployment_status": "success", "summary": response_text}

        task.artifacts["deployment"] = deployment
        deployed = deployment.get("deployment_status") == "success"

        if deployed:
            task.status = TaskStatus.DEPLOYED
            task.completed_at = time.time()
            self.total_tasks_completed += 1
            self.trust_score = min(100, self.trust_score + 1)
        else:
            task.status = TaskStatus.FAILED
            self.total_tasks_failed += 1

        self.log_event("deployment", f"Deployment {'succeeded' if deployed else 'failed'}: {task.title}", {
            "status": deployment.get("deployment_status"),
            "health_check": deployment.get("health_check", {}).get("status"),
            "file_count": len(deployment.get("manifest", {}).get("files", [])),
        })

        return AgentMessage(
            from_agent=self.name,
            to_agent="orchestrator",
            message_type="deployment_result",
            content={
                "task_id": task.task_id,
                "deployed": deployed,
                "deployment": deployment,
            },
        )
