import json
import os
import shutil
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError


def attach_policy(
    attach_to_type: str,
    attach_to_name: str,
    policy_arn: str,
) -> Tuple[bool, Optional[str]]:
    """
    Attach an existing IAM policy (by ARN) to a user or role.

    Returns (success, policy_arn_if_known).
    """
    try:
        iam_client = boto3.client("iam")

        # Validate target principal exists
        try:
            if attach_to_type == "user":
                iam_client.get_user(UserName=attach_to_name)
            elif attach_to_type == "role":
                iam_client.get_role(RoleName=attach_to_name)
            else:
                print(f"❌ Unknown attach_to_type: {attach_to_type}")
                return False, None
        except iam_client.exceptions.NoSuchEntityException:
            print(f"❌ {attach_to_type.capitalize()} {attach_to_name} does not exist")
            return False, None

        # Check if already attached
        already_attached = False
        try:
            if attach_to_type == "user":
                attached = iam_client.list_attached_user_policies(
                    UserName=attach_to_name
                )
            else:
                attached = iam_client.list_attached_role_policies(
                    RoleName=attach_to_name
                )
            already_attached = any(
                p.get("PolicyArn") == policy_arn for p in attached["AttachedPolicies"]
            )
        except ClientError as e:
            print(f"⚠️  Could not list attached policies: {e}")

        if already_attached:
            print(
                f"✅ Policy already attached to {attach_to_type} {attach_to_name}"
            )
            return True, policy_arn

        # Attach policy
        try:
            if attach_to_type == "user":
                iam_client.attach_user_policy(
                    UserName=attach_to_name, PolicyArn=policy_arn
                )
            else:
                iam_client.attach_role_policy(
                    RoleName=attach_to_name, PolicyArn=policy_arn
                )
            print(
                f"✅ Attached policy to {attach_to_type} {attach_to_name}"
            )

            return True, policy_arn

        except ClientError as e:
            print(
                f"❌ Failed to attach policy to {attach_to_type} {attach_to_name}: {e}"
            )
            return False, None

    except Exception as e:
        print(f"❌ Failed to ensure/attach policy: {e}")
        return False, None


def create_policy(policy_name: str, policy_document: Dict) -> Optional[str]:
    """
    Create a customer-managed IAM policy if it does not exist.

    Returns the policy ARN (existing or newly created) if successful, otherwise None.
    """
    try:
        iam_client = boto3.client("iam")
        sts_client = boto3.client("sts")
        account_id = sts_client.get_caller_identity()["Account"]
        policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"

        # Try to create policy
        try:
            iam_client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document),
            )
            print(f"✅ Created IAM policy {policy_name}")
        except iam_client.exceptions.EntityAlreadyExistsException:
            print(f"✅ IAM policy {policy_name} already exists")

        return policy_arn
    except Exception as e:
        print(f"❌ Failed to create policy {policy_name}: {e}")
        return None


def attach_custom_policy(
    policy_name: str,
    policy_json_path: str,
    attach_to_type: str,
    attach_to_name: str,
    replacements: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Ensure a custom IAM policy exists from a JSON file and attach it to a user or role.

    Args:
        policy_name: Name for the IAM policy
        policy_json_path: Filesystem path to the policy JSON template
        attach_to_type: "user" or "role"
        attach_to_name: IAM UserName or RoleName to attach the policy to
        replacements: Optional dict of string replacements to apply to the JSON template

    Returns:
        Policy ARN if successful, None if failed
    """
    try:
        with open(policy_json_path, "r", encoding="utf-8") as f:
            policy_content = f.read()
        if replacements:
            for key, value in replacements.items():
                policy_content = policy_content.replace(key, value)
        policy_document = json.loads(policy_content)

        # Create (or resolve) the policy ARN
        policy_arn = create_policy(policy_name=policy_name, policy_document=policy_document)
        if not policy_arn:
            print(f"❌ Failed to create policy {policy_name}")
            return None

        # Attach to the target principal
        success, _ = attach_policy(
            attach_to_type=attach_to_type,
            attach_to_name=attach_to_name,
            policy_arn=policy_arn,
        )
        if success:
            return policy_arn
        return None
    except Exception as e:
        print(
            "❌ Failed to attach custom policy "
            f"{policy_name} for {attach_to_type} {attach_to_name}: {e}"
        )
        return None


def create_guardrail(region_name: str = "us-east-1"):
    """
    Create a guardrail for AWS Bedrock with predefined security policies.

    Args:
        region_name: AWS region name

    Returns:
        dict: Response from create_guardrail API call, or None if failed.
    """
    control_client = boto3.client("bedrock", region_name=region_name)

    # Define the standard blocked message
    blocked_message = "Your input contains content that is not allowed."

    # Generate unique name
    name = "aws-assistant-guardrail"

    # Define description
    description = (
        "AWS assistant guardrail: deny hacking topics on input and apply violence "
        "category moderation on input."
    )

    try:
        response = control_client.create_guardrail(
            name=name,
            description=description,
            contentPolicyConfig={
                "filtersConfig": [
                    {
                        "type": "VIOLENCE",
                        "inputStrength": "HIGH",
                        "outputStrength": "NONE",
                    },
                ]
            },
            topicPolicyConfig={
                "topicsConfig": [
                    {
                        "name": "Security Exploits and Hacking",
                        "definition": (
                            "Content describing or instructing on security exploits, hacking "
                            "techniques, or malicious activities against AWS or any systems."
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
            blockedOutputsMessaging=blocked_message,
        )

        # Check if guardrail creation was successful
        if "guardrailId" in response and "guardrailArn" in response:
            print("✅ Guardrail created successfully!")
            print(f"Guardrail ID: {response['guardrailId']}")
            print(f"Guardrail ARN: {response['guardrailArn']}")
            print(f"Version: {response.get('version', 'N/A')}")
            return response
        else:
            print("❌ Guardrail creation failed - missing expected response fields")
            return None

    except Exception as e:
        # If guardrail with the same name already exists, reuse it
        message = str(e)
        if "ConflictException" in message or "already has this name" in message:
            try:
                summaries = control_client.list_guardrails().get("guardrails", [])
                existing = next(
                    (g for g in summaries if g.get("name") == name),
                    None,
                )
                if existing:
                    print("✅ Guardrail already exists, reusing it")
                    # Get full details if needed
                    guardrail_id = existing.get("guardrailId") or existing.get("id")
                    guardrail_arn = existing.get("guardrailArn") or existing.get("arn")
                    return {
                        "guardrailId": guardrail_id,
                        "guardrailArn": guardrail_arn,
                        "version": existing.get("version", "DRAFT"),
                    }
            except Exception as inner:
                print(f"⚠️  Failed to look up existing guardrail: {inner}")

        print(f"❌ Failed to create guardrail: {message}")
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
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()

                    if content:
                        documents.append(
                            {
                                "key": file_path.stem,
                                "content": content,
                                "metadata": {"filename": file_path.name},
                            }
                        )

                except Exception as e:
                    print(f"⚠️  Error loading {file_path.name}: {e}")

        print(f"✅ Loaded {len(documents)} documents from {folder_path}")
        return documents

    except Exception as e:
        print(f"❌ Failed to load documents from folder: {str(e)}")
        return []


def setup_s3_vectors(
    s3_vectors_client,
    vector_bucket_name: str,
    vector_index_name: str,
    embedding_dimensions: int = 1024,
) -> Optional[str]:
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


def vectorize_and_store_documents(
    documents: List[Dict],
    s3_vectors_client,
    bedrock_runtime_client,
    vector_bucket_name: str,
    vector_index_name: str,
    embedding_model_id: str = "amazon.titan-embed-text-v2:0",
    embedding_dimensions: int = 1024,
) -> bool:
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
                    modelId=embedding_model_id, body=json.dumps(embedding_request)
                )

                response_body = json.loads(response["body"].read())
                embedding = response_body["embedding"]

                # Prepare vector for insertion
                vectors_to_insert.append(
                    {
                        "key": doc["key"],
                        "data": {"float32": [float(x) for x in embedding]},
                        "metadata": {
                            "AMAZON_BEDROCK_TEXT": doc["content"],
                            "x-amz-bedrock-kb-source-uri": doc["metadata"].get(
                                "filename", doc["key"]
                            ),
                            **doc["metadata"],
                        },
                    }
                )

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

        print(
            f"✅ Successfully uploaded {len(vectors_to_insert)} documents to S3 Vectors"
        )
        return True

    except Exception as e:
        print(f"❌ Failed to vectorize and store documents: {str(e)}")
        return False


def create_knowledge_base(
    bedrock_agent_client,
    vector_index_arn: str,
    kb_name: str,
    kb_role_arn: str,
    region_name: str = "us-east-1",
    embedding_model_id: str = "amazon.titan-embed-text-v2:0",
    embedding_dimensions: int = 1024,
) -> Optional[str]:
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

        # Try to create Knowledge Base; if already exists, look it up
        kb_response = None
        try:
            kb_response = bedrock_agent_client.create_knowledge_base(
                name=kb_name,
                description=("Knowledge base using S3 Vectors for document retrieval"),
                roleArn=kb_role_arn,
                knowledgeBaseConfiguration={
                    "type": "VECTOR",
                    "vectorKnowledgeBaseConfiguration": {
                        "embeddingModelArn": (
                            f"arn:aws:bedrock:{region_name}::foundation-model/"
                            f"{embedding_model_id}"
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
        except Exception as e:
            message = str(e)
            if "ConflictException" in message or "already exists" in message:
                summaries = bedrock_agent_client.list_knowledge_bases().get(
                    "knowledgeBaseSummaries", []
                )
                existing = next(
                    (k for k in summaries if k.get("name") == kb_name),
                    None,
                )
                if existing:
                    knowledge_base_id = existing.get("knowledgeBaseId") or existing.get(
                        "id"
                    )
                    print(
                        "✅ Knowledge Base already exists, reusing it: "
                        f"{knowledge_base_id}"
                    )
                    return knowledge_base_id
                raise
            else:
                raise

        knowledge_base_id = kb_response["knowledgeBase"]["knowledgeBaseId"]
        print(f"✅ Created Knowledge Base ID: {knowledge_base_id}")

        return knowledge_base_id

    except Exception as e:
        print(f"❌ Failed to create knowledge base: {str(e)}")
        return None


def wait_for_knowledge_base_ready(
    bedrock_agent_client, knowledge_base_id: str, max_wait_time: int = 60
) -> bool:
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

        iam_client = boto3.client("iam")
        sts_client = boto3.client("sts")

        # Trust policy that allows Bedrock to assume this role
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }

        account_id = sts_client.get_caller_identity()["Account"]
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
                Description="Execution role for Bedrock Knowledge Base operations",
            )
            print(f"✅ Created IAM role: {role_name}")

            # Attach the necessary policies for Knowledge Base
            policies = [
                "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
                "arn:aws:iam::aws:policy/AmazonS3FullAccess",
            ]

            for policy_arn in policies:
                iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
                print(f"✅ Attached policy {policy_arn} to role {role_name}")

            # Ensure custom policy for S3 Vectors permissions
            custom_policy_name = f"{role_name}-s3vectors-policy"
            policy_json_path = os.path.join(
                os.path.dirname(__file__), "policies", "S3VectorsFullAccess.json"
            )
            attach_custom_policy(
                policy_name=custom_policy_name,
                policy_json_path=policy_json_path,
                attach_to_type="role",
                attach_to_name=role_name,
            )

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
                    print(
                        f"⏳ Role not ready yet (attempt {attempt + 1}/{max_retries}), "
                        f"waiting {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                else:
                    print(
                        f"❌ Role verification failed after {max_retries} attempts: {check_error}"
                    )
                    return None

        return role_arn

    except Exception as e:
        print(f"❌ Failed to create Knowledge Base role: {str(e)}")
        return None


def setup_complete_knowledge_base(
    documents_folder: Optional[str] = None,
    vector_bucket_name: str = "bedrock-vector-bucket",
    vector_index_name: str = "bedrock-vector-index",
    kb_name: str = "bedrock-knowledge-base",
    region_name: str = "us-east-1",
) -> Optional[Tuple[str, str]]:
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
            documents_folder = os.path.join(os.getcwd(), "docs/")

        if (
            not os.path.exists(documents_folder)
            or len(os.listdir(documents_folder)) == 0
        ):
            zip_url = (
                "https://codesignal-staging-assets.s3.amazonaws.com/uploads/"
                "1755867202135/techco-kb-sample-md.zip"
            )
            zip_path = os.path.join(os.getcwd(), "techco-data.zip")
            # Download the zip file
            with urllib.request.urlopen(zip_url) as response, open(
                zip_path, "wb"
            ) as out_file:
                shutil.copyfileobj(response, out_file)
            # Extract the zip file
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall()
            # Remove the zip file and README.md
            os.remove(zip_path)
            os.remove("README.md")

        # Create AWS clients
        s3_vectors_client = boto3.client("s3vectors", region_name=region_name)
        bedrock_runtime_client = boto3.client(
            "bedrock-runtime", region_name=region_name
        )
        bedrock_agent_client = boto3.client("bedrock-agent", region_name=region_name)

        # Step 1: Load documents
        documents = load_documents_from_folder(documents_folder)
        if not documents:
            print(
                "❌ No documents found. Please add documents to the folder before running setup."
            )
            return None

        # Step 2: Set up S3 Vectors
        vector_index_arn = setup_s3_vectors(
            s3_vectors_client, vector_bucket_name, vector_index_name
        )
        if not vector_index_arn:
            return None

        # Step 3: Create IAM role for Knowledge Base
        kb_role_arn = create_knowledge_base_role()
        if not kb_role_arn:
            return None

        # Step 4: Vectorize and store documents
        if not vectorize_and_store_documents(
            documents,
            s3_vectors_client,
            bedrock_runtime_client,
            vector_bucket_name,
            vector_index_name,
        ):
            return None

        # Step 5: Create Knowledge Base
        knowledge_base_id = create_knowledge_base(
            bedrock_agent_client, vector_index_arn, kb_name, kb_role_arn, region_name
        )
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

