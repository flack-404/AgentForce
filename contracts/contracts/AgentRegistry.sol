// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AgentRegistry - ERC-8004 Compatible Agent Identity & Reputation
 * @notice Registers autonomous agent identities with capabilities, metadata, and reputation tracking.
 * @dev Part of AgentForge multi-agent swarm system.
 */
contract AgentRegistry {
    struct Agent {
        string capabilities;
        string metadataURI;
        uint256 registeredAt;
        uint8 reputationScore;
        uint256 taskCount;
        bool exists;
    }

    struct ReputationUpdate {
        bytes32 taskId;
        uint8 outcome; // 0 = SUCCESS, 1 = PARTIAL, 2 = FAILURE
        uint8 score;
        uint256 computeUsed;
        uint256 timestamp;
    }

    address public owner;
    uint256 public agentCount;

    mapping(bytes32 => Agent) public agents;
    mapping(bytes32 => ReputationUpdate[]) public reputationHistory;
    mapping(bytes32 => mapping(bytes32 => bool)) public validations; // agentId => validatorId => validated

    event AgentRegistered(bytes32 indexed agentId, string capabilities, string metadataURI);
    event ReputationUpdated(bytes32 indexed agentId, bytes32 indexed taskId, uint8 outcome, uint8 score);
    event AgentValidated(bytes32 indexed agentId, bytes32 indexed validatorId);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function registerAgent(
        bytes32 agentId,
        string calldata capabilities,
        string calldata metadataURI
    ) external onlyOwner {
        if (!agents[agentId].exists) {
            agentCount++;
        }
        agents[agentId] = Agent({
            capabilities: capabilities,
            metadataURI: metadataURI,
            registeredAt: block.timestamp,
            reputationScore: 75, // Initial reputation
            taskCount: 0,
            exists: true
        });
        emit AgentRegistered(agentId, capabilities, metadataURI);
    }

    function updateReputation(
        bytes32 agentId,
        bytes32 taskId,
        uint8 outcome,
        uint8 score,
        uint256 computeUsed
    ) external onlyOwner {
        require(agents[agentId].exists, "Agent not registered");
        require(score <= 100, "Score must be <= 100");

        agents[agentId].taskCount++;

        // Weighted moving average: new_rep = (old_rep * taskCount + score) / (taskCount + 1)
        uint256 tc = agents[agentId].taskCount;
        uint256 oldRep = agents[agentId].reputationScore;
        agents[agentId].reputationScore = uint8((oldRep * (tc - 1) + score) / tc);

        reputationHistory[agentId].push(ReputationUpdate({
            taskId: taskId,
            outcome: outcome,
            score: score,
            computeUsed: computeUsed,
            timestamp: block.timestamp
        }));

        emit ReputationUpdated(agentId, taskId, outcome, score);
    }

    function validateAgent(bytes32 agentId, bytes32 validatorId) external onlyOwner {
        require(agents[agentId].exists, "Agent not registered");
        validations[agentId][validatorId] = true;
        emit AgentValidated(agentId, validatorId);
    }

    function getAgent(bytes32 agentId) external view returns (
        string memory capabilities,
        string memory metadataURI,
        uint256 registeredAt,
        uint8 reputationScore,
        uint256 taskCount
    ) {
        Agent storage a = agents[agentId];
        return (a.capabilities, a.metadataURI, a.registeredAt, a.reputationScore, a.taskCount);
    }

    function getTrustScore(bytes32 agentId) external view returns (uint8) {
        if (!agents[agentId].exists) return 0;
        return agents[agentId].reputationScore;
    }

    function getReputationHistory(bytes32 agentId) external view returns (ReputationUpdate[] memory) {
        return reputationHistory[agentId];
    }

    function isValidated(bytes32 agentId, bytes32 validatorId) external view returns (bool) {
        return validations[agentId][validatorId];
    }
}
