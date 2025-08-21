import os
import json
import time
import boto3
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def create_guardrail(control_client):
    """
    Create a guardrail for AWS Bedrock with predefined security policies.
    
    Args:
        control_client: boto3 Bedrock client.
    
    Returns:
        dict: Response from create_guardrail API call, or None if failed.
    """
    # Define the standard blocked message
    blocked_message = "Your input contains content that is not allowed."
    
    # Generate unique name 
    name = "aws-assistant-guardrail"
    
    # Define description
    description = "AWS assistant guardrail: deny hacking topics on input and apply violence category moderation on input."
    
    try:
        response = control_client.create_guardrail(
            name=name,
            description=description,
            contentPolicyConfig={
                "filtersConfig": [
                    {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "NONE"},
                ]
            },
            topicPolicyConfig={
                "topicsConfig": [
                    {
                        "name": "Security Exploits and Hacking",
                        "definition": (
                            "Content describing or instructing on security exploits, hacking techniques, or malicious activities against AWS or any systems."
                        ),
                        "examples": [
                            "hack",
                            "exploit",
                            "breach",
                            "attack",
                        ],
                        "type": "DENY",
                    }
                ]
            },
            blockedInputMessaging=blocked_message,
            blockedOutputsMessaging=blocked_message
        )
        
        # Check if guardrail creation was successful
        if "guardrailId" in response and "guardrailArn" in response:
            print(f"✅ Guardrail created successfully!")
            print(f"Guardrail ID: {response['guardrailId']}")
            print(f"Guardrail ARN: {response['guardrailArn']}")
            print(f"Version: {response.get('version', 'N/A')}")
            return response
        else:
            print("❌ Guardrail creation failed - missing expected response fields")
            return None
            
    except Exception as e:
        print(f"❌ Failed to create guardrail: {str(e)}")
        return None


def load_documents_from_folder(folder_path: str) -> List[Dict]:
    """
    Load documents from a folder for knowledge base ingestion.
    
    Args:
        folder_path: Path to folder containing documents
    
    Returns:
        List of document dictionaries, or empty list if failed
    """
    documents = []
    try:
        folder = Path(folder_path)
        
        if not folder.exists():
            print(f"❌ Folder not found: {folder_path}")
            return documents
            
        for file_path in folder.iterdir():
            if file_path.is_file():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    
                    if content:
                        documents.append({
                            "key": file_path.stem,
                            "content": content,
                            "metadata": {
                                "filename": file_path.name
                            }
                        })
                            
                except Exception as e:
                    print(f"⚠️  Error loading {file_path.name}: {e}")
        
        print(f"✅ Loaded {len(documents)} documents from {folder_path}")
        return documents
        
    except Exception as e:
        print(f"❌ Failed to load documents from folder: {str(e)}")
        return []


def setup_s3_vectors(s3_vectors_client, vector_bucket_name: str, vector_index_name: str, 
                     embedding_dimensions: int = 1024) -> Optional[str]:
    """
    Create S3 Vectors bucket and index for knowledge base storage.
    
    Args:
        s3_vectors_client: boto3 S3 Vectors client
        vector_bucket_name: Name for the S3 Vectors bucket
        vector_index_name: Name for the vector index
        embedding_dimensions: Dimensions for embeddings (default 1024)
    
    Returns:
        Vector index ARN if successful, None if failed
    """
    try:
        print("Setting up S3 Vectors...")
        
        # Create S3 vector bucket
        try:
            s3_vectors_client.create_vector_bucket(vectorBucketName=vector_bucket_name)
            print(f"✅ Created vector bucket: {vector_bucket_name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"✅ Vector bucket already exists: {vector_bucket_name}")
            else:
                raise e
        
        # Create vector index
        try:
            s3_vectors_client.create_index(
                vectorBucketName=vector_bucket_name,
                indexName=vector_index_name,
                dimension=embedding_dimensions,
                distanceMetric="cosine",
                dataType="float32",
            )
            print(f"✅ Created vector index: {vector_index_name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"✅ Vector index already exists: {vector_index_name}")
            else:
                raise e
        
        # Get the vector index ARN
        indexes_response = s3_vectors_client.list_indexes(
            vectorBucketName=vector_bucket_name
        )
        index_arn = indexes_response["indexes"][0]["indexArn"]
        print(f"✅ Vector Index ARN: {index_arn}")
        
        return index_arn
        
    except Exception as e:
        print(f"❌ Failed to setup S3 Vectors: {str(e)}")
        return None


def vectorize_and_store_documents(documents: List[Dict], s3_vectors_client, bedrock_runtime_client,
                                vector_bucket_name: str, vector_index_name: str, 
                                embedding_model_id: str = "amazon.titan-embed-text-v2:0",
                                embedding_dimensions: int = 1024) -> bool:
    """
    Generate embeddings and store documents in S3 Vectors.
    
    Args:
        documents: List of document dictionaries
        s3_vectors_client: boto3 S3 Vectors client
        bedrock_runtime_client: boto3 Bedrock Runtime client
        vector_bucket_name: Name of the S3 Vectors bucket
        vector_index_name: Name of the vector index
        embedding_model_id: Model ID for embeddings
        embedding_dimensions: Dimensions for embeddings
    
    Returns:
        True if successful, False if failed
    """
    try:
        print("Vectorizing and storing documents...")
        
        if not documents:
            print("❌ No documents to process")
            return False
        
        vectors_to_insert = []
        
        # Generate embeddings for each document
        for doc in documents:
            print(f"  Processing: {doc['key']}")
            
            # Create embedding request
            embedding_request = {
                "inputText": doc["content"],
                "dimensions": embedding_dimensions,
                "normalize": True,
            }
            
            try:
                # Get embedding from Bedrock
                response = bedrock_runtime_client.invoke_model(
                    modelId=embedding_model_id, 
                    body=json.dumps(embedding_request)
                )
                
                response_body = json.loads(response["body"].read())
                embedding = response_body["embedding"]
                
                # Prepare vector for insertion
                vectors_to_insert.append({
                    "key": doc["key"],
                    "data": {
                        "float32": [float(x) for x in embedding]
                    },
                    "metadata": {
                        "AMAZON_BEDROCK_TEXT": doc["content"],
                        "x-amz-bedrock-kb-source-uri": doc["metadata"].get("filename", doc["key"]),
                        **doc["metadata"],
                    },
                })
                
            except Exception as e:
                print(f"⚠️  Failed to process {doc['key']}: {e}")
                continue
        
        if not vectors_to_insert:
            print("❌ No vectors to insert")
            return False
            
        # Insert vectors into S3 Vectors index
        s3_vectors_client.put_vectors(
            vectorBucketName=vector_bucket_name,
            indexName=vector_index_name,
            vectors=vectors_to_insert,
        )
        
        print(f"✅ Successfully uploaded {len(vectors_to_insert)} documents to S3 Vectors")
        return True
        
    except Exception as e:
        print(f"❌ Failed to vectorize and store documents: {str(e)}")
        return False


def create_knowledge_base(bedrock_agent_client, vector_index_arn: str, kb_name: str,
                         kb_role_arn: str, region_name: str = "us-east-1",
                         embedding_model_id: str = "amazon.titan-embed-text-v2:0",
                         embedding_dimensions: int = 1024) -> Optional[str]:
    """
    Create Bedrock Knowledge Base connected to S3 Vectors.
    
    Args:
        bedrock_agent_client: boto3 Bedrock Agent client
        vector_index_arn: ARN of the S3 Vectors index
        kb_name: Name for the knowledge base
        kb_role_arn: ARN of the IAM role for the knowledge base
        region_name: AWS region name
        embedding_model_id: Model ID for embeddings
        embedding_dimensions: Dimensions for embeddings
    
    Returns:
        Knowledge base ID if successful, None if failed
    """
    try:
        print("Creating Bedrock Knowledge Base...")
        
        # Create Knowledge Base
        kb_response = bedrock_agent_client.create_knowledge_base(
            name=kb_name,
            description="Knowledge base using S3 Vectors for document retrieval",
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
        print(f"✅ Created Knowledge Base ID: {knowledge_base_id}")
        
        return knowledge_base_id
        
    except Exception as e:
        print(f"❌ Failed to create knowledge base: {str(e)}")
        return None


def wait_for_knowledge_base_ready(bedrock_agent_client, knowledge_base_id: str, 
                                max_wait_time: int = 60) -> bool:
    """
    Wait for Knowledge Base to be ready.
    
    Args:
        bedrock_agent_client: boto3 Bedrock Agent client
        knowledge_base_id: ID of the knowledge base
        max_wait_time: Maximum wait time in seconds
    
    Returns:
        True if knowledge base is ready, False if failed or timed out
    """
    try:
        print("Waiting for Knowledge Base to be ready...")
        
        for _ in range(max_wait_time // 2):
            kb_status = bedrock_agent_client.get_knowledge_base(
                knowledgeBaseId=knowledge_base_id
            )
            status = kb_status["knowledgeBase"]["status"]
            
            if status == "ACTIVE":
                print(f"✅ Knowledge Base Status: {status}")
                return True
            elif status == "FAILED":
                print(f"❌ Knowledge Base creation failed with status: {status}")
                return False
            
            print(f"  Status: {status}, waiting...")
            time.sleep(2)
        
        print(f"❌ Knowledge Base creation timed out after {max_wait_time} seconds")
        return False
        
    except Exception as e:
        print(f"❌ Failed to check knowledge base status: {str(e)}")
        return False


def create_knowledge_base_role(role_name: str = "kb-service-role") -> Optional[str]:
    """
    Create IAM role for Bedrock Knowledge Base with necessary policies.
    
    Args:
        role_name: Name for the IAM role
    
    Returns:
        Role ARN if successful, None if failed
    """
    try:
        print(f"Creating Knowledge Base IAM role: {role_name}")
        
        iam_client = boto3.client('iam')
        sts_client = boto3.client('sts')
        
        # Trust policy that allows Bedrock to assume this role
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        account_id = sts_client.get_caller_identity()['Account']
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        
        # Check if role already exists
        role_exists = False
        try:
            iam_client.get_role(RoleName=role_name)
            print(f"✅ IAM role {role_name} already exists")
            role_exists = True
        except iam_client.exceptions.NoSuchEntityException:
            pass
        
        if not role_exists:
            # Create the role
            iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Execution role for Bedrock Knowledge Base operations"
            )
            print(f"✅ Created IAM role: {role_name}")
            
            # Attach the necessary policies for Knowledge Base
            policies = [
                "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
                "arn:aws:iam::aws:policy/AmazonS3FullAccess"
            ]
            
            for policy_arn in policies:
                iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
                print(f"✅ Attached policy {policy_arn} to role {role_name}")
            
            # Wait for role to be fully created
            print("⏳ Waiting for role to propagate...")
            time.sleep(15)  # Wait for role to propagate
        
        # Test role existence with retries
        print("⏳ Verifying role is ready...")
        max_retries = 24  # 2 minutes max wait
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                # Check if the role exists and is accessible
                iam_client.get_role(RoleName=role_name)
                print(f"✅ Knowledge Base role {role_name} is ready!")
                return role_arn
                
            except Exception as check_error:
                if attempt < max_retries - 1:
                    print(f"⏳ Role not ready yet (attempt {attempt + 1}/{max_retries}), waiting {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    print(f"❌ Role verification failed after {max_retries} attempts: {check_error}")
                    return None
        
        return role_arn
        
    except Exception as e:
        print(f"❌ Failed to create Knowledge Base role: {str(e)}")
        return None


def setup_complete_knowledge_base(documents_folder: str = None,
                                 vector_bucket_name: str = "bedrock-vector-bucket",
                                 vector_index_name: str = "bedrock-vector-index",
                                 kb_name: str = "bedrock-knowledge-base",
                                 region_name: str = "us-east-1") -> Optional[Tuple[str, str]]:
    """
    Complete setup function that creates everything needed for the Knowledge Base.
    
    Args:
        documents_folder: Path to documents folder (defaults to ./documents)
        vector_bucket_name: Name for S3 Vectors bucket
        vector_index_name: Name for vector index
        kb_name: Name for knowledge base
        region_name: AWS region name
    
    Returns:
        Tuple of (knowledge_base_id, vector_index_arn) if successful, None if failed
    """
    try:
        print("=" * 60)
        print("BEDROCK KNOWLEDGE BASE SETUP")
        print("=" * 60)
        
        # Default documents folder path
        if documents_folder is None:
            documents_folder = os.path.join(os.path.dirname(__file__), "documents")
        
        # Create AWS clients
        s3_vectors_client = boto3.client("s3vectors", region_name=region_name)
        bedrock_runtime_client = boto3.client("bedrock-runtime", region_name=region_name)
        bedrock_agent_client = boto3.client("bedrock-agent", region_name=region_name)
        sts_client = boto3.client("sts", region_name=region_name)
        
        # Get AWS account ID
        account_id = sts_client.get_caller_identity()["Account"]
        
        # Step 1: Load documents
        documents = load_documents_from_folder(documents_folder)
        if not documents:
            print("❌ No documents found. Please add documents to the folder before running setup.")
            return None
        
        # Step 2: Set up S3 Vectors
        vector_index_arn = setup_s3_vectors(s3_vectors_client, vector_bucket_name, vector_index_name)
        if not vector_index_arn:
            return None
        
        # Step 3: Create IAM role for Knowledge Base
        kb_role_arn = create_knowledge_base_role()
        if not kb_role_arn:
            return None
        
        # Step 4: Vectorize and store documents
        if not vectorize_and_store_documents(documents, s3_vectors_client, bedrock_runtime_client,
                                           vector_bucket_name, vector_index_name):
            return None
        
        # Step 5: Create Knowledge Base
        knowledge_base_id = create_knowledge_base(bedrock_agent_client, vector_index_arn, 
                                                kb_name, kb_role_arn, region_name)
        if not knowledge_base_id:
            return None
        
        # Step 6: Wait for Knowledge Base to be ready
        if not wait_for_knowledge_base_ready(bedrock_agent_client, knowledge_base_id):
            return None
        
        print("\n" + "=" * 60)
        print("SETUP COMPLETE!")
        print("=" * 60)
        print(f"\nKnowledge Base ID: {knowledge_base_id}")
        print(f"Vector Index ARN: {vector_index_arn}")
        print("\nYour Knowledge Base is ready to use!")
        
        return knowledge_base_id, vector_index_arn
        
    except Exception as e:
        print(f"❌ Complete knowledge base setup failed: {str(e)}")
        return None
