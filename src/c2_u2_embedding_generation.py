import os
import boto3
import json

from botocore.exceptions import ClientError


def generate_and_store_embeddings(vector_bucket, vector_index, embedding_dimensions=1024):
    """
    Course 2, Unit 2: Embedding Generation and Vector Storage

    Demonstrates how to:
    - Generate embeddings using Amazon Bedrock
    - Convert embeddings to proper format for S3 Vectors
    - Insert vectors with metadata into S3 Vectors index
    """

    region_name = os.getenv("AWS_REGION", "us-east-1")

    # Initialize AWS clients
    s3_vectors_client = boto3.client("s3vectors", region_name=region_name)
    bedrock_runtime_client = boto3.client("bedrock-runtime", region_name=region_name)

    embedding_model_id = "amazon.titan-embed-text-v2:0"

    try:
        # Prepare sample documents for embedding
        print("Preparing sample documents...")
        sample_documents = [
            {
                "key": "doc1",
                "content": (
                    "Amazon Web Services (AWS) is a comprehensive cloud computing platform. "
                    "It offers over 200 services including computing, storage, databases, "
                    "networking, analytics, machine learning, and artificial intelligence."
                ),
                "metadata": {"title": "AWS Overview", "category": "cloud-computing"},
            },
            {
                "key": "doc2",
                "content": (
                    "Amazon Bedrock is a fully managed service that offers a choice of "
                    "high-performing foundation models (FMs) from leading AI companies like "
                    "AI21 Labs, Anthropic, Cohere, Meta, Stability AI, and Amazon via a single API."
                ),
                "metadata": {"title": "Amazon Bedrock", "category": "ai-ml"},
            },
            {
                "key": "doc3",
                "content": (
                    "Amazon Bedrock Knowledge Bases allows you to give FMs and agents "
                    "contextual information from your company's private data sources for "
                    "Retrieval Augmented Generation (RAG) to deliver more relevant, accurate, "
                    "and customized responses."
                ),
                "metadata": {"title": "Knowledge Bases", "category": "rag"},
            },
        ]

        vectors_to_insert = []

        print("Generating embeddings for sample documents...")
        for doc in sample_documents:
            print(f"   Generating embedding for: {doc['key']}")

            # Generate embedding using Bedrock
            embedding_request = {
                "inputText": doc["content"],
                "dimensions": embedding_dimensions,
                "normalize": True,
            }

            response = bedrock_runtime_client.invoke_model(
                modelId=embedding_model_id, body=json.dumps(embedding_request)
            )

            response_body = json.loads(response["body"].read())
            embedding = response_body["embedding"]

            # Convert to float32 as required by S3 Vectors
            embedding_float32 = [float(x) for x in embedding]

            vectors_to_insert.append(
                {
                    "key": doc["key"],
                    "data": {"float32": embedding_float32},
                    "metadata": {"source_text": doc["content"], **doc["metadata"]},
                }
            )
            print(
                f"   ✓ Generated embedding for: {doc['key']} ({len(embedding_float32)} dimensions)"
            )

        # Insert vectors into S3 Vectors index
        print(f"\nInserting vectors into S3 Vectors index: {vector_index}...")
        s3_vectors_client.put_vectors(
            vectorBucketName=vector_bucket,
            indexName=vector_index,
            vectors=vectors_to_insert,
        )
        print(f"✓ Inserted {len(vectors_to_insert)} vectors into the index")

        print("\nEmbedding generation and storage completed successfully!")

        return {
            "vectors_inserted": len(vectors_to_insert),
            "embedding_model": embedding_model_id,
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
    # Example usage - you would need to provide actual values from c2_u1
    vector_bucket = "your-vector-bucket-name"
    vector_index = "your-vector-index-name"
    result = generate_and_store_embeddings(vector_bucket, vector_index)
    print(f"\nResult: {result}")
