# Quick Start

## Setup

### 1. Install agentcore CLI:
```bash
pip install bedrock-agentcore-starter-toolkit==0.1.3
```

### 2. Install other pip requirements
```bash
pip install -r requirements.txt
```

### 3. Export AWS credentials
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### 4. Open Docker if you want to work with Agent Core CLI

## Local Testing

### 1. Run your agent core server locally

```bash
python main.py
```
### 2. Test the server with a request
```bash
python test.py
```

## Working with Agent Core CLI (Locally)

### 1. Set up your agent project for deployment:

```bash
agentcore configure --entrypoint main.py --name crew_demo
```

> `agentcore configure` inspects your entry point script, gathers details you pass (agent name, region, IAM execution-role, required packages), and writes them to a `.bedrock_agentcore.yaml` blueprint. With that blueprint in place, later commands can build and deploy the agent without asking more questions.

### 1.1 (Optional) Add --disable-otel to silence the OpenTelemetry noise 
```bash
agentcore configure --disable-otel --entrypoint main.py --name crew_demo
```

### 2. Deploy locally with your env variables and chosen model
```bash
agentcore launch --local \
   --env AWS_REGION=$AWS_REGION \
   --env AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
   --env AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
   --env MODEL="us.anthropic.claude-sonnet-4-20250514-v1:0"
```

> `agentcore launch --local` spins up a Docker container on `http://localhost:8080`, copying the environment variables straight into the runtime so the Bedrock LLM wrapper can authenticate and select the model you specify.

### 3. Invoke agent locally
```bash
agentcore invoke '{"prompt":"What is AWS Bedrock?"}' --local
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

> **Tip** If you already have a least-privilege execution role, supply its ARN up front with `--execution-role`; otherwise the toolkit will generate one for you automatically. ([AWS Open Source][3], [AWS Documentation][4])

### 1. Configure the Agent

```bash
agentcore configure --entrypoint main.py --name crew_demo
```

> **Tip** For some reason I could only make launch to AWS work when I deleted the previous created `.bedrock_agentcore.yaml` and ran configure again. I think it was because of some ID it created in that file.

### 2. Launch the Agent to AWS

```bash
agentcore launch --env MODEL="us.anthropic.claude-sonnet-4-20250514-v1:0"
```

> This builds the container, pushes it to ECR, and creates the AgentCore runtime. It will wait until the runtime is marked `READY`.

### 3. Check Agent Status

```bash
agentcore status
```

> Prints the runtime ARN, status, image digest, and timestamp. Use `--verbose` to get the full JSON response.

### 4. Invoke the Deployed Agent

```bash
agentcore invoke '{"prompt":"What is AWS Bedrock?"}'
```

> Sends a request to the deployed runtime using the `InvokeAgentRuntime` API. Add `--session-id <id>` to persist memory between calls.

### 6. Update and Redeploy After Code Changes

```bash
agentcore launch
```

> Rebuilds the image and replaces the running runtime. No need to reconfigure.

### 7. List resources created in AWS

#### List agent runtimes (Not supported in CLI yet)

```bash
aws bedrock-agentcore list-agent-runtimes
```

> This should list all the agent runtimes we create in Agent Core, but the bedrock-agentcore commands are not yet supported in the AWS CLI, althought there's documentation for that :/

#### List ECR repositories 

```bash
aws ecr describe-repositories
```

> This will list the repositories created for the Docker image of our app, it will be named something like `bedrock-agentcore-<app_name>`, in our case `bedrock-agentcore-crew_demo`

#### List CodeBuild projects

```bash
aws codebuild list-projects
```

> Lists all AWS CodeBuild projects in your account. When you launch to AWS, the Agent Core CLI creates a CodeBuild project to build and push your Docker image. It’s usually named `bedrock-agentcore-<app_name>-builder` (for example, `bedrock-agentcore-crew_demo-builder`). You’ll use this name when cleaning up resources.

### 8. Cleanup

```bash
python cleanup.py
```

> This will list every agent runtime, delete the runtime, ecr and codebuild project.

