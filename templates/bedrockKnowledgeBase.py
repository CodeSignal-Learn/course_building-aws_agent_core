import os
from common import setup_complete_knowledge_base

# Configuration
DOCUMENTS_FOLDER = os.path.join(os.path.dirname(__file__), "documents")
VECTOR_BUCKET_NAME = "bedrock-vector-bucket"
VECTOR_INDEX_NAME = "bedrock-vector-index"
KB_NAME = "bedrock-knowledge-base"
REGION_NAME = "us-east-1"

# Setup complete knowledge base
result = setup_complete_knowledge_base(
    documents_folder=DOCUMENTS_FOLDER,
    vector_bucket_name=VECTOR_BUCKET_NAME,
    vector_index_name=VECTOR_INDEX_NAME,
    kb_name=KB_NAME,
    region_name=REGION_NAME,
)

# Check if knowledge base setup was successful
if result:
    knowledge_base_id, vector_index_arn = result
    print(f"\nKnowledge Base is ready to use!")
    print(f"Knowledge Base ID: {knowledge_base_id}")
    print(f"Vector Index ARN: {vector_index_arn}")

else:
    print("❌ Failed to create knowledge base. Please check the error messages above.")
    exit(1)
