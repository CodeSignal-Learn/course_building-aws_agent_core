import os
import sys
from typing import Any, Dict

from botocore.config import Config
import boto3


def choose_model() -> str:
    # Shopping Assistant: pick a model via env override
    return os.getenv("MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0")


def main() -> int:
    region = os.getenv("AWS_REGION", "us-east-1")
    model_id = choose_model()

    # Safe defaults
    inference_defaults: Dict[str, Any] = {
        "maxTokens": int(os.getenv("MAX_TOKENS", "512")),
        "temperature": float(os.getenv("TEMPERATURE", "0.3")),
        "topP": float(os.getenv("TOP_P", "0.9")),
    }

    # Timeouts and retries
    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(
            connect_timeout=int(os.getenv("CONNECT_TIMEOUT", "5")),
            read_timeout=int(os.getenv("READ_TIMEOUT", "60")),
            retries={
                "max_attempts": int(os.getenv("MAX_ATTEMPTS", "4")),
                "mode": os.getenv("RETRY_MODE", "standard"),
            },
        ),
    )

    system_prompt = "You are Shopping Assistant. Keep outputs factual and concise."
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": (
                        "Explain temperature vs top-p briefly and suggest "
                        "safe defaults for shopping Q&A."
                    )
                }
            ],
        },
    ]

    try:
        result = client.converse(
            modelId=model_id,
            messages=messages,
            system=[{"text": system_prompt}],
            inferenceConfig=inference_defaults,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Converse failed: {exc}", file=sys.stderr)
        return 1

    content_parts = result.get("output", {}).get("message", {}).get("content", [])
    text = "".join(part.get("text", "") for part in content_parts)
    print(text.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
