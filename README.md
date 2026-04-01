# AgentForge — Autonomous Multi-Agent Swarm

An autonomous multi-agent system where AI agents collaborate through trust-gated delegation, with on-chain identity and reputation via ERC-8004. Agents discover tasks, decompose them, write code, review each other's work, and deploy all with real LLM reasoning and verifiable execution logs.

## Problem

Current AI agent frameworks are single-agent, black-box systems with no accountability. There's no way to verify what an agent did, delegate based on trust, or enforce compute budgets across a team of agents.

## Solution

AgentForge is a **trust-gated multi-agent swarm** that:

1. **Discovers tasks** from GitHub issues or custom challenges
2. **Decomposes** them into subtasks via a Planner agent (Groq LLM)
3. **Develops** solutions through a Developer agent with iterative code generation
4. **Reviews** code quality through a QA agent with automatic revision loops
5. **Deploys** approved code through a Deployer agent
6. **Registers agents on-chain** with ERC-8004 identity and weighted reputation
7. **Stores execution logs** as content-addressed Filecoin-compatible CIDs
8. **Exports DevSpot-compatible** `agent.json` manifest and `agent_log.json`

## Architecture

```
┌──────────────────────────────────────────────────┐
│                 SwarmOrchestrator                 │
│         (Trust gates · Budget enforcement)        │
└──────┬──────┬──────────┬──────────┬──────────────┘
       │      │          │          │
  ┌────▼──┐ ┌─▼───────┐ ┌▼───────┐ ┌▼─────────┐
  │Planner│ │Developer│ │   QA   │ │ Deployer  │
  │ Agent │ │  Agent  │ │ Agent  │ │  Agent    │
  └───────┘ └─────────┘ └────────┘ └───────────┘
       │         │           │           │
       └─────────┴─────┬─────┴───────────┘
                        │
           ┌────────────┼────────────┐
           │            │            │
    ┌──────▼───┐  ┌─────▼─────┐  ┌──▼──────────┐
    │  Groq    │  │  ERC-8004 │  │  Filecoin   │
    │  LLM API │  │  Registry │  │  Storage    │
    │(llama-3.3)│  │(Base Sep.)│  │ (CID/IPLD) │
    └──────────┘  └───────────┘  └─────────────┘
```

## Pipeline Flow

```
Challenge Input
    → Planner: discovers & decomposes tasks (LLM)
    → Developer: generates code for each subtask (LLM)
    → QA: reviews code, requests revisions (LLM, max 3 cycles)
    → Deployer: prepares artifacts, runs health checks (LLM)
    → Orchestrator: registers all agents on-chain, stores logs to Filecoin
    → Result: agent.json + agent_log.json + on-chain tx hashes + CIDs
```

## Smart Contracts (Base Sepolia)

| Contract | Address | Purpose |
|----------|---------|---------|
| AgentRegistry (ERC-8004) | `0x1E1E767c5f637Ed13981e0E3108e7aEeD0F06D81` | Agent registration, trust scores, weighted reputation |

## Tech Stack

- **Backend**: Python 3, FastAPI, WebSocket streaming, async orchestration
- **LLM**: Groq API — `llama-3.3-70b-versatile` (primary), `llama-3.1-8b-instant` (fallback)
- **Frontend**: Next.js 14, React 18, TailwindCSS
- **Contracts**: Solidity 0.8.20, Hardhat, Base Sepolia
- **Storage**: Content-addressed SHA-256 CIDs (Filecoin/IPLD compatible, `bafyrei` prefix)
- **Identity**: ERC-8004 on-chain agent identity with weighted moving average reputation
- **Compatibility**: DevSpot `agent.json` manifest + `agent_log.json` execution log

## Key Features

- **Trust-Gated Delegation**: Orchestrator checks agent trust scores before delegating tasks
- **Budget Enforcement**: Per-agent spending limits with hard stops ($50 total, per-role caps)
- **QA Review Loop**: Developer ↔ QA revision cycle (max 3 rounds, lenient after 2)
- **Model Fallback**: Automatic fallback from 70B to 8B model on rate limits
- **Real-Time Events**: WebSocket streaming of all agent decisions, tool calls, reviews
- **Content-Addressed Storage**: Every execution log, artifact, and manifest gets a deterministic CID
- **On-Chain Reputation**: Weighted moving average (0.7 new + 0.3 old) reputation updates per run
- **No Mock Data**: All data comes from live API calls — GitHub issues, Groq LLM, on-chain transactions

## Running Locally

### Prerequisites

- Node.js 18+
- Python 3.10+
- Groq API key (free at console.groq.com)

### 1. Backend (Port 8001)

```bash
cd AgentForge/backend
pip install -r requirements.txt
```

Create `.env`:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
PRIVATE_KEY=your_ethereum_private_key
RPC_URL=https://sepolia.base.org
CHAIN_ID=84532
AGENT_REGISTRY=0x1E1E767c5f637Ed13981e0E3108e7aEeD0F06D81
```

```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001
```

### 2. Frontend (Port 3002)

```bash
cd AgentForge/frontend
npm install
```

Create `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8001
```

```bash
npm run dev -- -p 3002
```

### 3. Contracts (already deployed)

If you need to redeploy:
```bash
cd AgentForge/contracts
npm install
npx hardhat compile
npx hardhat run scripts/deploy.ts --network baseSepolia
```

### 4. Open in browser

Navigate to http://localhost:3002

### 5. Run a test

On the dashboard:
1. Click "Discover from GitHub" to find real open issues, or
2. Enter a custom challenge title + description
3. Click "Launch Autonomous Swarm"
4. Watch the live event feed as agents collaborate
5. Check Agents / Tasks / Logs / Trust / Budget pages for detailed views

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/run` | Launch a swarm challenge |
| GET | `/status` | Current swarm status + agent states |
| GET | `/agents` | All registered agents with stats |
| GET | `/tasks` | Task queue with status |
| GET | `/logs` | DevSpot-compatible execution log |
| GET | `/manifest` | DevSpot-compatible agent.json |
| GET | `/budget` | Budget utilization per agent |
| GET | `/storage` | Filecoin CIDs for stored data |
| GET | `/history` | Past run history |
| WS | `/ws` | Real-time event stream |

## Mathematics & Algorithms

### Reputation Scoring (On-Chain)

The `AgentRegistry` contract uses a **cumulative moving average** for reputation:

```
new_reputation = (old_reputation * (taskCount - 1) + new_score) / taskCount
```

Where `new_score` is 0-100 based on task outcome. Initial reputation for newly registered agents is 75. All arithmetic is done in unsigned integers (uint8 for reputation, uint256 for intermediate calculations).

Outcome encoding: `0 = SUCCESS`, `1 = PARTIAL`, `2 = FAILURE`

### Trust-Gated Delegation

Before delegating a task to any agent, the orchestrator checks:

```python
trust_score = registry.getTrustScore(agent_id)  # on-chain read
if trust_score < MIN_TRUST_THRESHOLD:            # threshold = 60
    raise TrustGateError(f"Agent {role} blocked: trust {trust_score} < 60")
```

This implements a **binary trust gate** — agents either have delegation privileges or they don't. The threshold of 60 means an agent must maintain above-average performance to remain trusted.

### Budget Enforcement

Per-agent budget limits enforce compute cost control:

```
Total budget: $50.00
  Planner:   $10.00 (20%)
  Developer: $20.00 (40%)
  QA:        $10.00 (20%)
  Deployer:  $10.00 (20%)
```

Cost calculation per LLM call:

```
cost = (input_tokens * $0.59/1M) + (output_tokens * $0.79/1M)
```

Based on Groq Llama 3.3 70B pricing. Before each agent runs, the orchestrator checks:

```python
if agent.budget_used + estimated_cost > agent.budget_limit:
    raise BudgetExceededError(...)
```

### Content-Addressed Storage (CIDv1)

Every artifact, log, and manifest is stored with a deterministic content identifier:

```
CID = "bafyrei" + SHA-256(json_bytes)[:52]
```

This follows the CIDv1 convention for dag-cbor codec with SHA-256 multihash. The `bafyrei` prefix indicates:
- `b` = base32 encoding
- `afyrei` = multicodec for CIDv1 + dag-cbor + sha2-256

Data is stored both by category path (`filecoin_data/{category}/{name}.json`) and by CID (`filecoin_data/cids/{cid}.json`) for content-addressed retrieval.

### QA Review Convergence

The QA review loop implements a **diminishing returns** strategy:

```
Round 1-2: Strict review — any issue triggers revision
Round 3+:  Lenient review — only CRITICAL issues trigger revision (approve if no critical)
Max rounds: 3 (hard stop)
```

This prevents infinite revision loops while ensuring quality. The convergence logic:

```python
if review_count >= 2:
    # Lenient mode: approve if no critical issues
    prompt += "Be lenient. Only reject if there are CRITICAL issues."
if review_count >= MAX_RETRY_CYCLES:
    # Force approve
    return {"approved": True, "reason": "Max revisions reached"}
```

### Model Fallback Strategy

On Groq API rate limits (HTTP 429), the system falls back to a smaller model:

```
Primary:  llama-3.3-70b-versatile  (high quality, 100K daily token limit)
Fallback: llama-3.1-8b-instant     (lower quality, separate rate limits)
```

The fallback is transparent — no retry loops or sleep delays. If the primary model returns 429, the exact same prompt is sent to the fallback model immediately.

### Agent Identity (ERC-8004)

Each agent gets a deterministic on-chain identity:

```
agentId = keccak256(agent_name_string)  // bytes32
```

The `registerAgent(agentId, capabilities, metadataURI)` function stores:
- Capabilities string (comma-separated)
- Metadata URI (IPFS/HTTP link to agent manifest)
- Registration timestamp
- Initial reputation (75)

### DevSpot Compatibility

The `agent.json` manifest follows the DevSpot agent identity standard:

```json
{
  "name": "AgentForge Swarm",
  "version": "1.0.0",
  "operator": "0x...",          // real wallet from PRIVATE_KEY
  "capabilities": ["plan", "code", "review", "deploy"],
  "trust_scores": {...},        // per-agent on-chain trust
  "erc8004_registry": "0x1E1E...",
  "chain": "base-sepolia"
}
```

The `agent_log.json` execution log contains timestamped events:
```json
{
  "session_id": "uuid",
  "events": [
    {"timestamp": "ISO-8601", "agent": "swarm-planner", "event_type": "decision", "description": "..."}
  ],
  "outcome": "completed",
  "total_cost_usd": 0.0077
}
```

## Generated Artifacts

After each run, AgentForge produces:

- **`agent.json`** — DevSpot-compatible manifest with real operator wallet, capabilities, trust scores
- **`agent_log.json`** — Structured execution log with all events, decisions, tool calls
- **Filecoin CIDs** — Content-addressed storage for logs, artifacts, and manifests
- **On-chain tx hashes** — ERC-8004 registration and reputation update transactions

## Hackathon Tracks & Bounties

- **AI Track**: Autonomous multi-agent orchestration with real LLM reasoning
- **EF Agent Bounties (both)**: DevSpot-compatible agent identity + execution logs
- **Filecoin Bounty**: Content-addressed storage with IPLD-compatible CIDs

## License

MIT
