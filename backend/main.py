import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router

app = FastAPI(
    title="AgentForge — Autonomous Agent Swarm",
    description="Multi-agent swarm with ERC-8004 trust-gated collaboration and Filecoin persistence",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all errors and return JSON with CORS headers."""
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.get("/")
async def root():
    return {
        "name": "AgentForge",
        "version": "1.0.0",
        "description": "Autonomous multi-agent swarm with ERC-8004 trust-gated collaboration",
        "endpoints": {
            "POST /api/run": "Start autonomous swarm on a challenge",
            "GET /api/status": "Current swarm status",
            "GET /api/agents": "All agent details",
            "GET /api/events": "Full event log",
            "GET /api/tasks": "All tasks",
            "GET /api/logs": "DevSpot-compatible execution log",
            "GET /api/manifest": "agent.json manifest",
            "GET /api/budget": "Budget dashboard",
            "GET /api/storage": "Filecoin storage items",
            "WS /api/ws": "Real-time event stream",
        },
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
