import os
from strands import Agent
from strands.models import BedrockModel
from strands_tools import calculator, retrieve
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Define the Bedrock model ID
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"

# Read guardrail info from environment variables
GUARDRAIL_ID = os.getenv("GUARDRAIL_ID")
GUARDRAIL_VERSION = os.getenv("GUARDRAIL_VERSION", "DRAFT")

# Create a Bedrock model with guardrail configuration
model = BedrockModel(
    model_id=MODEL_ID,
    guardrail_id=GUARDRAIL_ID,
    guardrail_version=GUARDRAIL_VERSION
)

# Define the system prompt
system_prompt = "You are an AWS Technical Assistant. Provide clear, accurate information about AWS services."

# Create an agent with both calculator and retrieve tools
agent = Agent(
    model=model,
    system_prompt=system_prompt,
    tools=[calculator, retrieve]
)

# Create the Bedrock AgentCore Runtime app wrapper
app = BedrockAgentCoreApp()

# Mark this function as the entrypoint for the AgentCore runtime
@app.entrypoint
def invoke(payload: dict):
    """
    Receives a payload with a 'prompt' key and asks the Strands agent.
    Returns the agent's response in a dictionary.
    """

    # Get the prompt from the payload
    user_prompt = payload.get("prompt")

    # Ask the agent directly
    response = agent(user_prompt)

    # Return the result as a JSON-serializable dict
    return {"result": str(response)}

# If running locally, start a development server
if __name__ == "__main__":
    app.run()  # Starts the HTTP server on port 8080