import os
from mcp import stdio_client, StdioServerParameters
from strands import Agent
from strands.tools.mcp import MCPClient
from strands.models import BedrockModel


def build_agent(system_prompt: str | None = None, tools: list | None = None) -> Agent:
    model = BedrockModel(
        model_id=os.getenv("MODEL", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    return Agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools,
    )


stdio_mcp_client = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx", args=["awslabs.aws-documentation-mcp-server@latest"]
        )
    )
)

# Create an agent with MCP tools
with stdio_mcp_client:
    # Get the tools from the MCP server
    tools = stdio_mcp_client.list_tools_sync()

    # Create an agent with these tools
    agent = Agent(tools=tools)
    agent("What are the most recent AWS Bedrock features released in 2025?")
