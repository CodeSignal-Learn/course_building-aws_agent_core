#!/usr/bin/env python3
"""
Cleanup script to remove all resources created by bedrockKnowledgeBase.py

This script will remove:
1. Bedrock Knowledge Base
2. IAM role and custom policies
3. S3 Vectors index and bucket
4. Guardrail
5. IAM policies from users (optional)

Note: This does NOT disable Bedrock models as they might be used by other resources.
"""

import boto3
import time
from botocore.exceptions import ClientError


def cleanup_knowledge_base(kb_name: str = "bedrock-knowledge-base", region_name: str = "us-east-1"):
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


def cleanup_iam_role(role_name: str = "kb-service-role"):
    """Remove IAM role and associated policies"""
    try:
        iam_client = boto3.client('iam')
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        
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


def cleanup_s3_vectors(vector_bucket_name: str = "bedrock-vector-bucket", 
                      vector_index_name: str = "bedrock-vector-index", 
                      region_name: str = "us-east-1"):
    """Remove S3 Vectors index and bucket"""
    try:
        s3_vectors_client = boto3.client("s3vectors", region_name=region_name)
        
        # Delete vector index
        try:
            s3_vectors_client.delete_index(
                vectorBucketName=vector_bucket_name,
                indexName=vector_index_name
            )
            print(f"✅ Deleted vector index: {vector_index_name}")
        except Exception as e:
            if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                print(f"ℹ️  Vector index {vector_index_name} not found")
            else:
                print(f"⚠️  Could not delete vector index: {e}")
        
        # Wait a bit for index deletion to propagate
        time.sleep(2)
        
        # Delete vector bucket
        try:
            s3_vectors_client.delete_vector_bucket(vectorBucketName=vector_bucket_name)
            print(f"✅ Deleted vector bucket: {vector_bucket_name}")
        except Exception as e:
            if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                print(f"ℹ️  Vector bucket {vector_bucket_name} not found")
            else:
                print(f"⚠️  Could not delete vector bucket: {e}")
                
    except Exception as e:
        print(f"❌ Error cleaning up S3 Vectors: {e}")


def cleanup_guardrail(region_name: str = "us-east-1"):
    """Remove Bedrock guardrail"""
    try:
        bedrock_client = boto3.client("bedrock", region_name=region_name)
        
        # List guardrails to find the one we created
        response = bedrock_client.list_guardrails()
        guardrail_id = None
        
        for guardrail in response.get("guardrails", []):
            if guardrail["name"] == "aws-assistant-guardrail":
                guardrail_id = guardrail["id"]
                break
        
        if guardrail_id:
            bedrock_client.delete_guardrail(guardrailIdentifier=guardrail_id)
            print(f"✅ Deleted guardrail: aws-assistant-guardrail (ID: {guardrail_id})")
        else:
            print("ℹ️  Guardrail aws-assistant-guardrail not found")
            
    except Exception as e:
        print(f"❌ Error deleting guardrail: {e}")


def cleanup_user_policies(username: str = "learner", 
                         policies: list = ["arn:aws:iam::aws:policy/AmazonBedrockFullAccess"]):
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
    print("=" * 60)
    print("BEDROCK KNOWLEDGE BASE CLEANUP")
    print("=" * 60)
    print()
    
    # Get user confirmation
    print("This will delete the following resources:")
    print("• Bedrock Knowledge Base (bedrock-knowledge-base)")
    print("• IAM Role (kb-service-role) and custom policies")
    print("• S3 Vectors bucket and index (bedrock-vector-bucket)")
    print("• Bedrock Guardrail (aws-assistant-guardrail)")
    print()
    
    response = input("Are you sure you want to proceed? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Cleanup cancelled")
        return
    
    print("\n🧹 Starting cleanup...\n")
    
    # Clean up in reverse order of creation (to handle dependencies)
    print("1. Cleaning up Knowledge Base...")
    cleanup_knowledge_base()
    print()
    
    print("2. Cleaning up IAM Role...")
    cleanup_iam_role()
    print()
    
    print("3. Cleaning up S3 Vectors...")
    cleanup_s3_vectors()
    print()
    
    print("4. Cleaning up Guardrail...")
    cleanup_guardrail()
    print()
    
    # Optional: Remove user policies
    remove_user_policies = input("Remove Bedrock policies from user 'learner'? (y/N): ").strip().lower()
    if remove_user_policies in ['y', 'yes']:
        print("5. Cleaning up User Policies...")
        cleanup_user_policies()
        print()
    
    print("=" * 60)
    print("🎉 CLEANUP COMPLETE!")
    print("=" * 60)
    print()
    print("Note: Bedrock models remain enabled as they may be used by other resources.")
    print("To disable models, use the AWS console or run disable commands manually.")


if __name__ == "__main__":
    main()
