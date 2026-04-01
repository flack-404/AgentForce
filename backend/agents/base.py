from __future__ import annotations
import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any

from groq import Groq
import config


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"
    FAILED = "failed"


@dataclass
class AgentMessage:
    from_agent: str
    to_agent: str
    message_type: str  # "task_assignment", "code_submission", "review_result", "deployment_result", "status_update"
    content: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ToolCall:
    tool_name: str
    input_data: dict[str, Any]
    output_data: Any
    cost_usd: float
    tokens_used: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentTask:
    task_id: str
    title: str
    description: str
    assigned_to: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    parent_task_id: str | None = None
    subtasks: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    reviews: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


class BaseAgent:
    def __init__(self, name: str, role: str, capabilities: list[str]):
        self.agent_id = str(uuid.uuid4())
        self.name = name
        self.role = role
        self.capabilities = capabilities
        self.trust_score: int = 75  # Initial trust
        self.reputation_score: int = 75
        self.total_tasks_completed: int = 0
        self.total_tasks_failed: int = 0
        self.budget_used: float = 0.0
        self.budget_limit: float = config.AGENT_BUDGETS.get(role, 10.0)
        self.tool_calls: list[ToolCall] = []
        self.message_history: list[AgentMessage] = []
        self._event_log: list[dict] = []
        self._groq = Groq(api_key=config.GROQ_API_KEY)

    @property
    def budget_remaining(self) -> float:
        return self.budget_limit - self.budget_used

    @property
    def budget_pct(self) -> float:
        return (self.budget_used / self.budget_limit * 100) if self.budget_limit > 0 else 0

    def log_event(self, event_type: str, description: str, details: dict | None = None):
        event = {
            "timestamp": time.time(),
            "agent": self.name,
            "event_type": event_type,
            "description": description,
            "details": details or {},
        }
        self._event_log.append(event)
        return event

    def llm_call(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> tuple[str, ToolCall]:
        """Make a Groq LLM call, track cost. Falls back to smaller model on rate limit."""
        start = time.time()
        models = [config.GROQ_MODEL, config.GROQ_FALLBACK_MODEL]
        response = None
        used_model = models[0]
        for model in models:
            try:
                response = self._groq.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=4096,
                )
                used_model = model
                break
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    self.log_event("rate_limit", f"Rate limited on {model}, trying fallback...")
                    continue
                raise
        if response is None:
            raise RuntimeError("All models rate limited. Please wait and try again.")
        content = response.choices[0].message.content or ""
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        total_tokens = input_tokens + output_tokens
        cost = (input_tokens * config.COST_PER_INPUT_TOKEN) + (output_tokens * config.COST_PER_OUTPUT_TOKEN)
        self.budget_used += cost

        tool_call = ToolCall(
            tool_name="groq_llm",
            input_data={"system": system_prompt[:200], "user": user_prompt[:200], "model": used_model},
            output_data=content[:500],
            cost_usd=cost,
            tokens_used=total_tokens,
        )
        self.tool_calls.append(tool_call)
        self.log_event("tool_call", f"LLM call ({total_tokens} tokens, ${cost:.4f})", {
            "tool": "groq_llm",
            "model": used_model,
            "tokens": total_tokens,
            "cost_usd": round(cost, 6),
            "duration_ms": round((time.time() - start) * 1000),
        })
        return content, tool_call

    def receive_message(self, msg: AgentMessage):
        self.message_history.append(msg)

    async def process(self, task: AgentTask, context: dict[str, Any]) -> AgentMessage:
        """Override in subclass. Process a task and return a message."""
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "trust_score": self.trust_score,
            "reputation_score": self.reputation_score,
            "tasks_completed": self.total_tasks_completed,
            "tasks_failed": self.total_tasks_failed,
            "budget_used": round(self.budget_used, 4),
            "budget_limit": self.budget_limit,
            "budget_remaining": round(self.budget_remaining, 4),
            "tool_calls_count": len(self.tool_calls),
        }
