#!/usr/bin/env bash
set -euo pipefail

# Demonstrate AgentCore Short-term Memory operations

: "${AWS_REGION:=us-east-1}"
: "${ACTOR_ID:=User42}"
: "${SESSION_ID:=DemoSession1}"

export AWS_REGION ACTOR_ID SESSION_ID

uv run python src/c4_u4_agentcore_short_term_memory.py

echo "For reference, see docs: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-getting-started.html"




