import os
from typing import List, Tuple

from bedrock_agentcore.memory import MemoryClient


def main() -> int:
    region = os.getenv("AWS_REGION", "us-east-1")
    client = MemoryClient(region_name=region)

    memory = client.create_memory(
        name="Course4ShortTermMemory",
        description="Short-term memory for session context",
    )
    memory_id = memory.get("id")
    print(f"Created memory: {memory_id}")

    actor_id = os.getenv("ACTOR_ID", "User42")
    session_id = os.getenv("SESSION_ID", "DemoSession1")

    messages: List[Tuple[str, str]] = [
        ("Hi, I need help with my order.", "USER"),
        ("Sure, what's your order number?", "ASSISTANT"),
        ("lookup_order(order_id='A-987')", "TOOL"),
        ("Found your order, it shipped yesterday.", "ASSISTANT"),
    ]

    client.create_event(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
        messages=messages,
    )

    conversations = client.list_events(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
        max_results=10,
    )
    print("Conversation events:")
    for item in conversations:
        print(item)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
