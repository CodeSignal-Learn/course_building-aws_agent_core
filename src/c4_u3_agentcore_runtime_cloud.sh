#!/usr/bin/env bash
set -euo pipefail

# Cloud deployment of the AgentCore Runtime (Preview)
# Steps: configure → launch (cloud) → status → invoke → list → delete (optional)

: "${AWS_REGION:=us-east-1}"
: "${APP_NAME:=shopping-assistant-cloud}"
: "${ENTRYPOINT:=src.c4_u3_agentcore_runtime_cloud:invoke}"

echo "Configuring runtime for cloud: $APP_NAME (region: $AWS_REGION)"
agentcore configure \
  --name "$APP_NAME" \
  --entrypoint "$ENTRYPOINT"

echo "Launching runtime to AWS..."
agentcore launch \
  --name "$APP_NAME" \
  --region "$AWS_REGION"

echo "Checking runtime status..."
agentcore status \
  --name "$APP_NAME" \
  --region "$AWS_REGION"

echo "Invoking runtime with a sample payload..."
agentcore invoke \
  --name "$APP_NAME" \
  --payload '{"prompt":"Hello from cloud runtime"}' \
  --region "$AWS_REGION"

echo "Listing runtimes in region..."
agentcore list --region "$AWS_REGION"

echo "To delete the runtime (and supporting resources) when done:"
echo "  agentcore delete --name $APP_NAME --region $AWS_REGION --yes"


