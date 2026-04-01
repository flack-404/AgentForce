import { ethers } from "hardhat";

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying AgentRegistry with:", deployer.address);
  console.log("Balance:", ethers.formatEther(await ethers.provider.getBalance(deployer.address)), "ETH");

  const AgentRegistry = await ethers.getContractFactory("AgentRegistry");
  const registry = await AgentRegistry.deploy();
  await registry.waitForDeployment();

  const addr = await registry.getAddress();
  console.log("AgentRegistry deployed to:", addr);
  console.log("\nUpdate backend/.env with:");
  console.log(`AGENT_REGISTRY=${addr}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
