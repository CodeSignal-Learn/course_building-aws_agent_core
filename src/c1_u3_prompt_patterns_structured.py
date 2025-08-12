import json
import os
import sys
from typing import Any, Dict

from botocore.config import Config
import boto3


def main() -> int:
    region = os.getenv("AWS_REGION", "us-east-1")
    model_id = os.getenv(
        "MODEL",
        "us.anthropic.claude-sonnet-4-20250514-v1:0",
    )

    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(
            connect_timeout=5,
            read_timeout=60,
            retries={"max_attempts": 3},
        ),
    )

    # Shopping Assistant: intent classification + filters schema
    system_instruction = (
        "You are Shopping Assistant. Return ONLY valid JSON for intent, "
        "reply, and filters."
    )
    user_request = (
        "User: I'm looking for wireless earbuds under $150, preferably by "
        "Anker or Sony."
    )

    schema_hint: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "intent": {"type": "string"},
            "reply": {"type": "string"},
            "filters": {
                "type": "object",
                "properties": {
                    "brand": {"type": "string"},
                    "category": {"type": "string"},
                    "price_min": {"type": "number"},
                    "price_max": {"type": "number"},
                },
                "additionalProperties": False,
            },
        },
        "required": ["intent", "reply"],
        "additionalProperties": False,
    }

    # Use correct approach: pass system via the `system` parameter to converse
    system_parts = [
        {"text": system_instruction},
        {"text": f"Schema: {json.dumps(schema_hint)}"},
        {"text": "Respond with ONLY the JSON. No prose."},
    ]
    messages = [
        {"role": "user", "content": [{"text": user_request}]},
    ]

    try:
        result = client.converse(
            modelId=model_id,
            messages=messages,
            system=system_parts,
            inferenceConfig={
                "maxTokens": 400,
                "temperature": 0.2,
                "topP": 0.9,
            },
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Converse failed: {exc}", file=sys.stderr)
        return 1

    parts = result.get("output", {}).get("message", {}).get("content", [])
    text = "".join(p.get("text", "") for p in parts)

    # Try to parse JSON; if it fails, print the raw output for debugging.
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        print(text)
        return 2

    print(json.dumps(parsed, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
