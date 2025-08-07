import os
from crewai import LLM, Agent, Task, Crew, Process
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Create a Bedrock LLM wrapper using environment variables
llm = LLM(
    model=os.getenv("MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_region_name=os.getenv("AWS_REGION")
)

# Define an agent with no tools, just the Bedrock LLM
assistant = Agent(
    role="Friendly Assistant",
    goal="Answer AWS and Bedrock questions",
    backstory="Lives inside AgentCore now!",
    llm=llm
)

# Create the Bedrock AgentCore Runtime app wrapper
app = BedrockAgentCoreApp()

# Mark this function as the entrypoint for the AgentCore runtime
@app.entrypoint
def invoke(payload: dict):
    """
    Receives a payload with a 'prompt' key and runs the CrewAI crew.
    Returns the agent's response in a dictionary.
    """
    
    # Get the prompt from the payload, or use a default if not provided
    user_prompt = payload.get("prompt", "Hello AgentCore")

    # Create a brand-new Task for this turn only
    turn_task = Task(
        agent=assistant,
        description=user_prompt,
        expected_output="An accurate, concise answer."
    )

    # Create a new crew with the current task for this invocation
    current_crew = Crew(
        agents=[assistant],
        tasks=[turn_task],
        process=Process.sequential
    )

    # Run the Crew and get the result
    result = current_crew.kickoff()

    # Return the result as a JSON-serializable dict
    return {"result": result.raw}

# If running locally, start a development server
if __name__ == "__main__":
    app.run()  # Starts the HTTP server on port 8080
