import os
import boto3
import json
import time
import uuid
from botocore.exceptions import ClientError


def setup_bedrock_knowledge_base():
    """
    Complete setup of Bedrock Knowledge Base with S3 Vectors storage
    using manual embedding computation and vector insertion
    """

    region_name = os.getenv("AWS_REGION", "us-east-1")

    # Initialize AWS clients
    s3_vectors_client = boto3.client("s3vectors", region_name=region_name)
    bedrock_agent_client = boto3.client("bedrock-agent", region_name=region_name)
    bedrock_runtime_client = boto3.client("bedrock-runtime", region_name=region_name)
    bedrock_agent_runtime_client = boto3.client(
        "bedrock-agent-runtime", region_name=region_name
    )

    # Configuration
    vector_bucket_name = f"bedrock-vector-bucket-{uuid.uuid4().hex[:8]}"
    vector_index_name = f"bedrock-vector-index-{uuid.uuid4().hex[:8]}"
    kb_name = f"bedrock-knowledge-base-{uuid.uuid4().hex[:8]}"
    kb_role_arn = f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/kb-service-role"

    embedding_model_id = "amazon.titan-embed-text-v2:0"
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

        # Step 3: Prepare sample documents and generate embeddings
        print("\nStep 3: Generating embeddings for sample documents...")
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

        # Step 4: Insert vectors into S3 Vectors index
        print("\nStep 4: Inserting vectors into S3 Vectors index...")
        s3_vectors_client.put_vectors(
            vectorBucketName=vector_bucket_name,
            indexName=vector_index_name,
            vectors=vectors_to_insert,
        )
        print(f"✓ Inserted {len(vectors_to_insert)} vectors into the index")

        # Step 5: Create Bedrock Knowledge Base with S3 Vectors
        print("\nStep 5: Creating Bedrock Knowledge Base...")
        try:
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
                        "indexArn": index_arn,
                    },
                },
                clientToken=str(uuid.uuid4()),
            )
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

        # Step 6: Test vector search directly in S3 Vectors
        print("\nStep 6: Testing direct vector search...")
        test_query = "What is Amazon Bedrock?"

        # Generate embedding for test query
        query_embedding_request = {
            "inputText": test_query,
            "dimensions": embedding_dimensions,
            "normalize": True,
        }

        query_response = bedrock_runtime_client.invoke_model(
            modelId=embedding_model_id, body=json.dumps(query_embedding_request)
        )

        query_response_body = json.loads(query_response["body"].read())
        query_embedding = [float(x) for x in query_response_body["embedding"]]

        # Search vectors
        search_response = s3_vectors_client.query_vectors(
            vectorBucketName=vector_bucket_name,
            indexName=vector_index_name,
            queryVector={"float32": query_embedding},
            topK=3,
        )

        print(f"Direct S3 Vectors search results for '{test_query}':")
        for i, result in enumerate(search_response.get("matches", []), 1):
            print(f"   {i}. Key: {result['key']}, Score: {result['similarity']:.4f}")
            if "metadata" in result:
                print(
                    f"      Source: {result['metadata'].get('source_text', 'N/A')[:100]}..."
                )

        # Step 7: Query the Knowledge Base using Bedrock
        print("\nStep 7: Querying the Knowledge Base through Bedrock...")
        queries = [
            "What is Amazon Bedrock?",
            "How does AWS help with cloud computing?",
            "What are the benefits of Knowledge Bases?",
        ]

        for i, query in enumerate(queries, 1):
            print(f"\n--- Query {i}: {query} ---")

            try:
                response = bedrock_agent_runtime_client.retrieve_and_generate(
                    input={"text": query},
                    retrieveAndGenerateConfiguration={
                        "type": "KNOWLEDGE_BASE",
                        "knowledgeBaseConfiguration": {
                            "knowledgeBaseId": knowledge_base_id,
                            "modelArn": (
                                f"arn:aws:bedrock:{region_name}::foundation-model/"
                                "amazon.nova-pro-v1:0"
                                # NOTE: Claude sonnet 4 does not work
                                # NOTE: alternative: anthropic.claude-3-5-sonnet-20240620-v1:0
                            ),
                            "retrievalConfiguration": {
                                "vectorSearchConfiguration": {"numberOfResults": 3}
                            },
                            "generationConfiguration": {
                                "inferenceConfig": {
                                    "textInferenceConfig": {
                                        "maxTokens": 500,
                                        "temperature": 0.1,
                                    }
                                }
                            },
                        },
                    },
                )

                answer = response["output"]["text"]
                print(f"Answer: {answer}")

                # Show sources
                if "citations" in response:
                    print("\nSources:")
                    for citation in response["citations"]:
                        for ref in citation.get("retrievedReferences", []):
                            metadata = ref.get("metadata", {})
                            print(
                                f"- Key: {metadata.get('x-amz-bedrock-kb-source-uri', 'Unknown')}"
                            )
                            print(
                                f"  Content: {ref.get('content', {}).get('text', 'N/A')[:100]}..."
                            )

            except Exception as e:
                print(f"Error querying knowledge base: {str(e)}")

        print("\nSetup completed successfully!")
        print(f"Knowledge Base ID: {knowledge_base_id}")
        print(f"S3 Vector Bucket: {vector_bucket_name}")
        print(f"Vector Index: {vector_index_name}")
        print(f"Vector Index ARN: {index_arn}")

        return {
            "knowledge_base_id": knowledge_base_id,
            "vector_bucket": vector_bucket_name,
            "vector_index": vector_index_name,
            "vector_index_arn": index_arn,
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
    result = setup_bedrock_knowledge_base()
    print(f"\nSetup result: {json.dumps(result, indent=2)}")
