import os
from common import create_guardrail, grant_user_policy, setup_complete_knowledge_base
from enableModel import enable_model

# Configuration
BEDROCK_MODELS = ["anthropic.claude-sonnet-4-20250514-v1:0", "amazon.titan-embed-text-v2:0", "amazon.nova-pro-v1:0"]
USER_POLICIES = ["arn:aws:iam::aws:policy/AmazonBedrockFullAccess"]
DOCUMENTS_FOLDER = os.path.join(os.path.dirname(__file__), "docs")
VECTOR_BUCKET_NAME = "bedrock-vector-bucket"
VECTOR_INDEX_NAME = "bedrock-vector-index"
KB_NAME = "bedrock-knowledge-base"
REGION_NAME = "us-east-1"

def main():
    # 1. Grant user policies
    for policy in USER_POLICIES:
        if not grant_user_policy("learner", policy):
            print(f"❌ Failed to grant {policy} to learner. Exiting.")
            exit(1)

    # 2. Enable the Bedrock models
    for model in BEDROCK_MODELS:
        result = enable_model(model)
        if result["status"] == "enabled":
            print(f"✅ Bedrock model {model} enabled")
        else:
            print(f"❌ Failed to enable Bedrock model {model}")
            exit(1)

    # 3. Create guardrail
    guardrail = create_guardrail(REGION_NAME)
    if not guardrail:
        print("❌ Failed to create guardrail. Exiting.")
        exit(1)
    else:
        print(f"✅ Guardrail is ready to use with ID: {guardrail['guardrailId']}")

    # 4. Setup complete knowledge base
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
        print("❌ Failed to create knowledge base. Exiting.")
        exit(1)

if __name__ == "__main__":
    main()





