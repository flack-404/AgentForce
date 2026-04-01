"""ERC-8004 Agent Identity & Reputation on Base Sepolia."""
from __future__ import annotations
import time
from web3 import Web3
from eth_account import Account
import config


# Minimal ERC-8004 ABI for AgentRegistry (we deploy our own lightweight version)
AGENT_REGISTRY_ABI = [
    {
        "inputs": [
            {"name": "agentId", "type": "bytes32"},
            {"name": "capabilities", "type": "string"},
            {"name": "metadataURI", "type": "string"},
        ],
        "name": "registerAgent",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "agentId", "type": "bytes32"},
            {"name": "taskId", "type": "bytes32"},
            {"name": "outcome", "type": "uint8"},
            {"name": "score", "type": "uint8"},
            {"name": "computeUsed", "type": "uint256"},
        ],
        "name": "updateReputation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "agentId", "type": "bytes32"}],
        "name": "getAgent",
        "outputs": [
            {"name": "capabilities", "type": "string"},
            {"name": "metadataURI", "type": "string"},
            {"name": "registeredAt", "type": "uint256"},
            {"name": "reputationScore", "type": "uint8"},
            {"name": "taskCount", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "agentId", "type": "bytes32"}],
        "name": "getTrustScore",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "agentCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class ERC8004Registry:
    """Interact with AgentForge's ERC-8004 identity contracts on Base Sepolia."""

    def __init__(self, contract_address: str | None = None):
        self.w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
        self.account = Account.from_key(config.PRIVATE_KEY)
        self.contract_address = contract_address
        self.contract = None
        if contract_address:
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=AGENT_REGISTRY_ABI,
            )
        self._tx_hashes: list[str] = []
        self._nonce: int | None = None

    def _send_tx(self, fn) -> str:
        """Build, sign, and send a transaction."""
        if self._nonce is None:
            self._nonce = self.w3.eth.get_transaction_count(self.account.address)
        nonce = self._nonce
        self._nonce += 1
        tx = fn.build_transaction({
            "from": self.account.address,
            "nonce": nonce,
            "gas": 300000,
            "gasPrice": self.w3.eth.gas_price,
            "chainId": config.CHAIN_ID,
        })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        hex_hash = receipt.transactionHash.hex()
        self._tx_hashes.append(hex_hash)
        return hex_hash

    def register_agent(self, agent_id: str, capabilities: str, metadata_uri: str) -> str:
        """Register an agent identity on-chain. Returns tx hash."""
        if not self.contract:
            raise RuntimeError("No contract address set")
        agent_id_bytes = Web3.keccak(text=agent_id)
        fn = self.contract.functions.registerAgent(agent_id_bytes, capabilities, metadata_uri)
        return self._send_tx(fn)

    def update_reputation(self, agent_id: str, task_id: str, outcome: int, score: int, compute_used: int) -> str:
        """Update an agent's reputation after task completion. Returns tx hash."""
        if not self.contract:
            raise RuntimeError("No contract address set")
        agent_id_bytes = Web3.keccak(text=agent_id)
        task_id_bytes = Web3.keccak(text=task_id)
        fn = self.contract.functions.updateReputation(agent_id_bytes, task_id_bytes, outcome, score, compute_used)
        return self._send_tx(fn)

    def get_trust_score(self, agent_id: str) -> int:
        """Read an agent's trust score from chain."""
        if not self.contract:
            return 75
        agent_id_bytes = Web3.keccak(text=agent_id)
        return self.contract.functions.getTrustScore(agent_id_bytes).call()

    @property
    def operator_address(self) -> str:
        return self.account.address

    @property
    def tx_hashes(self) -> list[str]:
        return self._tx_hashes
