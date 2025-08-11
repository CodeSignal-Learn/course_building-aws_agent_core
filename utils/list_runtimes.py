import os

import boto3

# Get the region from the environment variable
REGION = os.getenv("AWS_REGION", "us-east-1")

# Create AgentCore client
ac = boto3.client("bedrock-agentcore-control", region_name=REGION)


def list_agent_runtimes():
    response = ac.list_agent_runtimes()
    return response.get("agentRuntimes", [])


def print_runtime_summary(runtime: dict):
    print(f"ID: {runtime.get('agentRuntimeId')}")
    print(f"Name: {runtime.get('agentRuntimeName')}")
    print(f"ARN: {runtime.get('agentRuntimeArn')}")
    print(f"Version: {runtime.get('agentRuntimeVersion')}")
    print(f"Status: {runtime.get('status')}")
    print(f"Last Updated At: {runtime.get('lastUpdatedAt')}")


if __name__ == "__main__":
    # List all agent runtimes
    runtimes = list_agent_runtimes()

    if not runtimes:
        print("No AgentCore runtimes found.")
    else:
        print(f"Found the following runtimes in {REGION}:")
        for runtime in runtimes:
            # Print the runtime summary and details
            print_runtime_summary(runtime)

            print("\n" + "-" * 100 + "\n")
