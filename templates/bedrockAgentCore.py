from enableModel import enable_model
from common import grant_user_policy

# Bedrock model ID to enable
MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"

def main():
    # 1. Give Bedrock full access to learner user
    bedrock_policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
    
    if not grant_user_policy("learner", bedrock_policy_arn, create_user=True):
        print("❌ Failed to grant Bedrock access to learner. Exiting.")
        return

    # 2. Give AgentCoreFullAccess to learner user
    agentcore_policy_arn = "arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess"
    
    if not grant_user_policy("learner", agentcore_policy_arn, create_user=False):
        print("❌ Failed to grant AgentCoreFullAccess to learner. Exiting.")
        return

    # 3. Enable the model
    enable_model(MODEL_ID)

if __name__ == "__main__":
    main()