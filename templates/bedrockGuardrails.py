import boto3
from common import create_guardrail

# Create Bedrock control-plane client
# Used for managing resources like guardrails and policies
control = boto3.client("bedrock")

# Create an input guardrail for the AWS technical assistant
response = create_guardrail(control_client=control)

# Check if guardrail was created successfully
if response:
    print(f"Guardrail is ready to use with ID: {response['guardrailId']}")
    # You can now use the guardrail in your applications
    guardrail_id = response['guardrailId']
    guardrail_arn = response['guardrailArn']
else:
    print("Failed to create guardrail. Please check the error messages above.")
    exit(1)
