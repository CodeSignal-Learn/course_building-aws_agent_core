import json
import os
import sys
import uuid

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

    # Create a simple guardrail via the control-plane API.
    control = boto3.client(
            "bedrock",
            region_name=region,
            config=Config(
                connect_timeout=5,
                read_timeout=60,
                retries={"max_attempts": 3},
            ),
        )
    try:
        create_resp = control.create_guardrail(
            name=f"demo-guardrail-{uuid.uuid4().hex[:8]}",
            description=(
                "Demo guardrail with content filters, denied topics, and "
                "PII handling"
            ),
            contentPolicyConfig={
                "filtersConfig": [
                    {
                        "type": "HATE",
                        "inputStrength": "HIGH",
                        "outputStrength": "HIGH",
                    },
                    {
                        "type": "VIOLENCE",
                        "inputStrength": "HIGH",
                        "outputStrength": "HIGH",
                    },
                ]
            },
            topicPolicyConfig={
                "topicsConfig": [
                    {
                        "name": "Investment Advice",
                        "definition": (
                            "Providing guidance or recommendations about "
                            "financial investments."
                        ),
                        "examples": [
                            "Should I invest in stock X?",
                            "What are the best investments right now?",
                        ],
                        "type": "DENY",
                    }
                ]
            },
            sensitiveInformationPolicyConfig={
                "piiEntitiesConfig": [
                    {"type": "EMAIL", "action": "ANONYMIZE"},
                    {"type": "PHONE", "action": "ANONYMIZE"},
                ]
            },
            blockedInputMessaging=(
                "Your input contains content that is not allowed."
            ),
            blockedOutputsMessaging=(
                "The response contains content that is not allowed."
            ),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"CreateGuardrail failed: {exc}", file=sys.stderr)
        return 2

    guardrail_id = create_resp.get("guardrailId")
    # Newly created guardrails can be referenced with DRAFT version.
    guardrail_version = "DRAFT"

    # Shopping Assistant: test guardrails on unsafe + PII content
    user_prompt = (
        "Can you provide me investment advice?"
    )

    messages = [{"role": "user", "content": [{"text": user_prompt}]}]

    try:
        result = client.converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig={
                "maxTokens": 300,
                "temperature": 0.2,
                "topP": 0.9,
            },
            guardrailConfig={
                "guardrailIdentifier": guardrail_id,
                "guardrailVersion": guardrail_version,
            },
            system=[
                {
                    "text": (
                        "You are Shopping Assistant. Remove PII and refuse "
                        "dangerous content."
                    )
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Converse failed: {exc}", file=sys.stderr)
        return 1

    # If the guardrail triggers, the model output may be adjusted or blocked
    # with messages/reasons.
    output_message = result.get("output", {}).get("message", {})
    parts = output_message.get("content", [])
    text_chunks = [p.get("text", "") for p in parts]
    print("".join(text_chunks).strip())

    # Optionally, inspect metadata about guardrail actions if present
    if "guardrailAction" in result.get("metrics", {}):
        print(json.dumps(result.get("metrics", {}), indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
