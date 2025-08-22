import os
import time

from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.models import BedrockModel
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider


def build_agent(tools: list | None = None) -> Agent:
    model = BedrockModel(
        model_id=os.getenv("MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    return Agent(model=model, tools=tools)


def main() -> int:
    region = os.getenv("AWS_REGION", "us-east-1")
    client = MemoryClient(region_name=region)

    memory = client.create_memory_and_wait(
        name="Course4LongTermMemory",
        strategies=[
            {
                "summaryMemoryStrategy": {
                    "name": "SessionSummarizer",
                    "namespaces": ["/summaries/{actorId}/{sessionId}"],
                }
            }
        ],
    )
    memory_id = memory.get("id")
    print(f"Created long-term memory: {memory_id}")

    actor_id = os.getenv("ACTOR_ID", "User84")
    session_id = os.getenv("SESSION_ID", "OrderSupportSession1")

    provider = AgentCoreMemoryToolProvider(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
        namespace=f"/summaries/{actor_id}/{session_id}",
    )
    agent = build_agent(tools=provider.tools)

    # Record a session; summarization strategy will run server-side
    agent.tool.agent_core_memory(
        action="record",
        content=(
            "USER: I need a secure architecture to build an AWS RAG app on Bedrock. "
            "ASSISTANT: We can use Bedrock Knowledge Bases with S3 vectors and a retrieval tool. "
            "TOOL: kb_create_with_s3_vectors(bucket='docs-bucket', index='kb-index') "
            "ASSISTANT: Ensure IAM roles allow Bedrock, S3, and KMS if using encryption. "
            "USER: Also need guidance on VPC endpoints and private network access. "
            "ASSISTANT: Use interface endpoints for Bedrock and S3 Gateway endpoint; "
            "restrict egress via NAT policies."
        ),
    )

    # Allow strategy processing time
    time.sleep(60)

    # Retrieve generated summaries via the tool
    summaries = agent.tool.agent_core_memory(
        action="retrieve",
        query="RAG architecture guidance Bedrock KB, IAM, VPC endpoints",
    )
    print(str(summaries))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
