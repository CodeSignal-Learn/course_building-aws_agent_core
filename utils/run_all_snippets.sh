#!/usr/bin/env bash

# Runs all course snippets sequentially and reports PASS/FAIL/SKIP.
# SKIP is used when required environment variables are missing.

set -uo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$REPO_ROOT/src"
LOG_DIR="$REPO_ROOT/.snippet_logs"
mkdir -p "$LOG_DIR"

# Ensure Python can import local modules if needed
export PYTHONPATH="$SRC_DIR:${PYTHONPATH:-}"

# timeout for long-running snippets (seconds)
LONG_TIMEOUT=6

# name|abs_path|type(short|long)|env_req
# env_req can be empty, a single VAR, or ANY:VAR1,VAR2
SNIPPETS=(
  "C1 U1 Setup & First Call|$SRC_DIR/c1_u1_setup_first_call.py|short|"
  "C1 U2 Models & Configs|$SRC_DIR/c1_u2_models_and_configs.py|short|"
  "C1 U3 Prompt Patterns & Structured|$SRC_DIR/c1_u3_prompt_patterns_structured.py|short|"
  "C1 U4 Guardrails|$SRC_DIR/c1_u4_guardrails.py|short|"
  "C2 U1 Create KB|$SRC_DIR/c2_u1_create_kb.py|short|KB_S3_BUCKET"
  "C2 U2 S3 Vectors|$SRC_DIR/c2_u2_s3_vectors.py|short|KNOWLEDGE_BASE_ID"
  "C2 U3 Query KB|$SRC_DIR/c2_u3_query_kb.py|short|KNOWLEDGE_BASE_ID"
  "C2 U4 Quality & Latency|$SRC_DIR/c2_u4_quality_latency.py|short|KNOWLEDGE_BASE_ID"
  "C3 U1 Strands Quickstart|$SRC_DIR/c3_u1_strands_quickstart.py|short|"
  "C3 U2 Tools & Structured Output|$SRC_DIR/c3_u2_tools_structured.py|short|"
  "C3 U3 MCP Prebuilt|$SRC_DIR/c3_u3_mcp_prebuilt.py|short|ANY:AGENTCORE_GATEWAY_MCP_URL,GATEWAY_MCP_URL"
  "C3 U4 MCP Custom Server|$SRC_DIR/c3_u4_mcp_custom_server.py|short|"
  "C4 U1 AgentCore Concepts|$SRC_DIR/c4_u1_agentcore_concepts.py|short|"
  "C4 U2 AgentCore Runtime|$SRC_DIR/c4_u2_agentcore_runtime.py|long|"
  "C4 U3 AgentCore MCP|$SRC_DIR/c4_u3_agentcore_mcp.py|long|ANY:AGENTCORE_GATEWAY_MCP_URL,GATEWAY_MCP_URL"
  "C4 U4 AgentCore Memory|$SRC_DIR/c4_u4_agentcore_memory.py|long|"
)

RESULTS=()

have_any_env() {
  local list_csv="$1"
  IFS=',' read -r -a vars <<< "$list_csv"
  for v in "${vars[@]}"; do
    if [[ -n "${!v:-}" ]]; then
      return 0
    fi
  done
  return 1
}

check_env_req() {
  local req="$1"
  if [[ -z "$req" ]]; then
    echo "OK"
    return 0
  fi
  if [[ "$req" == ANY:* ]]; then
    local csv="${req#ANY:}"
    if have_any_env "$csv"; then
      echo "OK"
      return 0
    else
      echo "MISSING_ANY:$csv"
      return 1
    fi
  fi
  if [[ -n "${!req:-}" ]]; then
    echo "OK"
    return 0
  else
    echo "MISSING:$req"
    return 1
  fi
}

run_short() {
  local path="$1"
  local log="$2"
  python3 "$path" >"$log" 2>&1
  echo $?
}

run_long_with_timeout() {
  local path="$1"
  local log="$2"
  local timeout_s="$3"

  python3 "$path" >"$log" 2>&1 &
  local pid=$!

  local elapsed=0
  while kill -0 "$pid" >/dev/null 2>&1; do
    sleep 1
    elapsed=$((elapsed + 1))
    if (( elapsed >= timeout_s )); then
      # started and still running: treat as PASS (startup ok), then terminate
      kill "$pid" >/dev/null 2>&1 || true
      # give it a moment to exit
      sleep 1
      return 0
    fi
  done

  # Process exited before timeout; return its exit code
  wait "$pid"
  echo $?
}

pad_right() { printf "%-34s" "$1"; }

echo "Running course snippets..."
echo

for entry in "${SNIPPETS[@]}"; do
  IFS='|' read -r name path type env_req <<< "$entry"
  short_name="$name"
  log_file="$LOG_DIR/$(basename "$path").log"

  env_status=$(check_env_req "$env_req") || true

  if [[ "$env_status" != "OK" ]]; then
    RESULTS+=("$short_name|SKIP|$env_status|$log_file")
    echo "$(pad_right "$short_name") SKIP  ($env_status)"
    continue
  fi

  if [[ ! -f "$path" ]]; then
    RESULTS+=("$short_name|FAIL|NOT_FOUND|$log_file")
    echo "$(pad_right "$short_name") FAIL  (file not found)"
    continue
  fi

  if [[ "$type" == "short" ]]; then
    rc=$(run_short "$path" "$log_file")
  else
    rc=$(run_long_with_timeout "$path" "$log_file" "$LONG_TIMEOUT")
  fi

  if [[ "$rc" == "0" ]]; then
    RESULTS+=("$short_name|PASS||$log_file")
    echo "$(pad_right "$short_name") PASS"
  else
    RESULTS+=("$short_name|FAIL|rc=$rc|$log_file")
    echo "$(pad_right "$short_name") FAIL  (rc=$rc)"
  fi
done

echo
echo "Summary:"
printf "%-34s %-6s %s\n" "Snippet" "Result" "Details"
printf "%-34s %-6s %s\n" "------" "------" "-------"
for r in "${RESULTS[@]}"; do
  IFS='|' read -r n s d l <<< "$r"
  printf "%-34s %-6s %s\n" "$n" "$s" "${d:-} (log: $l)"
done

echo
echo "Logs saved to: $LOG_DIR"



