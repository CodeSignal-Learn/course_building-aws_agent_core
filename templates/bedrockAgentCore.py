import json
import os
import shutil
import subprocess

import boto3
from common import (
    create_guardrail,
    setup_complete_knowledge_base,
    attach_custom_policy,
    attach_policy,
)
from enableModel import enable_model

# Configuration
BEDROCK_MODELS = [
    "anthropic.claude-sonnet-4-20250514-v1:0",
    "amazon.titan-embed-text-v2:0",
]
USER_POLICIES = [
    "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
    "arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess",
]
DOCUMENTS_FOLDER = os.path.join(os.getcwd(), "docs")
VECTOR_BUCKET_NAME = "bedrock-vector-bucket"
VECTOR_INDEX_NAME = "bedrock-vector-index"
KB_NAME = "bedrock-knowledge-base"
REGION_NAME = "us-east-1"
ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]


def create_execution_role():
    iam = boto3.client("iam")

    # Create role if it doesn't exist
    try:
        iam.create_role(
            RoleName="AmazonBedrockAgentCoreSDKRuntime",
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
        )
        print("✅ Created IAM role AmazonBedrockAgentCoreSDKRuntime")
    except iam.exceptions.EntityAlreadyExistsException:
        print("✅ IAM role AmazonBedrockAgentCoreSDKRuntime already exists")

    # Ensure execution policy exists and is attached to the role
    policy_name = "AmazonBedrockAgentCoreRuntimeExecutionPolicy"
    policy_json_path = os.path.join(
        os.path.dirname(__file__),
        "policies",
        "BedrockAgentCoreRuntimeExecutionPolicy.json",
    )
    attach_custom_policy(
        policy_name=policy_name,
        policy_json_path=policy_json_path,
        attach_to_type="role",
        attach_to_name="AmazonBedrockAgentCoreSDKRuntime",
        replacements={"{AWS_ACCOUNT_ID}": ACCOUNT_ID},
    )

    return f"arn:aws:iam::{ACCOUNT_ID}:role/AmazonBedrockAgentCoreSDKRuntime"


def configure_agent(
    entrypoint: str = "agent.py",
    name: str = "my_agent",
    region: str = "us-east-1",
    requirements_file: str = "requirements.txt",
    protocol: str = "HTTP",  # or "MCP"
):
    print(shutil.which("pip3"))
    if not shutil.which("agentcore"):
        raise RuntimeError(
            "agentcore CLI not found on PATH. "
            "`pip install bedrock-agentcore-starter-toolkit` first."
        )

    entrypoint_path = os.path.join(os.path.dirname(__file__), entrypoint)
    requirements_path = os.path.join(os.path.dirname(__file__), requirements_file)

    cfg_cmd = [
        "agentcore",
        "configure",
        "--entrypoint",
        entrypoint_path,
        "--name",
        name,
        "--region",
        region,
        "--protocol",
        protocol,
        "--ecr",
        "auto",  # avoids the “Press Enter to auto-create ECR” prompt
        "--requirements-file",
        requirements_path,
        "--disable-otel",  # Disable OpenTelemetry noise
    ]

    # Create execution service role with BedrockAgentCoreRuntimeExecutionPolicy
    execution_role_arn = create_execution_role()
    cfg_cmd += ["--execution-role", execution_role_arn]

    cfg_cmd += ["--authorizer-config", "null"]

    # This will not prompt as long as the above values are sufficient.
    subprocess.run(cfg_cmd, check=True)


def launch_agent(guardrail_id: str):
    launch_cmd = ["agentcore", "launch"]

    # Pass the guardrail ID to the agent as env variable
    launch_cmd += ["--env", f"GUARDRAIL_ID={guardrail_id}"]

    subprocess.run(launch_cmd, check=True)


def main():
    # 1. Grant user policies
    for policy in USER_POLICIES:
        success, _ = attach_policy(
            attach_to_type="user",
            attach_to_name="learner",
            policy_arn=policy,
        )
        if not success:
            print(f"❌ Failed to grant {policy} to learner. Exiting.")
            exit(1)

    # 2. Enable the Bedrock models
    for model in BEDROCK_MODELS:
        result = enable_model(model)
        if result["status"] == "enabled":
            print(f"✅ Bedrock model {model} enabled")
        else:
            print(f"❌ Failed to enable Bedrock model {model}")
            exit(1)

    # 3. Create guardrail
    guardrail = create_guardrail(REGION_NAME)
    if not guardrail:
        print("❌ Failed to create guardrail. Exiting.")
        exit(1)
    else:
        guardrail_id = guardrail["guardrailId"]
        print(f"✅ Guardrail is ready to use with ID: {guardrail_id}")

    # 4. Setup complete knowledge base
    result = setup_complete_knowledge_base(
        documents_folder=DOCUMENTS_FOLDER,
        vector_bucket_name=VECTOR_BUCKET_NAME,
        vector_index_name=VECTOR_INDEX_NAME,
        kb_name=KB_NAME,
        region_name=REGION_NAME,
    )

    # Check if knowledge base setup was successful
    if result:
        knowledge_base_id, vector_index_arn = result
        print("\nKnowledge Base is ready to use!")
        print(f"Knowledge Base ID: {knowledge_base_id}")
        print(f"Vector Index ARN: {vector_index_arn}")
    else:
        print("❌ Failed to create knowledge base. Exiting.")
        exit(1)

    # 5. Configure and then launch agent
    configure_agent(
        entrypoint="agent.py",
        name="my_agent",
        region="us-east-1",
        requirements_file="requirements.txt",
    )
    print("✅ Agent is configured")

    launch_agent(
        guardrail_id=guardrail_id,
    )
    print("✅ Agent is launched")


if __name__ == "__main__":
    main()
