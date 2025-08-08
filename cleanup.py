import os
import json

import boto3

# Get the region from the environment variable
REGION = os.getenv("AWS_REGION", "us-east-1")

# Create AgentCore client
ac = boto3.client("bedrock-agentcore-control", region_name=REGION)
# Create ECR client
ecr = boto3.client("ecr", region_name=REGION)
# Create CodeBuild client
codebuild = boto3.client("codebuild", region_name=REGION)

def list_agent_runtimes():
    response = ac.list_agent_runtimes()
    return response.get("agentRuntimes", [])

def delete_agent_runtime(runtime_id):
    response = ac.delete_agent_runtime(agentRuntimeId=runtime_id)
    return response["status"]


def delete_ecr_repository_for_app(app_name):
    repository_name = f"bedrock-agentcore-{app_name}"
    try:
        ecr.delete_repository(repositoryName=repository_name, force=True)
        print(f"Deleted ECR repo: {repository_name}")
    except Exception as error:
        print(f"Skip ECR delete for {repository_name}: {error}")


def delete_codebuild_project_for_app(app_name):
    project_name = f"bedrock-agentcore-{app_name}-builder"
    try:
        codebuild.delete_project(name=project_name)
        print(f"Deleted CodeBuild project: {project_name}")
    except Exception as error:
        print(f"Skip CodeBuild delete for {project_name}: {error}")


def delete_codebuild_project_by_name(project_name):
    try:
        codebuild.delete_project(name=project_name)
        print(f"Deleted CodeBuild project: {project_name}")
    except Exception as error:
        print(f"Skip CodeBuild delete for {project_name}: {error}")

def print_runtime_summary(runtime: dict):
    print(f"ID: {runtime.get('agentRuntimeId')}")
    print(f"Name: {runtime.get('agentRuntimeName')}")
    print(f"ARN: {runtime.get('agentRuntimeArn')}")
    print(f"Version: {runtime.get('agentRuntimeVersion')}")
    print(f"Status: {runtime.get('status')}")
    print(f"Last Updated At: {runtime.get('lastUpdatedAt')}")

def print_runtime_details(runtime_id: str):
    """Attempt to fetch full runtime details, which may include artifact info like containerUri."""
    resp = ac.get_agent_runtime(agentRuntimeId=runtime_id)

    print("Runtime Details:")
    print(json.dumps(resp, indent=2))


if __name__ == "__main__":
    # List all agent runtimes
    runtimes = list_agent_runtimes()

    if not runtimes:
        print("No AgentCore runtimes found.")
    else:
        print(f"Region: {REGION}")
        print("Found the following runtimes:")
        for runtime in runtimes:
            # Print the runtime summary and details
            print_runtime_summary(runtime)

            # Get the runtime ID and app name
            runtime_id = runtime.get('agentRuntimeId')
            app_name = runtime.get('agentRuntimeName')
            status = runtime.get('status')

            if status != 'DELETING':
                # Delete the agent runtime
                print(f"Deleting runtime {runtime_id}")
                new_status = delete_agent_runtime(runtime_id)
                print(f"Status after deletion: {new_status}")

            delete_ecr_repository_for_app(app_name)
            delete_codebuild_project_for_app(app_name)

            print("\n" + "-" * 100 + "\n")
