import os
import boto3
import time
import uuid
from botocore.exceptions import ClientError


def setup_s3_vectors_infrastructure():
    """
    Course 2, Unit 1: S3 Vectors Infrastructure Setup

    Sets up the foundational infrastructure for S3 Vectors:
    - Creates S3 Vector Bucket for embeddings storage
    - Creates Vector Index with specified dimensions and distance metric
    - Waits for infrastructure to be ready
    """

    region_name = os.getenv("AWS_REGION", "us-east-1")

    # Initialize S3 Vectors client
    s3_vectors_client = boto3.client("s3vectors", region_name=region_name)

    # Configuration
    vector_bucket_name = f"bedrock-vector-bucket-{uuid.uuid4().hex[:8]}"
    vector_index_name = f"bedrock-vector-index-{uuid.uuid4().hex[:8]}"
    embedding_dimensions = 1024

    try:
        # Step 1: Create S3 Vector Bucket for embeddings storage
        print("Step 1: Creating S3 Vector Bucket...")
        _ = s3_vectors_client.create_vector_bucket(vectorBucketName=vector_bucket_name)
        print(f"✓ Created S3 Vector Bucket: {vector_bucket_name}")

        # Step 2: Create Vector Index
        print("\nStep 2: Creating Vector Index...")
        _ = s3_vectors_client.create_index(
            vectorBucketName=vector_bucket_name,
            indexName=vector_index_name,
            dimension=embedding_dimensions,
            distanceMetric="cosine",
            dataType="float32",
        )
        print(f"✓ Created Vector Index: {vector_index_name}")

        # Wait for vector index to be active and get its ARN
        print("⏳ Waiting for vector index to be ready...")
        index_ready = False
        while not index_ready:
            indexes_response = s3_vectors_client.list_indexes(
                vectorBucketName=vector_bucket_name
            )
            if indexes_response["indexes"]:
                index_arn = indexes_response["indexes"][0]["indexArn"]
                print(f"✓ Vector Index ARN: {index_arn}")
                index_ready = True
            else:
                print("   Index not yet available, waiting...")
                time.sleep(10)

        print("\nS3 Vectors infrastructure setup completed successfully!")
        print(f"Vector Bucket: {vector_bucket_name}")
        print(f"Vector Index: {vector_index_name}")
        print(f"Vector Index ARN: {index_arn}")

        return {
            "vector_bucket": vector_bucket_name,
            "vector_index": vector_index_name,
            "vector_index_arn": index_arn,
            "embedding_dimensions": embedding_dimensions
        }

    except ClientError as e:
        print(
            f"AWS Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
        )
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise


if __name__ == "__main__":
    result = setup_s3_vectors_infrastructure()
    print(f"\nSetup result: {result}")
