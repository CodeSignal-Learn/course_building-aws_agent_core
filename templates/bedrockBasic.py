from pprint import pprint
from common import grant_user_policy
from enableModel import enable_model

# Bedrock model ID to enable
MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"
BEDROCK_POLICY_ARN = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"

def main():
    # 1. Give Bedrock full access to learner user
    if not grant_user_policy("learner", BEDROCK_POLICY_ARN):
        print("❌ Failed to grant Bedrock access to learner. Exiting.")
        exit(1)

    # 2. Enable the Bedrock model
    result = enable_model(MODEL_ID)
    pprint(result)

    if result["status"] == "enabled":
        print(f"✅ Bedrock model {MODEL_ID} enabled")
    else:
        print(f"❌ Failed to enable Bedrock model {MODEL_ID}")
        exit(1)

if __name__ == "__main__":
    main()
