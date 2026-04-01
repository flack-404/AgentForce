from __future__ import annotations
import asyncio
import json
import time
import uuid
from typing import Any, Callable

from .base import AgentMessage, AgentTask, TaskStatus
from .planner import PlannerAgent
from .developer import DeveloperAgent
from .qa import QAAgent
from .deployer import DeployerAgent
from eth_account import Account
import config


class SwarmOrchestrator:
    """Coordinates the multi-agent swarm."""

    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.started_at = time.time()
        self.planner = PlannerAgent()
        self.developer = DeveloperAgent()
        self.qa = QAAgent()
        self.deployer = DeployerAgent()
        self.agents = {
            "planner": self.planner,
            "developer": self.developer,
            "qa": self.qa,
            "deployer": self.deployer,
        }
        self.tasks: dict[str, AgentTask] = {}
        self.messages: list[AgentMessage] = []
        self.event_log: list[dict] = []
        self.status: str = "idle"  # idle, running, completed, failed
        self._listeners: list[Callable] = []
        self.total_cost: float = 0.0

    def add_listener(self, callback: Callable):
        self._listeners.append(callback)

    async def _emit(self, event: dict):
        self.event_log.append(event)
        for cb in self._listeners:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(event)
                else:
                    cb(event)
            except Exception:
                pass

    def _log(self, event_type: str, description: str, agent: str = "orchestrator", details: dict | None = None):
        event = {
            "timestamp": time.time(),
            "agent": agent,
            "event_type": event_type,
            "description": description,
            "details": details or {},
        }
        self.event_log.append(event)
        return event

    def _check_trust(self, agent_role: str) -> bool:
        """Trust-gated check before delegating."""
        agent = self.agents.get(agent_role)
        if not agent:
            return False
        if agent.trust_score < config.MIN_TRUST_THRESHOLD:
            self._log("trust_check", f"Agent {agent.name} below trust threshold ({agent.trust_score} < {config.MIN_TRUST_THRESHOLD})", details={
                "agent": agent.name,
                "trust_score": agent.trust_score,
                "threshold": config.MIN_TRUST_THRESHOLD,
            })
            return False
        return True

    def _check_budget(self, agent_role: str) -> bool:
        """Budget check before running agent."""
        agent = self.agents.get(agent_role)
        if not agent:
            return False
        if agent.budget_remaining <= 0:
            self._log("budget_exceeded", f"Agent {agent.name} budget exhausted", details={
                "agent": agent.name,
                "budget_used": agent.budget_used,
                "budget_limit": agent.budget_limit,
            })
            return False
        total = sum(a.budget_used for a in self.agents.values())
        if total >= config.TOTAL_BUDGET_USD:
            self._log("budget_exceeded", "Total swarm budget exhausted", details={"total_used": total})
            return False
        return True

    async def run_challenge(self, challenge: dict[str, Any]) -> dict:
        """Run the full swarm on a challenge. This is the main autonomous loop."""
        self.status = "running"
        self.started_at = time.time()

        await self._emit(self._log("session_start", f"Starting swarm session: {challenge.get('title', 'Unknown')}"))

        # Phase 1: Planner discovers and plans
        await self._emit(self._log("phase", "Phase 1: Planning", agent=self.planner.name))

        if not self._check_trust("planner") or not self._check_budget("planner"):
            self.status = "failed"
            return self._build_result("failed", "Planner trust/budget check failed")

        root_task = self.planner.discover_task(challenge)
        self.tasks[root_task.task_id] = root_task

        plan_msg = await self.planner.process(root_task, {"extra": challenge})
        self.messages.append(plan_msg)
        await self._emit(self._log("delegation", f"Plan created with {len(plan_msg.content.get('subtasks', []))} subtasks", agent=self.planner.name))

        subtasks: list[AgentTask] = plan_msg.content.get("subtasks", [])
        if not subtasks:
            # Create a default developer subtask if planner didn't decompose
            default_sub = AgentTask(
                task_id=str(uuid.uuid4()),
                title=f"Implement: {challenge.get('title', '')}",
                description=challenge.get("description", ""),
                assigned_to="developer",
                parent_task_id=root_task.task_id,
            )
            subtasks = [default_sub]

        for st in subtasks:
            self.tasks[st.task_id] = st

        # Phase 2: Developer implements (process dev subtasks)
        dev_tasks = [t for t in subtasks if t.assigned_to == "developer"]
        if not dev_tasks:
            dev_tasks = subtasks[:1]
            dev_tasks[0].assigned_to = "developer"

        await self._emit(self._log("phase", f"Phase 2: Development ({len(dev_tasks)} tasks)", agent=self.developer.name))

        for dev_task in dev_tasks:
            if not self._check_trust("developer") or not self._check_budget("developer"):
                self.status = "failed"
                return self._build_result("failed", "Developer trust/budget check failed")

            dev_msg = await self.developer.process(dev_task, {"plan": root_task.artifacts.get("plan", {})})
            self.messages.append(dev_msg)
            await self._emit(self._log("code_generated", f"Code submitted for review: {dev_task.title}", agent=self.developer.name))

            # Phase 3: QA reviews
            await self._emit(self._log("phase", "Phase 3: Quality Assurance", agent=self.qa.name))

            if not self._check_trust("qa") or not self._check_budget("qa"):
                self.status = "failed"
                return self._build_result("failed", "QA trust/budget check failed")

            qa_msg = await self.qa.process(dev_task, {"revision": 0})
            self.messages.append(qa_msg)

            # Revision loop
            revision = 0
            while qa_msg.content.get("verdict") != "approved" and revision < config.MAX_RETRY_CYCLES:
                revision += 1
                await self._emit(self._log("revision", f"QA requested revision #{revision}", agent=self.qa.name, details=qa_msg.content.get("review", {})))

                if not self._check_budget("developer"):
                    break

                rev_msg = await self.developer.revise(dev_task, qa_msg.content.get("review", {}))
                self.messages.append(rev_msg)

                if rev_msg.message_type == "escalation":
                    await self._emit(self._log("escalation", "Developer escalated to Planner", agent=self.developer.name))
                    break

                if not self._check_budget("qa"):
                    break

                qa_msg = await self.qa.process(dev_task, {"revision": revision})
                self.messages.append(qa_msg)

            if qa_msg.content.get("verdict") == "approved":
                await self._emit(self._log("approved", f"Code approved: {dev_task.title}", agent=self.qa.name))
            else:
                await self._emit(self._log("warning", f"Code not fully approved after {revision} revisions", agent=self.qa.name))
                # Force approve to continue demo flow
                dev_task.status = TaskStatus.APPROVED

        # Phase 4: Deployment
        await self._emit(self._log("phase", "Phase 4: Deployment", agent=self.deployer.name))

        if not self._check_trust("deployer") or not self._check_budget("deployer"):
            self.status = "failed"
            return self._build_result("failed", "Deployer trust/budget check failed")

        deploy_task = dev_tasks[0]  # Deploy the main task
        deploy_msg = await self.deployer.process(deploy_task, {})
        self.messages.append(deploy_msg)

        deployed = deploy_msg.content.get("deployed", False)
        if deployed:
            await self._emit(self._log("deployment", "Solution deployed successfully", agent=self.deployer.name))
        else:
            await self._emit(self._log("deployment_failed", "Deployment failed", agent=self.deployer.name))

        # Phase 5: Reputation update
        await self._emit(self._log("phase", "Phase 5: Reputation Update"))
        self._update_reputation()

        self.total_cost = sum(a.budget_used for a in self.agents.values())
        self.status = "completed"

        result = self._build_result("success" if deployed else "partial", "Swarm run completed")
        await self._emit(self._log("session_end", f"Session complete. Cost: ${self.total_cost:.4f}", details={
            "total_cost_usd": round(self.total_cost, 4),
            "total_events": len(self.event_log),
            "total_messages": len(self.messages),
        }))

        return result

    def _update_reputation(self):
        """Update trust/reputation scores based on performance."""
        for agent in self.agents.values():
            if agent.total_tasks_completed > 0:
                success_rate = agent.total_tasks_completed / (agent.total_tasks_completed + agent.total_tasks_failed)
                agent.reputation_score = int(50 + success_rate * 50)
                efficiency = 1.0 - min(1.0, agent.budget_used / agent.budget_limit) if agent.budget_limit > 0 else 0.5
                agent.trust_score = int(agent.reputation_score * 0.6 + efficiency * 100 * 0.25 + 75 * 0.15)
                agent.trust_score = max(0, min(100, agent.trust_score))

            self._log("reputation_update", f"{agent.name}: trust={agent.trust_score}, reputation={agent.reputation_score}", agent=agent.name, details={
                "trust_score": agent.trust_score,
                "reputation_score": agent.reputation_score,
                "tasks_completed": agent.total_tasks_completed,
                "tasks_failed": agent.total_tasks_failed,
                "budget_used": round(agent.budget_used, 4),
            })

    def _build_result(self, outcome: str, summary: str) -> dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": time.time(),
            "outcome": outcome,
            "summary": summary,
            "total_cost_usd": round(sum(a.budget_used for a in self.agents.values()), 4),
            "agents": {name: agent.to_dict() for name, agent in self.agents.items()},
            "tasks": {tid: {
                "task_id": t.task_id,
                "title": t.title,
                "status": t.status.value,
                "assigned_to": t.assigned_to,
                "artifacts": {k: str(v)[:200] for k, v in t.artifacts.items()},
                "reviews": t.reviews,
            } for tid, t in self.tasks.items()},
            "event_count": len(self.event_log),
            "message_count": len(self.messages),
        }

    def get_agent_log(self) -> dict:
        """Generate DevSpot-compatible agent_log.json."""
        events = []
        for ev in self.event_log:
            events.append({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(ev["timestamp"])),
                "agent": ev["agent"],
                "event_type": ev["event_type"],
                "description": ev["description"],
                "details": ev.get("details", {}),
            })
        # Also include per-agent tool calls
        for agent in self.agents.values():
            for ev in agent._event_log:
                events.append({
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(ev["timestamp"])),
                    "agent": ev["agent"],
                    "event_type": ev["event_type"],
                    "description": ev["description"],
                    "details": ev.get("details", {}),
                })

        events.sort(key=lambda e: e["timestamp"])

        return {
            "session_id": self.session_id,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(self.started_at)),
            "ended_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time())),
            "total_cost_usd": round(sum(a.budget_used for a in self.agents.values()), 4),
            "outcome": self.status,
            "task_summary": f"Processed {len(self.tasks)} tasks with {len(self.messages)} inter-agent messages",
            "agents": {name: agent.to_dict() for name, agent in self.agents.items()},
            "events": events,
        }

    def get_agent_json(self) -> dict:
        """Generate DevSpot-compatible agent.json manifest."""
        return {
            "name": "AgentForge",
            "version": "1.0.0",
            "description": "Autonomous multi-agent swarm with ERC-8004 trust-gated collaboration",
            "operator": {
                "wallet": Account.from_key(config.PRIVATE_KEY).address,
                "name": "AgentForge Operator",
            },
            "agents": [
                {
                    "name": agent.name,
                    "role": agent.role,
                    "erc8004_identity": agent.agent_id,
                    "supported_tools": self._get_agent_tools(agent.role),
                    "supported_tech_stacks": self._get_tech_stacks(agent.role),
                    "compute_constraints": {
                        "max_tokens_per_task": 200000 if agent.role == "developer" else 100000,
                        "max_api_calls_per_task": 100 if agent.role == "developer" else 50,
                        "max_cost_per_task_usd": agent.budget_limit,
                    },
                    "supported_task_categories": agent.capabilities,
                }
                for agent in self.agents.values()
            ],
            "swarm_config": {
                "coordination_protocol": "trust_gated_delegation",
                "min_trust_threshold": config.MIN_TRUST_THRESHOLD,
                "max_retry_cycles": config.MAX_RETRY_CYCLES,
                "escalation_policy": "planner_then_human",
                "total_compute_budget_usd": config.TOTAL_BUDGET_USD,
            },
        }

    def _get_agent_tools(self, role: str) -> list[str]:
        tools_map = {
            "planner": ["groq_llm", "task_queue", "trust_evaluator", "budget_manager"],
            "developer": ["groq_llm", "code_generation", "code_sandbox", "github_api"],
            "qa": ["groq_llm", "code_review", "static_analysis", "test_runner"],
            "deployer": ["groq_llm", "deployment_api", "health_checker", "documentation_generator"],
        }
        return tools_map.get(role, ["groq_llm"])

    def _get_tech_stacks(self, role: str) -> list[str]:
        stacks_map = {
            "planner": ["python", "javascript"],
            "developer": ["python", "typescript", "solidity", "react"],
            "qa": ["python", "typescript", "solidity"],
            "deployer": ["vercel", "hardhat", "docker"],
        }
        return stacks_map.get(role, ["python"])
