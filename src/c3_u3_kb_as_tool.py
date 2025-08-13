import os

from strands import Agent
from strands.models import BedrockModel
from strands_tools import calculator, retrieve


def build_agent(system_prompt: str | None = None) -> Agent:
    model = BedrockModel(
        model_id=os.getenv("MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    return Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[calculator, retrieve],
    )


def main() -> int:
    agent = build_agent(
        (
            "You are Shopping Assistant. If user asks to find products, call "
            "the search_products tool."
        )
    )

    # Basic search with default knowledge base and region
    results = agent.tool.retrieve(text="What categories of products are available?")
    print(str(results))

    # Advanced search with custom parameters
    results = agent.tool.retrieve(
        text="recent electronics products",
        numberOfResults=5,
        score=0.7,
        knowledgeBaseId="custom-kb-id",
        region="us-east-1",
        retrieveFilter={
            "andAll": [
                {"equals": {"key": "category", "value": "electronics"}},
                {"greaterThan": {"key": "year", "value": "2022"}},
            ]
        },
    )
    print(str(results))

    # Calculate the average price of electronics products
    results = agent(
        "What is the average price of electronics products released after 2022?"
    )
    print(str(results))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
