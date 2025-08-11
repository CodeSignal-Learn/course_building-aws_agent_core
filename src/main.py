import os
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Configure Bedrock model from environment
bedrock_model = BedrockModel(
    model_id=os.getenv("MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
    region_name=os.getenv("AWS_REGION", "us-east-1")
)

# Initialize Strands agent with the explicit Bedrock model and system prompt
agent = Agent(
    model=bedrock_model,
    system_prompt="You are a helpful assistant that can answer questions and help with tasks."
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

    # Get the prompt from the payload, or use a default if not provided
    user_prompt = payload.get("prompt", "Hello AgentCore")

    # Ask the agent directly
    response = agent(user_prompt)

    # Return the result as a JSON-serializable dict
    return {"result": str(response)}

# If running locally, start a development server
if __name__ == "__main__":
    app.run()  # Starts the HTTP server on port 8080
