import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
RPC_URL = os.getenv("RPC_URL", "https://sepolia.base.org")
CHAIN_ID = int(os.getenv("CHAIN_ID", "84532"))

AGENT_REGISTRY = os.getenv("AGENT_REGISTRY", "0x1E1E767c5f637Ed13981e0E3108e7aEeD0F06D81")

# Agent configuration
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"
MIN_TRUST_THRESHOLD = 60
MAX_RETRY_CYCLES = 3
TOTAL_BUDGET_USD = 50.0

AGENT_BUDGETS = {
    "planner": 10.0,
    "developer": 20.0,
    "qa": 10.0,
    "deployer": 10.0,
}

# Cost per 1M tokens (Groq Llama 3.3 70B)
COST_PER_INPUT_TOKEN = 0.59 / 1_000_000
COST_PER_OUTPUT_TOKEN = 0.79 / 1_000_000
