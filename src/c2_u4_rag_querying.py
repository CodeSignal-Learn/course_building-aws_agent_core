import os
import boto3
import json
from botocore.exceptions import ClientError


def test_rag_workflows(knowledge_base_id, vector_bucket, vector_index, embedding_dimensions=1024):
    """
    Course 2, Unit 4: RAG Querying and Testing
    Demonstrates two approaches to querying:
    1. Direct vector search using S3 Vectors
    2. Full RAG workflow using Bedrock Knowledge Base
    """
    region_name = os.getenv("AWS_REGION", "us-east-1")
    # Initialize AWS clients
    s3_vectors_client = boto3.client("s3vectors", region_name=region_name)
    bedrock_runtime_client = boto3.client("bedrock-runtime", region_name=region_name)
    bedrock_agent_runtime_client = boto3.client(
        "bedrock-agent-runtime", region_name=region_name
    )
    embedding_model_id = "amazon.titan-embed-text-v2:0"
    try:
        # Test 1: Direct vector search in S3 Vectors
        print("Test 1: Direct vector search using S3 Vectors...")
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
            vectorBucketName=vector_bucket,
            indexName=vector_index,
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

        # Test 2: Full RAG workflow using Bedrock Knowledge Base
        print("\n" + "="*60)
        print("Test 2: Full RAG workflow using Bedrock Knowledge Base...")
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
        print("\nRAG workflow testing completed successfully!")
        return {
            "direct_search_completed": True,
            "rag_queries_tested": len(queries),
            "knowledge_base_id": knowledge_base_id
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
    # Example usage - you would need to provide actual values from previous units
    knowledge_base_id = "your-knowledge-base-id"
    vector_bucket = "your-vector-bucket-name"
    vector_index = "your-vector-index-name"
    result = test_rag_workflows(knowledge_base_id, vector_bucket, vector_index)
    print(f"\nResult: {result}")
