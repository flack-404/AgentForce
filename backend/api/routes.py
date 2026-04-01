from __future__ import annotations
import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from agents.orchestrator import SwarmOrchestrator
from storage import filecoin
from erc8004.registry import ERC8004Registry

router = APIRouter()

# Global state
orchestrator: SwarmOrchestrator | None = None
ws_clients: list[WebSocket] = []
run_history: list[dict] = []


class ChallengeRequest(BaseModel):
    title: str
    description: str
    source: str = "manual"
    type: str = "coding"


class ContractConfig(BaseModel):
    address: str


# ERC-8004 registry (set after contract deployment)
erc8004: ERC8004Registry | None = None


async def broadcast(event: dict):
    """Broadcast event to all connected WebSocket clients."""
    msg = json.dumps(event, default=str)
    disconnected = []
    for ws in ws_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        ws_clients.remove(ws)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    try:
        # Send current state on connect
        if orchestrator:
            await websocket.send_text(json.dumps({
                "type": "state",
                "data": {
                    "status": orchestrator.status,
                    "agents": {n: a.to_dict() for n, a in orchestrator.agents.items()},
                    "event_count": len(orchestrator.event_log),
                },
            }, default=str))
        while True:
            await websocket.receive_text()  # Keep alive
    except WebSocketDisconnect:
        if websocket in ws_clients:
            ws_clients.remove(websocket)


@router.post("/run")
async def run_challenge(req: ChallengeRequest):
    """Start the autonomous swarm on a challenge."""
    global orchestrator
    orchestrator = SwarmOrchestrator()

    # Add WebSocket broadcast listener
    async def on_event(event: dict):
        await broadcast({"type": "event", "data": event})

    orchestrator.add_listener(on_event)

    challenge = {
        "title": req.title,
        "description": req.description,
        "source": req.source,
        "type": req.type,
    }

    # Run in background so we can stream events
    result = await orchestrator.run_challenge(challenge)

    # Store results on Filecoin
    log_data = orchestrator.get_agent_log()
    manifest_data = orchestrator.get_agent_json()

    log_storage = filecoin.store_execution_log(orchestrator.session_id, log_data)
    manifest_storage = filecoin.store_manifest(manifest_data)

    # Store agent states
    for name, agent in orchestrator.agents.items():
        filecoin.store_agent_state(name, agent.to_dict())

    # Store artifacts for each task
    for tid, task in orchestrator.tasks.items():
        if task.artifacts:
            filecoin.store_artifact(tid, "artifacts", task.artifacts)

    result["storage"] = {
        "execution_log": log_storage,
        "manifest": manifest_storage,
    }

    run_history.append(result)

    # Register agents on-chain if contract is configured
    if erc8004:
        try:
            tx_hashes = []
            for agent in orchestrator.agents.values():
                tx = erc8004.register_agent(
                    agent.agent_id,
                    ",".join(agent.capabilities),
                    manifest_storage["cid"],
                )
                tx_hashes.append({"agent": agent.name, "tx": tx})

            # Update reputation
            for agent in orchestrator.agents.values():
                for tid, task in orchestrator.tasks.items():
                    if task.assigned_to == agent.role and task.completed_at:
                        outcome = 0 if task.status.value == "deployed" else 2
                        tx = erc8004.update_reputation(
                            agent.agent_id, tid, outcome, agent.reputation_score,
                            int(agent.budget_used * 1_000_000),
                        )
                        tx_hashes.append({"agent": agent.name, "reputation_tx": tx})

            result["onchain"] = {"tx_hashes": tx_hashes}
        except Exception as e:
            result["onchain"] = {"error": str(e)}

    return result


@router.get("/status")
async def get_status():
    """Get current swarm status."""
    if not orchestrator:
        return {"status": "idle", "agents": {}}
    return {
        "status": orchestrator.status,
        "session_id": orchestrator.session_id,
        "agents": {n: a.to_dict() for n, a in orchestrator.agents.items()},
        "tasks": {tid: {"title": t.title, "status": t.status.value, "assigned_to": t.assigned_to}
                  for tid, t in orchestrator.tasks.items()},
        "event_count": len(orchestrator.event_log),
        "total_cost": round(sum(a.budget_used for a in orchestrator.agents.values()), 4),
    }


@router.get("/agents")
async def get_agents():
    """Get all agent details."""
    if not orchestrator:
        return {"agents": {}}
    return {"agents": {n: a.to_dict() for n, a in orchestrator.agents.items()}}


@router.get("/agents/{role}")
async def get_agent(role: str):
    """Get a specific agent's details."""
    if not orchestrator or role not in orchestrator.agents:
        return {"error": "Agent not found"}
    agent = orchestrator.agents[role]
    return {
        **agent.to_dict(),
        "tool_calls": [
            {"tool": tc.tool_name, "cost": tc.cost_usd, "tokens": tc.tokens_used, "timestamp": tc.timestamp}
            for tc in agent.tool_calls
        ],
        "event_log": agent._event_log,
    }


@router.get("/events")
async def get_events():
    """Get the full event log."""
    if not orchestrator:
        return {"events": []}
    return {"events": orchestrator.event_log}


@router.get("/tasks")
async def get_tasks():
    """Get all tasks."""
    if not orchestrator:
        return {"tasks": {}}
    return {"tasks": {
        tid: {
            "task_id": t.task_id,
            "title": t.title,
            "description": t.description,
            "status": t.status.value,
            "assigned_to": t.assigned_to,
            "subtasks": t.subtasks,
            "review_count": len(t.reviews),
            "has_artifacts": bool(t.artifacts),
        }
        for tid, t in orchestrator.tasks.items()
    }}


@router.get("/logs")
async def get_logs():
    """Get the DevSpot-compatible execution log."""
    if not orchestrator:
        return {"error": "No session"}
    return orchestrator.get_agent_log()


@router.get("/manifest")
async def get_manifest():
    """Get the agent.json manifest."""
    if not orchestrator:
        # Return a default manifest
        o = SwarmOrchestrator()
        return o.get_agent_json()
    return orchestrator.get_agent_json()


@router.get("/storage")
async def get_storage():
    """List all stored items on Filecoin."""
    return {"items": filecoin.list_stored()}


@router.get("/storage/{category}")
async def get_storage_category(category: str):
    """List stored items in a category."""
    return {"items": filecoin.list_stored(category)}


@router.get("/history")
async def get_history():
    """Get run history."""
    return {"runs": [
        {
            "session_id": r.get("session_id"),
            "outcome": r.get("outcome"),
            "total_cost_usd": r.get("total_cost_usd"),
            "started_at": r.get("started_at"),
            "ended_at": r.get("ended_at"),
        }
        for r in run_history
    ]}


@router.post("/erc8004/configure")
async def configure_erc8004(req: ContractConfig):
    """Set the ERC-8004 contract address."""
    global erc8004
    erc8004 = ERC8004Registry(req.address)
    return {"configured": True, "address": req.address, "operator": erc8004.operator_address}


@router.get("/budget")
async def get_budget():
    """Get real-time budget info."""
    if not orchestrator:
        return {"total_budget": 50.0, "used": 0, "agents": {}}
    return {
        "total_budget": 50.0,
        "total_used": round(sum(a.budget_used for a in orchestrator.agents.values()), 4),
        "agents": {
            n: {
                "budget_limit": a.budget_limit,
                "budget_used": round(a.budget_used, 4),
                "budget_remaining": round(a.budget_remaining, 4),
                "budget_pct": round(a.budget_pct, 1),
            }
            for n, a in orchestrator.agents.items()
        },
    }
