import os
import time
from typing import List, Tuple

from bedrock_agentcore.memory import MemoryClient


def main() -> int:
    region = os.getenv("AWS_REGION", "us-east-1")
    client = MemoryClient(region_name=region)

    memory = client.create_memory_and_wait(
        name="Course4LongTermMemory",
        strategies=[
            {
                "summaryMemoryStrategy": {
                    "name": "SessionSummarizer",
                    "namespaces": ["/summaries/{actorId}/{sessionId}"]
                }
            }
        ],
    )
    memory_id = memory.get("id")
    print(f"Created long-term memory: {memory_id}")

    actor_id = os.getenv("ACTOR_ID", "User84")
    session_id = os.getenv("SESSION_ID", "OrderSupportSession1")

    messages: List[Tuple[str, str]] = [
        ("Hi, I'm having trouble with my order #12345", "USER"),
        ("I'm sorry to hear that. Let me look up your order.", "ASSISTANT"),
        ("lookup_order(order_id='12345')", "TOOL"),
        (
            "I see your order was shipped 3 days ago. What specific issue are you experiencing?",
            "ASSISTANT",
        ),
        ("The package arrived damaged", "USER"),
    ]

    client.create_event(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
        messages=messages,
    )

    # Allow strategy processing time
    time.sleep(60)

    summaries = client.retrieve_memories(
        memory_id=memory_id,
        namespace=f"/summaries/{actor_id}/{session_id}",
        query="What happened in this session?",
    )

    print("Retrieved summaries:")
    for item in summaries:
        print(item)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
