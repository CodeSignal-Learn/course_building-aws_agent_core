import os
from typing import Dict

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel


def build_agent(system_prompt: str | None = None) -> Agent:
    model = BedrockModel(
        model_id=os.getenv("MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    return Agent(
        model=model,
        system_prompt=(system_prompt),
    )


app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: Dict):
    prompt = payload.get("prompt", "Hello from Shopping Assistant")
    agent = build_agent()
    result = agent(prompt)
    return {"result": str(result)}


if __name__ == "__main__":
    app.run()
