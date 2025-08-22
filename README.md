# Shopping Assistant Course Path

This repository builds a progressively richer Shopping Assistant across four courses.

## Course 1: Bedrock Basics

- `src/shopping_assistant/cli.py`: CLI that takes a query and calls Bedrock with safe defaults.
- Units:
  - `src/u1_setup_first_call.py`
  - `src/u2_models_and_configs.py`
  - `src/u3_prompt_patterns_structured.py`
  - `src/u4_guardrails.py`

## Course 2: Knowledge Bases with S3 Vectors (Preview)

- Data sample: `data/products.jsonl`
- Helpers: `src/shopping_assistant/kb.py`
- Units:
  - `src/c2_u1_create_kb.py` — upload dataset to S3
  - `src/c2_u2_s3_vectors.py` — wire S3 Vectors to your KB
  - `src/c2_u3_query_kb.py` — query KB and render product cards
  - `src/c2_u4_quality_latency.py` — quick quality/latency checks

## Course 3: Strands Agents 101

- Agent wrapper: `src/shopping_assistant/agent_strands.py`
- Units:
  - `src/c3_u1_strands_quickstart.py`
  - `src/c3_u2_tools_structured.py`
  - `src/c3_u3_mcp_prebuilt.py`
  - `src/c3_u4_mcp_custom_server.py`

## Course 4: Deploy on Bedrock AgentCore (Preview)

- Entrypoints: `src/shopping_assistant/agentcore_entrypoints.py`
- Units:
  - `src/c4_u1_agentcore_concepts.py`
  - `src/c4_u2_agentcore_runtime.py`
  - `src/c4_u3_agentcore_mcp.py`
  - `src/c4_u4_agentcore_memory.py`

## Quick run examples

- CLI: `uv run python -m shopping_assistant.cli "Find a budget laptop under $800"`
- Guardrails demo: set `BEDROCK_GUARDRAIL_ID`/`BEDROCK_GUARDRAIL_VERSION` then `uv run python src/shopping_assistant/guardrails_example.py`
- KB upload: set `KB_S3_BUCKET` then `uv run python src/c2_u1_create_kb.py`
- KB query: set `KNOWLEDGE_BASE_ID` then `uv run python src/c2_u3_query_kb.py`
- Strands quickstart: `uv run python src/c3_u1_strands_quickstart.py`
- AgentCore local: `uv run python src/c4_u2_agentcore_runtime.py`

## Setup (uv)

### 1. Install uv
```bash
# macOS (Homebrew)
brew install uv

# or universal installer
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Create and sync the virtual environment
```bash
uv sync
```

### 3. (Optional) Install AgentCore CLI into the project env
```bash
uv sync --group dev
```
You can then run CLI commands as `uv run agentcore ...`.

Alternatively, use an ephemeral CLI without adding it to the env:
```bash
uvx --from bedrock-agentcore-starter-toolkit==0.1.3 agentcore --help
```

### 4. Export AWS credentials
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### 5. Open Docker if you want to work with Agent Core CLI

## Local Testing

### 1. Run your AgentCore server locally

```bash
uv run python src/c4_u2_agentcore_runtime.py
```
### 2. Test the server with a request
```bash
uv run python utils/invoke.py
```

## Working with Agent Core CLI (Locally)

### 1. Set up your agent project for deployment:

```bash
uv run agentcore configure --entrypoint src/shopping_assistant/agentcore_entrypoints.py --name shopping_assistant
```

> `agentcore configure` inspects your entry point script, gathers details you pass (agent name, region, IAM execution-role, required packages), and writes them to a `.bedrock_agentcore.yaml` blueprint. With that blueprint in place, later commands can build and deploy the agent without asking more questions.

### 1.1 (Optional) Add --disable-otel to silence the OpenTelemetry noise
```bash
uv run agentcore configure --disable-otel --entrypoint src/shopping_assistant/agentcore_entrypoints.py --name shopping_assistant
```

### 2. Deploy locally with your env variables and chosen model
```bash
uv run agentcore launch --local \
   --env AWS_REGION=$AWS_REGION \
   --env AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
   --env AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
   --env MODEL="us.anthropic.claude-sonnet-4-20250514-v1:0"
```

> `agentcore launch --local` spins up a Docker container on `http://localhost:8080`, copying the environment variables straight into the runtime so the Bedrock LLM wrapper can authenticate and select the model you specify.

### 3. Invoke agent locally
```bash
uv run agentcore invoke '{"prompt":"What is AWS Bedrock?"}' --local
```

> `agentcore invoke` takes a JSON payload, calls the agent runtime at `/invocations`, and streams back the response. When you pass --local, the request is routed to the container that launch --local started on `http://localhost:8080`

## Working with Agent Core CLI (AWS)

Before you can deploy to the cloud you must have:

| Requirement                                                                                                                                    | Why it’s needed                                                                                                                                                                                                                                                      |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **An AWS account & CLI credentials** with programmatic access                                                                                  | The toolkit calls AWS APIs during `launch`.                                                                                                                                                                                                                          |
| **Two managed policies on the IAM user or profile you use to run the CLI**<br>`AmazonBedrockAgentCoreFullAccess` <br>`AmazonBedrockFullAccess` | Give the toolkit permission to create runtimes and invoke Bedrock models.                                                                                                                                                                     |
| **An *execution-role* for the runtime container**<br>(or let the toolkit create one)                                                           | The container assumes this role at run-time so it can pull the image, write CloudWatch logs, and call `bedrock:InvokeModel`. A minimal policy needs `ecr:Get*`, `logs:*`, `xray:*`, and the specific Bedrock model actions you plan to use. |
| **Docker running locally**                                                                                                   | The CLI builds a container image before it is pushed to Amazon ECR.                                                                                                                                                                           |

### 1. Configure the Agent

```bash
uv run agentcore configure --entrypoint src/shopping_assistant/agentcore_entrypoints.py --name shopping_assistant
```

> **Tip** For some reason I could only make launch to AWS work when I deleted the previous created `.bedrock_agentcore.yaml` and ran configure again. I think it was because of some ID it created in that file.

### 2. Launch the Agent to AWS

```bash
uv run agentcore launch --env MODEL="us.anthropic.claude-sonnet-4-20250514-v1:0"
```

> This builds the container, pushes it to ECR, and creates the AgentCore runtime. It will wait until the runtime is marked `READY`.

### 3. Check Agent Status

```bash
uv run agentcore status
```

> Prints the runtime ARN, status, image digest, and timestamp. Use `--verbose` to get the full JSON response.

### 4. Invoke the Deployed Agent

```bash
uv run agentcore invoke '{"prompt":"What is AWS Bedrock?"}'
```

> Sends a request to the deployed runtime using the `InvokeAgentRuntime` API. Add `--session-id <id>` to persist memory between calls.

### 6. Update and Redeploy After Code Changes

```bash
uv run agentcore launch
```

> Rebuilds the image and replaces the running runtime. No need to reconfigure.

### 7. List resources created in AWS

#### List agent runtimes

```bash
aws bedrock-agentcore list-agent-runtimes
```

> This should list all the agent runtimes we create in Agent Core.

#### List AgentCore runtimes (Boto3)

```bash
uv run python utils/list_runtimes.py
```

> Lists all AgentCore runtimes in the configured `AWS_REGION` using the `bedrock-agentcore-control` API.

#### List ECR repositories

```bash
aws ecr describe-repositories
```

> This will list the repositories created for the Docker image of our app, it will be named something like `bedrock-agentcore-<app_name>`, in our case `bedrock-agentcore-strands_demo`

#### List CodeBuild projects

```bash
aws codebuild list-projects
```

> Lists all AWS CodeBuild projects in your account. When you launch to AWS, the Agent Core CLI creates a CodeBuild project to build and push your Docker image. It’s usually named `bedrock-agentcore-<app_name>-builder` (for example, `bedrock-agentcore-strands_demo-builder`). You’ll use this name when cleaning up resources.

### 8. Cleanup

```bash
uv run python utils/cleanup.py
```

## Dependency management with uv

- Add a new dependency: `uv add <package>`
- Add a dev-only dependency: `uv add --group dev <package>`
- Remove a dependency: `uv remove <package>`
- Update the lockfile: `uv lock`
- Commit `uv.lock` to version control; `uv run` and `uv sync` will keep it up to date.


> This will delete every agentcore runtime, ecr and codebuild project.


## AWS Console Shortcuts

- **Bedrock Agent Core – Agents**: [Open console](https://us-east-1.console.aws.amazon.com/bedrock-agentcore/agents)
- **Amazon ECR – Private repositories**: [Open console](https://us-east-1.console.aws.amazon.com/ecr/private-registry/repositories?region=us-east-1)
- **AWS CodeBuild – Projects**: [Open console](https://us-east-1.console.aws.amazon.com/codesuite/codebuild/projects)