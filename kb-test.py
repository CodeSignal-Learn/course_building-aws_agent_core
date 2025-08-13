import os
import boto3
import json
import time
import uuid
from botocore.exceptions import ClientError


def setup_bedrock_knowledge_base():
    """
    Complete setup of Bedrock Knowledge Base with S3 Vectors storage
    """

    region_name = os.getenv("AWS_REGION")

    # Initialize AWS clients
    s3_client = boto3.client("s3")
    s3_vectors_client = boto3.client("s3vectors")
    bedrock_agent_client = boto3.client("bedrock-agent")
    bedrock_runtime_client = boto3.client("bedrock-agent-runtime")

    # Configuration
    bucket_name = f"bedrock-kb-bucket-{uuid.uuid4().hex[:8]}"
    vector_bucket_name = f"bedrock-vector-bucket-{uuid.uuid4().hex[:8]}"
    vector_index_name = f"bedrock-vector-index-{uuid.uuid4().hex[:8]}"
    kb_name = f"bedrock-knowledge-base-{uuid.uuid4().hex[:8]}"
    kb_role_arn = f"arn:aws:iam::605926690821:role/kb-service-role"
    # Replace `YOUR_ACCOUNT_ID` and `YOUR_ROLE` in the `kb_role_arn` variable with your actual AWS account ID and IAM role name.

    try:
        # Step 1: Create S3 bucket for documents
        print("Step 1: Creating S3 bucket for documents...")
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"✓ Created S3 bucket: {bucket_name}")

        # Step 2: Upload sample documents to S3 bucket
        print("\nStep 2: Uploading documents to S3 bucket...")
        sample_documents = [
            {
                "key": "doc1.txt",
                "content": "Amazon Web Services (AWS) is a comprehensive cloud computing platform. It offers over 200 services including computing, storage, databases, networking, analytics, machine learning, and artificial intelligence.",
            },
            {
                "key": "doc2.txt",
                "content": "Amazon Bedrock is a fully managed service that offers a choice of high-performing foundation models (FMs) from leading AI companies like AI21 Labs, Anthropic, Cohere, Meta, Stability AI, and Amazon via a single API.",
            },
            {
                "key": "doc3.txt",
                "content": "Amazon Bedrock Knowledge Bases allows you to give FMs and agents contextual information from your company's private data sources for Retrieval Augmented Generation (RAG) to deliver more relevant, accurate, and customized responses.",
            },
        ]

        for doc in sample_documents:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=doc["key"],
                Body=doc["content"].encode("utf-8"),
                ContentType="text/plain",
            )
            print(f"✓ Uploaded: {doc['key']}")

        # Step 3: Create S3 Vector Bucket for embeddings storage
        print("\nStep 3: Creating S3 Vector Bucket...")
        vector_bucket_response = s3_vectors_client.create_vector_bucket(
            vectorBucketName=vector_bucket_name
        )

        print(f"✓ Created S3 Vector Bucket: {vector_bucket_name}")

        # Step 4: Create Vector Index
        print("\nStep 4: Creating Vector Index...")
        vector_index_response = s3_vectors_client.create_index(
            vectorBucketName=vector_bucket_name,
            indexName=vector_index_name,
            dimension=1024,  # For amazon.titan-embed-text-v2:0
            distanceMetric="cosine",
            dataType="float32"
        )

        print(f"✓ Created Vector Index: {vector_index_name}")

        # Wait for vector index to be active
        index_arn = s3_vectors_client.list_indexes(
            vectorBucketName=vector_bucket_name
        )["indexes"][0]["indexArn"]

        print(f"✓ Vector Index ARN: {index_arn}")

        # Step 5: Create Bedrock Knowledge Base with S3 Vectors
        print("\nStep 5: Creating Bedrock Knowledge Base...")
        kb_response = bedrock_agent_client.create_knowledge_base(
            name=kb_name,
            description="Knowledge base using S3 Vectors for cost-effective storage",
            roleArn=kb_role_arn,
            knowledgeBaseConfiguration={
                "type": "VECTOR",
                "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": f"arn:aws:bedrock:{region_name}::foundation-model/amazon.titan-embed-text-v2:0",
                    "embeddingModelConfiguration": {
                        "bedrockEmbeddingModelConfiguration": {"dimensions": 1024}
                    },
                },
            },
            storageConfiguration={
                "type": "S3_VECTORS",
                "s3VectorsConfiguration": {
                    # "indexName": vector_index_name,
                    "indexArn": index_arn,
                    # "vectorBucketArn": vector_bucket_arn,
                },
            },
            clientToken=str(uuid.uuid4()),
        )

        knowledge_base_id = kb_response["knowledgeBase"]["knowledgeBaseId"]
        print(f"✓ Created Knowledge Base: {kb_name}")
        print(f"✓ Knowledge Base ID: {knowledge_base_id}")

        # Step 6: Connect S3 bucket to Knowledge Base (Create Data Source)
        # Alternative: compute embeddings and store them using s3vectors
        print("\nStep 6: Connecting S3 bucket to Knowledge Base...")
        data_source_response = bedrock_agent_client.create_data_source(
            knowledgeBaseId=knowledge_base_id,
            name=f"s3-data-source-{uuid.uuid4().hex[:8]}",
            description="S3 data source for knowledge base",
            dataSourceConfiguration={
                "type": "S3",
                "s3Configuration": {
                    "bucketArn": f"arn:aws:s3:::{bucket_name}",
                },
            },
            vectorIngestionConfiguration={
                "chunkingConfiguration": {
                    "chunkingStrategy": "FIXED_SIZE",
                    "fixedSizeChunkingConfiguration": {
                        "maxTokens": 300,
                        "overlapPercentage": 20,
                    },
                }
            },
            clientToken=str(uuid.uuid4()),
        )

        data_source_id = data_source_response["dataSource"]["dataSourceId"]
        print(f"✓ Created Data Source: {data_source_id}")

        # Step 7: Start ingestion job
        # Should not be needed once we switch to S3 Vectors
        print("\nStep 7: Starting ingestion job...")
        ingestion_response = bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            clientToken=str(uuid.uuid4()),
        )

        ingestion_job_id = ingestion_response["ingestionJob"]["ingestionJobId"]
        print(f"✓ Started ingestion job: {ingestion_job_id}")

        # Wait for ingestion to complete
        print("⏳ Waiting for ingestion to complete...")
        while True:
            job_status = bedrock_agent_client.get_ingestion_job(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                ingestionJobId=ingestion_job_id,
            )
            status = job_status["ingestionJob"]["status"]
            print(f"   Ingestion status: {status}")

            if status == "COMPLETE":
                print("✓ Ingestion completed successfully!")
                break
            elif status == "FAILED":
                print("✗ Ingestion failed!")
                print(
                    f"Failure reasons: {job_status['ingestionJob'].get('failureReasons', [])}"
                )
                return

            time.sleep(30)

        # Step 8: Query the Knowledge Base
        print("\nStep 8: Querying the Knowledge Base...")
        queries = [
            "What is Amazon Bedrock?",
            "How does AWS help with cloud computing?",
            "What are the benefits of Knowledge Bases?",
        ]

        for i, query in enumerate(queries, 1):
            print(f"\n--- Query {i}: {query} ---")

            try:
                response = bedrock_runtime_client.retrieve_and_generate(
                    input={"text": query},
                    retrieveAndGenerateConfiguration={
                        "type": "KNOWLEDGE_BASE",
                        "knowledgeBaseConfiguration": {
                            "knowledgeBaseId": knowledge_base_id,
                            "modelArn": f"arn:aws:bedrock:{region_name}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
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
                            print(
                                f"- {ref.get('location', {}).get('s3Location', {}).get('uri', 'Unknown source')}"
                            )

            except Exception as e:
                print(f"Error querying knowledge base: {str(e)}")

        print(f"\n🎉 Setup completed successfully!")
        print(f"Knowledge Base ID: {knowledge_base_id}")
        print(f"S3 Document Bucket: {bucket_name}")
        print(f"S3 Vector Bucket: {vector_bucket_name}")
        print(f"Vector Index: {vector_index_name}")

        return {
            "knowledge_base_id": knowledge_base_id,
            "document_bucket": bucket_name,
            "vector_bucket": vector_bucket_name,
            "vector_index": vector_index_name,
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
