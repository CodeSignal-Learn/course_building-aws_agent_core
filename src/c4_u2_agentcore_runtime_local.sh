#!/usr/bin/env bash
set -euo pipefail

# Local deployment of the AgentCore Runtime (Preview)
# Steps: configure → launch → invoke

: "${AWS_REGION:=us-east-1}"
: "${APP_NAME:=shopping_assistant_local}"
: "${ENTRYPOINT:=src/c4_u2_agentcore_runtime_local.py}"

echo "Configuring runtime: $APP_NAME (region: $AWS_REGION)"
uv run agentcore configure \
  --name "$APP_NAME" \
  --entrypoint "$ENTRYPOINT"

echo "Launching runtime locally..."
uv run agentcore launch \
  --env AWS_REGION=$AWS_REGION \
  --env AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  --env AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  --env MODEL="us.anthropic.claude-sonnet-4-20250514-v1:0" \
  --local


echo "Invoking runtime with a sample payload..."
uv run agentcore invoke \
  --payload '{"prompt":"Hello from local runtime"}' \
  --local

echo "Done. To tail logs in another terminal: agentcore logs --name $APP_NAME --region $AWS_REGION --follow"


