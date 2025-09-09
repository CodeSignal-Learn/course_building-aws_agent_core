#!/usr/bin/env python3
"""
Cleanup script to remove all resources created by bedrockKnowledgeBase.py and bedrockAgentCore.py

This script will remove:
1. Bedrock Agent Core (deployed agent)
2. ECR Repository (created by agentcore CLI)
3. CodeBuild Project (created by agentcore CLI)
4. S3 Config Backup Bucket (stores .bedrock_agentcore.yaml)
5. Bedrock Knowledge Base
6. IAM roles and custom policies (kb-service-role and AmazonBedrockAgentCoreSDKRuntime)
7. S3 Vectors index and bucket
8. Guardrail
9. IAM policies from users (optional)

Note: This does NOT disable Bedrock models as they might be used by other resources.
"""

import boto3
import time
from botocore.exceptions import ClientError

# Configuration Constants
REGION_NAME = "us-east-1"
AGENT_NAME = "my_agent"
KB_NAME = "bedrock-knowledge-base"
KB_ROLE_NAME = "kb-service-role"
AGENT_CORE_ROLE_NAME = "AmazonBedrockAgentCoreSDKRuntime"
AGENT_CORE_POLICY_NAME = "AmazonBedrockAgentCoreRuntimeExecutionPolicy"
VECTOR_BUCKET_NAME = "bedrock-vector-bucket"
VECTOR_INDEX_NAME = "bedrock-vector-index"
GUARDRAIL_NAME = "aws-assistant-guardrail"
CONFIG_BACKUP_BUCKET_NAME = "bedrock-agentcore-config-backup"
USERNAME = "learner"

# User policies to clean up
USER_POLICIES = [
    "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
    "arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess",
    "arn:aws:iam::aws:policy/AWSCodeBuildAdminAccess"
]


def cleanup_bedrock_agent_core(agent_name: str = AGENT_NAME):
    """Remove Bedrock Agent Core deployment
    
    Uses boto3 bedrock-agentcore-control client to list and delete agent runtimes.
    First lists all agent runtimes to find the matching one by name.
    """
    try:
        # Initialize the Bedrock Agent Core Control client
        bedrock_agentcore_client = boto3.client('bedrock-agentcore-control', region_name=REGION_NAME)
        
        # First, try to list agent runtimes to find the one we need to delete
        try:
            response = bedrock_agentcore_client.list_agent_runtimes()
            agent_runtimes = response.get("agentRuntimes", [])
            
            if not agent_runtimes:
                print("ℹ️  No agent runtimes found for cleanup")
                return
            
            # Look for our agent by name or runtime ID (since name might be N/A)
            target_runtime_id = None
            for runtime in agent_runtimes:
                runtime_name = runtime.get("name", "")
                runtime_id = runtime.get("agentRuntimeId", "")
                
                # Check if agent_name matches either the name or is at the start of the runtime ID
                if (agent_name in runtime_name.lower()) or (runtime_id.lower().startswith(agent_name.lower())):
                    target_runtime_id = runtime_id
                    break
            
            if target_runtime_id:
                # Delete the agent runtime
                try:
                    delete_response = bedrock_agentcore_client.delete_agent_runtime(
                        agentRuntimeId=target_runtime_id
                    )
                    status = delete_response.get('status', 'UNKNOWN')
                    print(f"✅ Deleted Bedrock Agent Core runtime: {target_runtime_id} (Status: {status})")
                    
                except bedrock_agentcore_client.exceptions.ResourceNotFoundException:
                    print(f"ℹ️  Agent runtime {target_runtime_id} not found")
                except Exception as e:
                    print(f"⚠️  Could not delete agent runtime {target_runtime_id}: {e}")
            else:
                print(f"ℹ️  No agent runtime found matching name: {agent_name}")
                
        except bedrock_agentcore_client.exceptions.ResourceNotFoundException:
            print("ℹ️  No agent runtimes found for cleanup")
        except Exception as e:
            print(f"⚠️  Error listing agent runtimes: {e}")
            
    except Exception as e:
        print(f"❌ Error cleaning up Bedrock Agent Core: {e}")


def cleanup_ecr_repository(repository_name: str = AGENT_NAME):
    """Remove ECR repository created by agentcore CLI"""
    try:
        ecr_client = boto3.client("ecr", region_name=REGION_NAME)
        
        # First, list all repositories to see what exists
        try:
            all_repos = ecr_client.describe_repositories()
            repositories = all_repos.get('repositories', [])
            
            if not repositories:
                print("ℹ️  No ECR repositories found for cleanup")
                return
            
            # Look for repository that matches or contains our agent name
            target_repo_name = None
            for repo in repositories:
                repo_name = repo.get('repositoryName', '')
                if repository_name in repo_name.lower() or repo_name.lower().startswith(repository_name.lower()):
                    target_repo_name = repo_name
                    break
            
            if not target_repo_name:
                print(f"ℹ️  No ECR repository found matching: {repository_name}")
                print(f"🔍 Available repositories: {[repo.get('repositoryName') for repo in repositories]}")
                return
            
            # Delete all images in the repository first
            response = ecr_client.list_images(repositoryName=target_repo_name)
            image_ids = response.get('imageIds', [])
            
            if image_ids:
                ecr_client.batch_delete_image(
                    repositoryName=target_repo_name,
                    imageIds=image_ids
                )
                print(f"✅ Deleted {len(image_ids)} images from ECR repository: {target_repo_name}")
            
            # Delete the repository
            ecr_client.delete_repository(
                repositoryName=target_repo_name,
                force=True
            )
            print(f"✅ Deleted ECR repository: {target_repo_name}")
            
        except ecr_client.exceptions.RepositoryNotFoundException:
            print(f"ℹ️  ECR repository {repository_name} not found")
        except Exception as e:
            print(f"⚠️  Could not delete ECR repository: {e}")
            
    except Exception as e:
        print(f"❌ Error cleaning up ECR repository: {e}")


def cleanup_codebuild_project(agent_name: str = AGENT_NAME):
    """Remove CodeBuild project created by agentcore CLI"""
    try:
        codebuild_client = boto3.client("codebuild", region_name=REGION_NAME)
        
        # The project name follows the pattern: bedrock-agentcore-{agent_name}-builder
        project_name = f"bedrock-agentcore-{agent_name}-builder"
        
        # Check if the project exists first
        try:
            # List projects to see if ours exists
            response = codebuild_client.list_projects()
            project_names = response.get('projects', [])
            
            if project_name not in project_names:
                print(f"ℹ️  CodeBuild project {project_name} not found")
                return
                
            # Delete the CodeBuild project (we know it exists)
            codebuild_client.delete_project(name=project_name)
            print(f"✅ Deleted CodeBuild project: {project_name}")
            
        except Exception as e:
            print(f"⚠️  Could not delete CodeBuild project {project_name}: {e}")
            
    except Exception as e:
        print(f"❌ Error cleaning up CodeBuild project: {e}")


def cleanup_agent_core_execution_role():
    """Remove AmazonBedrockAgentCoreSDKRuntime IAM role and associated policies"""
    try:
        iam_client = boto3.client('iam')
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        role_name = AGENT_CORE_ROLE_NAME
        
        # List attached policies
        try:
            response = iam_client.list_attached_role_policies(RoleName=role_name)
            policies = response.get('AttachedPolicies', [])
            
            # Detach all policies
            for policy in policies:
                iam_client.detach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy['PolicyArn']
                )
                print(f"✅ Detached policy {policy['PolicyName']} from role {role_name}")
            
            # Delete the role
            iam_client.delete_role(RoleName=role_name)
            print(f"✅ Deleted IAM role: {role_name}")
            
        except iam_client.exceptions.NoSuchEntityException:
            print(f"ℹ️  IAM role {role_name} not found")
        
        # Delete custom execution policy
        custom_policy_name = AGENT_CORE_POLICY_NAME
        custom_policy_arn = f"arn:aws:iam::{account_id}:policy/{custom_policy_name}"
        
        try:
            iam_client.delete_policy(PolicyArn=custom_policy_arn)
            print(f"✅ Deleted custom policy: {custom_policy_name}")
        except iam_client.exceptions.NoSuchEntityException:
            print(f"ℹ️  Custom policy {custom_policy_name} not found")
        except Exception as e:
            print(f"⚠️  Could not delete custom policy {custom_policy_name}: {e}")
            
    except Exception as e:
        print(f"❌ Error cleaning up Agent Core execution role: {e}")


def cleanup_knowledge_base(kb_name: str = KB_NAME, region_name: str = REGION_NAME):
    """Remove Bedrock Knowledge Base"""
    try:
        bedrock_agent_client = boto3.client("bedrock-agent", region_name=region_name)
        
        # List knowledge bases to find the one we created
        response = bedrock_agent_client.list_knowledge_bases()
        kb_id = None
        
        for kb in response.get("knowledgeBaseSummaries", []):
            if kb["name"] == kb_name:
                kb_id = kb["knowledgeBaseId"]
                break
        
        if kb_id:
            bedrock_agent_client.delete_knowledge_base(knowledgeBaseId=kb_id)
            print(f"✅ Deleted knowledge base: {kb_name} (ID: {kb_id})")
        else:
            print(f"ℹ️  Knowledge base {kb_name} not found")
            
    except Exception as e:
        print(f"❌ Error deleting knowledge base: {e}")


def cleanup_iam_role(role_name: str = KB_ROLE_NAME):
    """Remove IAM role and associated policies"""
    try:
        iam_client = boto3.client('iam')
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        
        # List and detach managed policies
        try:
            response = iam_client.list_attached_role_policies(RoleName=role_name)
            policies = response.get('AttachedPolicies', [])
            
            # Detach all managed policies
            for policy in policies:
                iam_client.detach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy['PolicyArn']
                )
                print(f"✅ Detached managed policy {policy['PolicyName']} from role {role_name}")
            
            # List and delete inline policies
            inline_response = iam_client.list_role_policies(RoleName=role_name)
            inline_policies = inline_response.get('PolicyNames', [])
            
            # Delete all inline policies
            for policy_name in inline_policies:
                iam_client.delete_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
                print(f"✅ Deleted inline policy {policy_name} from role {role_name}")
            
            # Delete the role
            iam_client.delete_role(RoleName=role_name)
            print(f"✅ Deleted IAM role: {role_name}")
            
        except iam_client.exceptions.NoSuchEntityException:
            print(f"ℹ️  IAM role {role_name} not found")
        
        # Delete custom S3 vectors policy
        custom_policy_name = f"{role_name}-s3vectors-policy"
        custom_policy_arn = f"arn:aws:iam::{account_id}:policy/{custom_policy_name}"
        
        try:
            iam_client.delete_policy(PolicyArn=custom_policy_arn)
            print(f"✅ Deleted custom policy: {custom_policy_name}")
        except iam_client.exceptions.NoSuchEntityException:
            print(f"ℹ️  Custom policy {custom_policy_name} not found")
        except Exception as e:
            print(f"⚠️  Could not delete custom policy {custom_policy_name}: {e}")
            
    except Exception as e:
        print(f"❌ Error cleaning up IAM role: {e}")


def cleanup_s3_vectors(vector_bucket_name: str = VECTOR_BUCKET_NAME, 
                      vector_index_name: str = VECTOR_INDEX_NAME, 
                      region_name: str = REGION_NAME):
    """Remove S3 Vectors index and bucket"""
    try:
        s3_vectors_client = boto3.client("s3vectors", region_name=region_name)
        
        # Check if vector bucket exists first
        try:
            # List vector buckets to see if ours exists
            response = s3_vectors_client.list_vector_buckets()
            bucket_names = [bucket.get('vectorBucketName', '') for bucket in response.get('vectorBuckets', [])]
            
            if vector_bucket_name not in bucket_names:
                print(f"ℹ️  Vector bucket {vector_bucket_name} not found")
                print(f"ℹ️  Vector index {vector_index_name} not found (bucket doesn't exist)")
                return
                
        except Exception as e:
            print(f"⚠️  Could not list vector buckets: {e}")
            return
        
        # Check if vector index exists
        try:
            response = s3_vectors_client.list_indexes(vectorBucketName=vector_bucket_name)
            index_names = [index.get('indexName', '') for index in response.get('indexes', [])]
            
            if vector_index_name in index_names:
                # Delete vector index
                s3_vectors_client.delete_index(
                    vectorBucketName=vector_bucket_name,
                    indexName=vector_index_name
                )
                print(f"✅ Deleted vector index: {vector_index_name}")
            else:
                print(f"ℹ️  Vector index {vector_index_name} not found")
                
        except Exception as e:
            print(f"⚠️  Could not check/delete vector index: {e}")
        
        # Wait a bit for index deletion to propagate
        time.sleep(2)
        
        # Delete vector bucket (only if it exists)
        try:
            s3_vectors_client.delete_vector_bucket(vectorBucketName=vector_bucket_name)
            print(f"✅ Deleted vector bucket: {vector_bucket_name}")
        except Exception as e:
            print(f"⚠️  Could not delete vector bucket: {e}")
                
    except Exception as e:
        print(f"❌ Error cleaning up S3 Vectors: {e}")


def cleanup_config_backup_bucket(bucket_name: str = CONFIG_BACKUP_BUCKET_NAME):
    """Remove S3 bucket used for configuration backup"""
    try:
        s3_client = boto3.client("s3", region_name=REGION_NAME)
        
        # Check if bucket exists first
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['404', 'NoSuchBucket']:
                print(f"ℹ️  S3 config backup bucket {bucket_name} not found")
                return
            else:
                print(f"⚠️  Could not check S3 bucket {bucket_name}: {e}")
                return
        
        # Delete all objects in the bucket first
        try:
            # List all objects
            response = s3_client.list_objects_v2(Bucket=bucket_name)
            objects = response.get('Contents', [])
            
            if objects:
                # Delete all objects
                delete_objects = [{'Key': obj['Key']} for obj in objects]
                s3_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': delete_objects}
                )
                print(f"✅ Deleted {len(objects)} objects from S3 bucket: {bucket_name}")
            
            # Delete the bucket
            s3_client.delete_bucket(Bucket=bucket_name)
            print(f"✅ Deleted S3 config backup bucket: {bucket_name}")
            
        except Exception as e:
            print(f"⚠️  Could not delete S3 bucket {bucket_name}: {e}")
            
    except Exception as e:
        print(f"❌ Error cleaning up S3 config backup bucket: {e}")


def cleanup_guardrail(region_name: str = REGION_NAME):
    """Remove Bedrock guardrail"""
    try:
        bedrock_client = boto3.client("bedrock", region_name=region_name)
        
        # List guardrails to find the one we created
        response = bedrock_client.list_guardrails()
        guardrail_id = None
        
        for guardrail in response.get("guardrails", []):
            if guardrail["name"] == GUARDRAIL_NAME:
                guardrail_id = guardrail["id"]
                break
        
        if guardrail_id:
            bedrock_client.delete_guardrail(guardrailIdentifier=guardrail_id)
            print(f"✅ Deleted guardrail: {GUARDRAIL_NAME} (ID: {guardrail_id})")
        else:
            print(f"ℹ️  Guardrail {GUARDRAIL_NAME} not found")
            
    except Exception as e:
        print(f"❌ Error deleting guardrail: {e}")


def cleanup_user_policies(username: str = USERNAME, policies: list = USER_POLICIES):
    """Remove IAM policies from user (optional)"""
    try:
        iam_client = boto3.client('iam')
        
        for policy_arn in policies:
            policy_name = policy_arn.split('/')[-1]
            try:
                iam_client.detach_user_policy(
                    UserName=username,
                    PolicyArn=policy_arn
                )
                print(f"✅ Detached policy {policy_name} from user {username}")
            except iam_client.exceptions.NoSuchEntityException:
                print(f"ℹ️  Policy {policy_name} was not attached to user {username}")
            except Exception as e:
                print(f"⚠️  Could not detach policy {policy_name}: {e}")
                
    except Exception as e:
        print(f"❌ Error cleaning up user policies: {e}")


def main():
    print("=" * 70)
    print("BEDROCK KNOWLEDGE BASE & AGENT CORE CLEANUP")
    print("=" * 70)
    print()
    
    # Get user confirmation
    print("This will delete the following resources:")
    print(f"• Bedrock Agent Core deployment ({AGENT_NAME})")
    print(f"• ECR Repository (bedrock-agentcore-{AGENT_NAME})")
    print(f"• CodeBuild Project (bedrock-agentcore-{AGENT_NAME}-builder)")
    print(f"• S3 Config Backup Bucket ({CONFIG_BACKUP_BUCKET_NAME})")
    print(f"• Bedrock Knowledge Base ({KB_NAME})")
    print(f"• IAM Roles ({KB_ROLE_NAME}, {AGENT_CORE_ROLE_NAME})")
    print("• Custom IAM policies")
    print(f"• S3 Vectors bucket and index ({VECTOR_BUCKET_NAME})")
    print(f"• Bedrock Guardrail ({GUARDRAIL_NAME})")
    print()
    
    response = input("Are you sure you want to proceed? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Cleanup cancelled")
        return
    
    print("\n🧹 Starting cleanup...\n")
    
    # Clean up in reverse order of creation (to handle dependencies)
    print("1. Cleaning up Bedrock Agent Core...")
    cleanup_bedrock_agent_core()
    print()
    
    print("2. Cleaning up ECR Repository...")
    cleanup_ecr_repository()
    print()
    
    print("3. Cleaning up CodeBuild Project...")
    cleanup_codebuild_project()
    print()
    
    print("4. Cleaning up S3 Config Backup Bucket...")
    cleanup_config_backup_bucket()
    print()
    
    print("5. Cleaning up Knowledge Base...")
    cleanup_knowledge_base()
    print()
    
    print("6. Cleaning up Knowledge Base IAM Role...")
    cleanup_iam_role()
    print()
    
    print("7. Cleaning up Agent Core Execution Role...")
    cleanup_agent_core_execution_role()
    print()
    
    print("8. Cleaning up S3 Vectors...")
    cleanup_s3_vectors()
    print()
    
    print("9. Cleaning up Guardrail...")
    cleanup_guardrail()
    print()
    
    # Optional: Remove user policies
    remove_user_policies = input(f"Remove all Bedrock and Agent Core policies from user '{USERNAME}'? (y/N): ").strip().lower()
    if remove_user_policies in ['y', 'yes']:
        print("10. Cleaning up User Policies...")
        cleanup_user_policies()
        print()
    
    print("=" * 70)
    print("🎉 CLEANUP COMPLETE!")
    print("=" * 70)
    print()
    print("Note: Bedrock models remain enabled as they may be used by other resources.")
    print("To disable models, use the AWS console or run disable commands manually.")


if __name__ == "__main__":
    main()
