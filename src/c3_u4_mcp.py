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
    agent = build_agent(tools=tools)
    q = """
    I need to setup a Bedrock Knowledge Base via AWS SDK (boto3) from scratch.
    I need to know the precise and detailed steps to do it. Context and requirements:
    - We want to use S3 vectors to store the documents.
    - You can assume AWS credentials and required environment variables are set up.
    - You can assume python dependencies are installed and model access is correctly configured.
    - You can assume the correct IAM permissions are set up.
    - We must do everything via code, no console or CLI.
    - Keep it as simple as possible.
    - Focus on showing a few main steps:
        - Create a S3 bucket.
        - Upload documents to the S3 bucket.
        - Create a Bedrock Knowledge Base.
        - Connect the S3 bucket to the Bedrock Knowledge Base.
        - Query the Bedrock Knowledge Base.
    - Do not return multiple snippets for each step, just a single code snippet with all steps.
    - Also include textual explanation of the steps.
    """
    agent(q)
