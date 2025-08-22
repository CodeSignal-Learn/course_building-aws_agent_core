#!/usr/bin/env python3
"""
Cleanup script for AWS resources created by kb-test.py

This script removes:
- All vector indexes starting with 'bedrock-vector-index-'
- All vector buckets starting with 'bedrock-vector-bucket-'
- All Knowledge Bases starting with 'bedrock-knowledge-base-'

Usage:
    python utils/cleanup_kb_resources.py [--dry-run]

Options:
    --dry-run    Show what would be deleted without actually deleting
"""

import os
import sys
import boto3
import argparse
from botocore.exceptions import ClientError, NoCredentialsError
from typing import List, Dict, Any


def setup_aws_clients(region_name: str) -> Dict[str, Any]:
    """Initialize AWS clients."""
    try:
        return {
            "s3_vectors": boto3.client("s3vectors", region_name=region_name),
            "bedrock_agent": boto3.client("bedrock-agent", region_name=region_name),
        }
    except NoCredentialsError:
        print("❌ AWS credentials not found. Please configure your AWS credentials.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error initializing AWS clients: {str(e)}")
        sys.exit(1)


def list_vector_buckets(s3_vectors_client, prefix: str = "bedrock-vector-bucket") -> List[str]:
    """List all vector buckets with the specified prefix."""
    try:
        response = s3_vectors_client.list_vector_buckets()
        return [
            bucket["vectorBucketName"]
            for bucket in response.get("vectorBuckets", [])
            if bucket["vectorBucketName"].startswith(prefix)
        ]
    except ClientError as e:
        print(f"❌ Error listing vector buckets: {e.response['Error']['Message']}")
        return []


def list_vector_indexes(
    s3_vectors_client, bucket_name: str, prefix: str = "bedrock-vector-index"
) -> List[Dict[str, str]]:
    """List all vector indexes in a bucket with the specified prefix."""
    try:
        response = s3_vectors_client.list_indexes(vectorBucketName=bucket_name)
        return [
            {"name": index["indexName"], "arn": index["indexArn"]}
            for index in response.get("indexes", [])
            if index["indexName"].startswith(prefix)
        ]
    except ClientError as e:
        error_msg = e.response['Error']['Message']
        print(f"❌ Error listing indexes for bucket {bucket_name}: {error_msg}")
        return []


def list_knowledge_bases(
    bedrock_agent_client, prefix: str = "bedrock-knowledge-base-"
) -> List[Dict[str, str]]:
    """List all Knowledge Bases with the specified prefix."""
    try:
        response = bedrock_agent_client.list_knowledge_bases()
        return [
            {"id": kb["knowledgeBaseId"], "name": kb["name"]}
            for kb in response.get("knowledgeBaseSummaries", [])
            if kb["name"].startswith(prefix)
        ]
    except ClientError as e:
        print(f"❌ Error listing Knowledge Bases: {e.response['Error']['Message']}")
        return []


def delete_vector_index(
    s3_vectors_client, bucket_name: str, index_name: str, dry_run: bool = False
) -> bool:
    """Delete a vector index."""
    if dry_run:
        print(
            f"🔍 [DRY RUN] Would delete vector index: {index_name} "
            f"from bucket: {bucket_name}"
        )
        return True

    try:
        s3_vectors_client.delete_index(
            vectorBucketName=bucket_name,
            indexName=index_name
        )
        print(f"✅ Deleted vector index: {index_name} from bucket: {bucket_name}")
        return True
    except ClientError as e:
        print(f"❌ Error deleting vector index {index_name}: {e.response['Error']['Message']}")
        return False


def delete_vector_bucket(s3_vectors_client, bucket_name: str, dry_run: bool = False) -> bool:
    """Delete a vector bucket."""
    if dry_run:
        print(f"🔍 [DRY RUN] Would delete vector bucket: {bucket_name}")
        return True

    try:
        s3_vectors_client.delete_vector_bucket(vectorBucketName=bucket_name)
        print(f"✅ Deleted vector bucket: {bucket_name}")
        return True
    except ClientError as e:
        print(f"❌ Error deleting vector bucket {bucket_name}: {e.response['Error']['Message']}")
        return False


def delete_knowledge_base(
    bedrock_agent_client, kb_id: str, kb_name: str, dry_run: bool = False
) -> bool:
    """Delete a Knowledge Base."""
    if dry_run:
        print(
            f"🔍 [DRY RUN] Would delete Knowledge Base: {kb_name} (ID: {kb_id})"
        )
        return True

    try:
        bedrock_agent_client.delete_knowledge_base(knowledgeBaseId=kb_id)
        print(f"✅ Deleted Knowledge Base: {kb_name} (ID: {kb_id})")
        return True
    except ClientError as e:
        error_msg = e.response['Error']['Message']
        print(f"❌ Error deleting Knowledge Base {kb_name}: {error_msg}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup AWS resources created by kb-test.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION", "us-east-1"),
        help="AWS region (default: us-east-1 or AWS_REGION env var)"
    )

    args = parser.parse_args()

    print(f"🧹 Starting cleanup of AWS resources (Region: {args.region})")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No resources will be actually deleted")
    print()

    # Initialize AWS clients
    clients = setup_aws_clients(args.region)
    s3_vectors_client = clients["s3_vectors"]
    bedrock_agent_client = clients["bedrock_agent"]

    # Track cleanup statistics
    stats = {
        "indexes_deleted": 0,
        "buckets_deleted": 0,
        "knowledge_bases_deleted": 0,
        "errors": 0
    }

    # Step 1: Delete Knowledge Bases first (they may reference vector indexes)
    print("🔍 Step 1: Finding Knowledge Bases to delete...")
    knowledge_bases = list_knowledge_bases(bedrock_agent_client)

    if knowledge_bases:
        print(f"Found {len(knowledge_bases)} Knowledge Base(s) to delete:")
        for kb in knowledge_bases:
            print(f"  - {kb['name']} (ID: {kb['id']})")
        print()

        for kb in knowledge_bases:
            if delete_knowledge_base(bedrock_agent_client, kb["id"], kb["name"], args.dry_run):
                stats["knowledge_bases_deleted"] += 1
            else:
                stats["errors"] += 1
        print()
    else:
        print("No Knowledge Bases found to delete.\n")

    # Step 2: Delete vector indexes
    print("🔍 Step 2: Finding vector indexes to delete...")
    vector_buckets = list_vector_buckets(s3_vectors_client)

    total_indexes = 0
    for bucket_name in vector_buckets:
        indexes = list_vector_indexes(s3_vectors_client, bucket_name)
        total_indexes += len(indexes)

        if indexes:
            print(f"Found {len(indexes)} vector index(es) in bucket {bucket_name}:")
            for index in indexes:
                print(f"  - {index['name']}")

            for index in indexes:
                if delete_vector_index(s3_vectors_client, bucket_name, index["name"], args.dry_run):
                    stats["indexes_deleted"] += 1
                else:
                    stats["errors"] += 1

    if total_indexes == 0:
        print("No vector indexes found to delete.")
    print()

    # Step 3: Delete vector buckets
    print("🔍 Step 3: Finding vector buckets to delete...")
    if vector_buckets:
        print(f"Found {len(vector_buckets)} vector bucket(s) to delete:")
        for bucket in vector_buckets:
            print(f"  - {bucket}")
        print()

        for bucket_name in vector_buckets:
            if delete_vector_bucket(s3_vectors_client, bucket_name, args.dry_run):
                stats["buckets_deleted"] += 1
            else:
                stats["errors"] += 1
        print()
    else:
        print("No vector buckets found to delete.\n")

    # Summary
    print("📊 Cleanup Summary:")
    print(f"  Knowledge Bases deleted: {stats['knowledge_bases_deleted']}")
    print(f"  Vector indexes deleted: {stats['indexes_deleted']}")
    print(f"  Vector buckets deleted: {stats['buckets_deleted']}")
    print(f"  Errors encountered: {stats['errors']}")

    if args.dry_run:
        print("\n🔍 This was a dry run. Use without --dry-run to actually delete resources.")
    elif stats["errors"] > 0:
        error_count = stats['errors']
        print(
            f"\n⚠️  Cleanup completed with {error_count} error(s). "
            "Check the output above for details."
        )
        sys.exit(1)
    else:
        print("\n✅ Cleanup completed successfully!")


if __name__ == "__main__":
    main()
