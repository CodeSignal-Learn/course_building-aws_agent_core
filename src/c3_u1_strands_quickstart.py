import os

from strands import Agent
from strands.models import BedrockModel
from pydantic import BaseModel, Field


class ProductInfo(BaseModel):
    """Complete product information."""

    name: str = Field(description="The name of the product")
    price: int = Field(description="The price of the product")
    category: str = Field(description="The category of the product")


def build_agent(system_prompt: str | None = None) -> Agent:
    model = BedrockModel(
        model_id=os.getenv("MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    return Agent(
        model=model,
        system_prompt=system_prompt,
    )


def main() -> int:
    agent = build_agent("You are an helpful Shopping Assistant.")
    print(agent("Hello world!"))
    print(
        agent.structured_output(
            ProductInfo,
            "The product is a laptop, the price is 1000, the category is electronics",
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
