from common import grant_user_policy
from enableModel import enable_model

# Bedrock model ID to enable
MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"
BEDROCK_POLICY_ARN = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"

def main():
    # 1. Give Bedrock full access to learner user  
    if not grant_user_policy("learner", BEDROCK_POLICY_ARN):
        print("❌ Failed to grant Bedrock access to learner. Exiting.")
        return

    # 2. Enable the Bedrock model
    enable_model(MODEL_ID)

if __name__ == "__main__":
    main()
