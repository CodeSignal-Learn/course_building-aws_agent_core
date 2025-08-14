#!/usr/bin/env bash
set -euo pipefail

# Demonstrate AgentCore Long-term Memory operations (summary strategy)

: "${AWS_REGION:=us-east-1}"
: "${ACTOR_ID:=User84}"
: "${SESSION_ID:=OrderSupportSession1}"

export AWS_REGION ACTOR_ID SESSION_ID

uv run python src/c4_u5_agentcore_long_term_memory.py

echo "For reference, see docs: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-getting-started.html"




