# Quick Start

## Setup

1. Install agentcore CLI:
```bash
pip install bedrock-agentcore-starter-toolkit==0.1.3
```

2. Install other pip requirements
```bash
pip install -r requirements.txt
```

3. Export AWS credentials
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

4. Open Docker if you want to work with Agent Core CLI

## Local Testing

1. Run your agent core server locally

```bash
python main.py
```
2. Test the server with a request
```bash
bash test.py
```

## Working with Agent Core CLI (Locally)

1. Set up your agent project for deployment:

```bash
agentcore configure --entrypoint main.py --name crew_demo
```

> `agentcore configure` inspects your entry point script, gathers details you pass (agent name, region, IAM execution-role, required packages), and writes them to a `.bedrock_agentcore.yaml` blueprint. With that blueprint in place, later commands can build and deploy the agent without asking more questions.

1.1 (Optional) Add --disable-otel to silence the OpenTelemetry noise 
```bash
agentcore configure --disable-otel --entrypoint main.py --name crew_demo
```

2. Deploy locally with your env variables and chosen model
```bash
agentcore launch --local \
   --env AWS_REGION=$AWS_REGION \
   --env AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
   --env AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
   --env MODEL="us.anthropic.claude-sonnet-4-20250514-v1:0"
```

> `agentcore launch --local` spins up a Docker container on `http://localhost:8080`, copying the environment variables straight into the runtime so the Bedrock LLM wrapper can authenticate and select the model you specify.

3. Invoke agent locally
```bash
agentcore invoke '{"prompt":"What is AWS Bedrock?"}' --local
```

> `agentcore invoke` takes a JSON payload, calls the agent runtime at `/invocations`, and streams back the response. When you pass --local, the request is routed to the container that launch --local started on `http://localhost:8080`

## Working with Agent Core CLI (AWS)

