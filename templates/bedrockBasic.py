from enableModel import enable_model

# Bedrock model ID to enable
MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"

def main():
    # Enable the model
    enable_model(MODEL_ID)

if __name__ == "__main__":
    main()
