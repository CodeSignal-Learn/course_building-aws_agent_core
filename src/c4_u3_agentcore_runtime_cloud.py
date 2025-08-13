from typing import Dict

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from .c4_u2_agentcore_runtime_local import build_agent


app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: Dict):
    prompt = payload.get("prompt", "Hello from Cloud Runtime")
    agent = build_agent()
    result = agent(prompt)
    return {"result": str(result)}


if __name__ == "__main__":
    app.run()
