import os
import boto3
import time
import uuid
from botocore.exceptions import ClientError


def create_bedrock_knowledge_base(vector_index_arn, embedding_dimensions=1024):
    """
    Course 2, Unit 3: Bedrock Knowledge Base Creation

    Creates and configures a Bedrock Knowledge Base that:
    - Uses S3 Vectors as the storage backend
    - Configures embedding model and dimensions
    - Waits for the knowledge base to become active
    """

    region_name = os.getenv("AWS_REGION", "us-east-1")

    # Initialize Bedrock Agent client
    bedrock_agent_client = boto3.client("bedrock-agent", region_name=region_name)

    # Configuration
    kb_name = f"bedrock-knowledge-base-{uuid.uuid4().hex[:8]}"
    kb_role_arn = f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/kb-service-role"
    embedding_model_id = "amazon.titan-embed-text-v2:0"

    try:
        print("Creating Bedrock Knowledge Base...")
        kb_response = bedrock_agent_client.create_knowledge_base(
            name=kb_name,
            description=(
                "Knowledge base using S3 Vectors for cost-effective storage "
                "with manual vector management"
            ),
            roleArn=kb_role_arn,
            knowledgeBaseConfiguration={
                "type": "VECTOR",
                "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": (
                        f"arn:aws:bedrock:{region_name}::foundation-model/{embedding_model_id}"
                    ),
                    "embeddingModelConfiguration": {
                        "bedrockEmbeddingModelConfiguration": {
                            "dimensions": embedding_dimensions
                        }
                    },
                },
            },
            storageConfiguration={
                "type": "S3_VECTORS",
                "s3VectorsConfiguration": {
                    "indexArn": vector_index_arn,
                },
            },
            clientToken=str(uuid.uuid4()),
        )

        knowledge_base_id = kb_response["knowledgeBase"]["knowledgeBaseId"]
        print(f"✓ Created Knowledge Base: {kb_name}")
        print(f"✓ Knowledge Base ID: {knowledge_base_id}")

        # Wait for knowledge base to be ready
        print("⏳ Waiting for knowledge base to be active...")
        kb_ready = False
        while not kb_ready:
            kb_status = bedrock_agent_client.get_knowledge_base(
                knowledgeBaseId=knowledge_base_id
            )
            status = kb_status["knowledgeBase"]["status"]
            print(f"   Knowledge Base status: {status}")

            if status == "ACTIVE":
                print("✓ Knowledge Base is active!")
                kb_ready = True
            elif status == "FAILED":
                raise RuntimeError("✗ Knowledge Base creation failed!")

            time.sleep(5)

        print("\nBedrock Knowledge Base creation completed successfully!")
        print(f"Knowledge Base ID: {knowledge_base_id}")
        print(f"Knowledge Base Name: {kb_name}")

        return {
            "knowledge_base_id": knowledge_base_id,
            "knowledge_base_name": kb_name,
            "embedding_model": embedding_model_id,
            "status": "ACTIVE"
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]

        if error_code == "AccessDeniedException":
            print(f"✗ Permission Error: {error_message}")
        elif error_code == "ValidationException":
            print(f"✗ Validation Error: {error_message}")
        else:
            print(f"✗ AWS Error ({error_code}): {error_message}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise


if __name__ == "__main__":
    # Example usage - you would need to provide actual vector index ARN from c2_u1
    vector_index_arn = "your-vector-index-arn"
    result = create_bedrock_knowledge_base(vector_index_arn)
    print(f"\nResult: {result}")
