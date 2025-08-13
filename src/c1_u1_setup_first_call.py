import os
import sys
from botocore.config import Config

import boto3


def main() -> int:
    region = os.getenv("AWS_REGION", "us-east-1")
    # Shopping Assistant: first Bedrock call via CLI prompt
    model_id = os.getenv("MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0")

    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
    )

    system_prompt = (
        "You are Shopping Assistant. Be concise and helpful when answering "
        "product questions."
    )
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": (
                        "Find a budget laptop under $800 and suggest 2 key "
                        "specs to compare."
                    )
                }
            ],
        },
    ]

    try:
        response = client.converse(
            modelId=model_id,
            messages=messages,
            system=[{"text": system_prompt}],
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Converse call failed: {exc}", file=sys.stderr)
        return 1

    output_message = response.get("output", {}).get("message", {})
    parts = output_message.get("content", [])
    text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
    print("".join(text_chunks).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
