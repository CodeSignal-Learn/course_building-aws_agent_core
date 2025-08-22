import os
from time import sleep

from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.models import BedrockModel
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider


def build_agent(tools: list | None = None) -> Agent:
    model = BedrockModel(
        model_id=os.getenv(
            "MODEL",
            "us.anthropic.claude-sonnet-4-20250514-v1:0",
        ),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    return Agent(model=model, tools=tools)


def delete_memory_if_exists(memory_name: str, region: str) -> None:
    client = MemoryClient(region_name=region)
    mem = [
        memory for memory in client.list_memories() if "ShortTermMemory" in memory.get("id")
    ]
    if mem:
        client.delete_memory(memory_id=mem[0].get("id"))


def main() -> int:
    region = os.getenv("AWS_REGION", "us-east-1")
    client = MemoryClient(region_name=region)
    delete_memory_if_exists(memory_name="ShortTermMemory", region=region)
    memory = client.create_memory(
        name="ShortTermMemory",
        description="Short-term memory for session context",
    )
    memory_id = memory.get("id")
    print(f"Created memory: {memory_id}")
    sleep(3)

    actor_id = os.getenv("ACTOR_ID", "User42")
    session_id = os.getenv("SESSION_ID", "DemoSession1")

    provider = AgentCoreMemoryToolProvider(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
        namespace="default",
        region=region,
    )
    agent = build_agent(tools=provider.tools)

    # Record a short interaction into AgentCore Memory via Strands tool
    agent.tool.agent_core_memory(
        action="record",
        content=(
            "USER: I need help enabling access to Amazon Bedrock models in us-east-1. "
            "ASSISTANT: You request model access per provider and region via console or API. "
            "TOOL: bedrock_list_foundation_models(region='us-east-1') "
            "ASSISTANT: Claude Sonnet is available; confirm IAM permissions and service quotas."
        ),
    )

    # Retrieve memory records for quick recall
    results = agent.tool.agent_core_memory(
        action="retrieve",
        query="bedrock model access steps",
    )
    print(str(results))

    return 0


if __name__ == "__main__":
    provider = AgentCoreMemoryToolProvider(
        memory_id="ShortTermMemory-vNvXoRHXts",  # Required
        actor_id="User42",        # Required
        session_id="DemoSession1",   # Required
        namespace="default",        # Required,
        region='us-east-1'
    )

    agent = Agent(tools=provider.tools)

    # Create a memory using the default IDs from initialization
    agent.tool.agent_core_memory(
        action="record",
        content="Hello, Remeber that my current hobby is knitting?"
    )

    # Search memory records using the default namespace from initialization
    agent.tool.agent_core_memory(
        action="retrieve",
        query="user preferences"
    )
    raise SystemExit(main())
