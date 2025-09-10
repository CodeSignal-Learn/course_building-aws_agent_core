import json
import os
import shutil
import subprocess
import time

import boto3
from common import (
    create_guardrail,
    setup_complete_knowledge_base,
    attach_custom_policy,
    attach_policy,
)
from enableModel import enable_model

# Configuration Constants
REGION_NAME = "us-east-1"
ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]

# Agent Configuration
AGENT_NAME = "my_agent"
AGENT_ENTRYPOINT = "agent.py"
REQUIREMENTS_FILE = "requirements.txt"
PROTOCOL = "HTTP"  # or "MCP"

# IAM Configuration
EXECUTION_ROLE_NAME = "AmazonBedrockAgentCoreSDKRuntime"
EXECUTION_POLICY_NAME = "AmazonBedrockAgentCoreRuntimeExecutionPolicy"
EXECUTION_POLICY_FILE = "BedrockAgentCoreRuntimeExecutionPolicy.json"
USERNAME = "learner"

# S3 Configuration
CONFIG_BACKUP_BUCKET_NAME = f"bedrock-agentcore-config-backup-{ACCOUNT_ID}"
# You can download it back using the following command:
# aws s3 cp s3://bedrock-agentcore-config-backup-$(aws sts get-caller-identity --query Account --output text)/.bedrock_agentcore.yaml .bedrock_agentcore.yaml

# Knowledge Base Configuration
KB_NAME = "bedrock-knowledge-base"
VECTOR_BUCKET_NAME = "bedrock-vector-bucket"
VECTOR_INDEX_NAME = "bedrock-vector-index"
DOCUMENTS_FOLDER = os.path.join(os.getcwd(), "docs")

# Bedrock Models
BEDROCK_MODELS = [
    "anthropic.claude-sonnet-4-20250514-v1:0",
    "amazon.titan-embed-text-v2:0",
]

# User Policies
USER_POLICIES = [
    "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
    "arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess",
    "arn:aws:iam::aws:policy/AWSCodeBuildAdminAccess"
]

# Directories
POLICIES_DIR = os.path.join(os.path.dirname(__file__), "policies")


def cleanup_existing_resources():
    """Clean up existing AgentCore resources before creating new ones"""
    print("🧹 Cleaning up existing AgentCore resources...")
    
    try:
        # 1. Cleanup Bedrock Agent Core runtime
        try:
            bedrock_agentcore_client = boto3.client('bedrock-agentcore-control', region_name=REGION_NAME)
            response = bedrock_agentcore_client.list_agent_runtimes()
            agent_runtimes = response.get("agentRuntimes", [])
            
            for runtime in agent_runtimes:
                runtime_name = runtime.get("name", "")
                runtime_id = runtime.get("agentRuntimeId", "")
                
                # Check if agent_name matches either the name or is at the start of the runtime ID
                if (AGENT_NAME in runtime_name.lower()) or (runtime_id.lower().startswith(AGENT_NAME.lower())):
                     try:
                         bedrock_agentcore_client.delete_agent_runtime(agentRuntimeId=runtime_id)
                         print(f"✅ Initiated deletion of agent runtime: {runtime_id}")
                         
                         # Wait for deletion to complete
                         print(f"⏳ Waiting for agent runtime {runtime_id} to be fully deleted...")
                         max_wait_time = 300  # 5 minutes
                         wait_interval = 10   # 10 seconds
                         elapsed_time = 0
                         
                         while elapsed_time < max_wait_time:
                             try:
                                 # Try to get the runtime - if it doesn't exist, deletion is complete
                                 bedrock_agentcore_client.get_agent_runtime(agentRuntimeId=runtime_id)
                                 print(f"⏳ Still deleting... ({elapsed_time}s elapsed)")
                                 time.sleep(wait_interval)
                                 elapsed_time += wait_interval
                             except Exception:
                                 # Runtime not found = deletion complete
                                 print(f"✅ Agent runtime {runtime_id} fully deleted")
                                 break
                         
                         if elapsed_time >= max_wait_time:
                             print(f"⚠️  Timeout waiting for agent runtime {runtime_id} deletion")
                             
                     except Exception as e:
                         if "DELETING" in str(e):
                             print(f"⚠️  Agent runtime {runtime_id} is already being deleted")
                         else:
                             print(f"⚠️  Could not delete agent runtime {runtime_id}: {e}")
                        
        except Exception as e:
            print(f"⚠️  Could not cleanup agent runtimes: {e}")
        
        # 2. Cleanup ECR repository
        try:
            ecr_client = boto3.client("ecr", region_name=REGION_NAME)
            all_repos = ecr_client.describe_repositories()
            repositories = all_repos.get('repositories', [])
            
            for repo in repositories:
                repo_name = repo.get('repositoryName', '')
                if AGENT_NAME in repo_name.lower() or repo_name.lower().startswith(f"bedrock-agentcore-{AGENT_NAME}".lower()):
                    try:
                        # Delete all images first
                        response = ecr_client.list_images(repositoryName=repo_name)
                        image_ids = response.get('imageIds', [])
                        
                        if image_ids:
                            ecr_client.batch_delete_image(repositoryName=repo_name, imageIds=image_ids)
                        
                        # Delete the repository
                        ecr_client.delete_repository(repositoryName=repo_name, force=True)
                        print(f"✅ Deleted existing ECR repository: {repo_name}")
                    except Exception as e:
                        print(f"⚠️  Could not delete ECR repository {repo_name}: {e}")
                        
        except Exception as e:
            print(f"⚠️  Could not cleanup ECR repositories: {e}")
        
        # 3. Cleanup CodeBuild project
        try:
            codebuild_client = boto3.client("codebuild", region_name=REGION_NAME)
            response = codebuild_client.list_projects()
            project_names = response.get('projects', [])
            project_name = f"bedrock-agentcore-{AGENT_NAME}-builder"
            
            if project_name in project_names:
                codebuild_client.delete_project(name=project_name)
                print(f"✅ Deleted existing CodeBuild project: {project_name}")
                
        except Exception as e:
            print(f"⚠️  Could not cleanup CodeBuild project: {e}")
        
        # 4. Cleanup config backup bucket
        try:
            s3_client = boto3.client("s3", region_name=REGION_NAME)
            
            try:
                s3_client.head_bucket(Bucket=CONFIG_BACKUP_BUCKET_NAME)
                
                # Delete all objects first
                response = s3_client.list_objects_v2(Bucket=CONFIG_BACKUP_BUCKET_NAME)
                objects = response.get('Contents', [])
                
                if objects:
                    delete_objects = [{'Key': obj['Key']} for obj in objects]
                    s3_client.delete_objects(
                        Bucket=CONFIG_BACKUP_BUCKET_NAME,
                        Delete={'Objects': delete_objects}
                    )
                
                # Delete the bucket
                s3_client.delete_bucket(Bucket=CONFIG_BACKUP_BUCKET_NAME)
                print(f"✅ Deleted existing config backup bucket: {CONFIG_BACKUP_BUCKET_NAME}")
                
            except s3_client.exceptions.NoSuchBucket:
                pass  # Bucket doesn't exist, which is fine
                
        except Exception as e:
            print(f"⚠️  Could not cleanup config backup bucket: {e}")
            
        print("✅ Cleanup completed\n")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        print("⚠️  Continuing with deployment despite cleanup errors...\n")


def create_execution_role():
    iam = boto3.client("iam")

    # Create role if it doesn't exist
    try:
        iam.create_role(
            RoleName=EXECUTION_ROLE_NAME,
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
        print(f"✅ Created IAM role {EXECUTION_ROLE_NAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"✅ IAM role {EXECUTION_ROLE_NAME} already exists")

    # Ensure execution policy exists and is attached to the role
    policy_json_path = os.path.join(POLICIES_DIR, EXECUTION_POLICY_FILE)
    attach_custom_policy(
        policy_name=EXECUTION_POLICY_NAME,
        policy_json_path=policy_json_path,
        attach_to_type="role",
        attach_to_name=EXECUTION_ROLE_NAME,
        replacements={"{AWS_ACCOUNT_ID}": ACCOUNT_ID},
    )

    return f"arn:aws:iam::{ACCOUNT_ID}:role/{EXECUTION_ROLE_NAME}"


def configure_agent(
    entrypoint: str = AGENT_ENTRYPOINT,
    name: str = AGENT_NAME,
    region: str = REGION_NAME,
    requirements_file: str = REQUIREMENTS_FILE,
    protocol: str = PROTOCOL,
):
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


def create_config_backup_bucket(bucket_name: str = CONFIG_BACKUP_BUCKET_NAME):
    """Create S3 bucket and upload the .bedrock_agentcore.yaml configuration file"""
    try:
        s3_client = boto3.client('s3', region_name=REGION_NAME)
        
        # Create the bucket
        try:
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"✅ Created S3 bucket: {bucket_name}")
        except s3_client.exceptions.BucketAlreadyOwnedByYou:
            print(f"✅ S3 bucket {bucket_name} already exists and is owned by you")
        except s3_client.exceptions.BucketAlreadyExists:
            print(f"⚠️  S3 bucket {bucket_name} already exists (owned by someone else)")
            return False
        
        # Upload the .bedrock_agentcore.yaml file
        config_file_path = os.path.join(os.path.dirname(__file__), ".bedrock_agentcore.yaml")
        
        if os.path.exists(config_file_path):
            s3_client.upload_file(
                config_file_path, 
                bucket_name, 
                ".bedrock_agentcore.yaml"
            )
            print(f"✅ Uploaded .bedrock_agentcore.yaml to bucket: {bucket_name}")
            return True
        else:
            print("⚠️  .bedrock_agentcore.yaml file not found, skipping upload")
            return False
            
    except Exception as e:
        print(f"❌ Error creating config backup bucket: {e}")
        return False


def launch_agent(guardrail_id: str, knowledge_base_id: str):
    launch_cmd = [
        "agentcore", 
        "launch",
        "--env", f"GUARDRAIL_ID={guardrail_id}",
        "--env", f"KNOWLEDGE_BASE_ID={knowledge_base_id}"
    ]

    subprocess.run(launch_cmd, check=True)


def main():
    # 0. Cleanup existing resources first
    cleanup_existing_resources()
    
    # 1. Grant user policies
    for policy in USER_POLICIES:
        success, _ = attach_policy(
            attach_to_type="user",
            attach_to_name=USERNAME,
            policy_arn=policy,
        )
        if not success:
            print(f"❌ Failed to grant {policy} to {USERNAME}. Exiting.")
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
    configure_agent()
    print("✅ Agent is configured")

    # 6. Create backup bucket and upload config
    create_config_backup_bucket()

    # 7. Launch agent
    launch_agent(
        guardrail_id=guardrail_id,
        knowledge_base_id=knowledge_base_id,
    )
    print("✅ Agent is launched")


if __name__ == "__main__":
    main()
