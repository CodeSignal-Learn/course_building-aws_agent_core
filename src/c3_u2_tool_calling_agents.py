import os

from strands import Agent
from strands.models import BedrockModel
from strands_tools import calculator


def build_agent(system_prompt: str | None = None) -> Agent:
    model = BedrockModel(
        model_id=os.getenv(
            "MODEL",
            "us.anthropic.claude-sonnet-4-20250514-v1:0",
        ),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    return Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[calculator],
    )


def main() -> int:
    agent = build_agent(
        (
            "You are a Checkout Assistant. Always use the calculator tool for "
            "any arithmetic. When asked for a final price after a discount, "
            "sum the cart item prices, then apply the discount using: final = "
            "sum(prices) * (1 - discount)."
        )
    )

    result = agent(
        "I have items in my cart priced 29.99, 54.50, and 12.00 dollars. "
        "What is the final price after applying a 15% discount?"
    )
    print(str(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
