### Amazon Bedrock AgentCore: key concepts

Amazon Bedrock AgentCore helps you deploy and operate production-grade AI agents securely and at scale, with any framework and model.

#### Core services
- **Runtime**: Serverless runtime for dynamic agents and tools with extended execution time, fast cold starts, strong session isolation, built-in identity, and multi‑modal payload support.
- **Identity**: Agent identity and access management that integrates with your existing IdPs, minimizes consent fatigue via a secure token vault, and enables just‑enough access with secure permission delegation.
- **Memory**: High-accuracy memory with support for short‑term (multi‑turn conversations) and long‑term memory that can be shared across agents and sessions, with developer control over what is remembered.
- **Code Interpreter**: Secure code execution in isolated sandboxes for complex workflows and data analysis; integrates with popular frameworks.
- **Browser**: Cloud-based browser runtime so agents can interact with websites at scale with enterprise-grade security and observability.
- **Gateway**: Discover, secure, and invoke tools; transform APIs, Lambda functions, and existing services into agent‑compatible tools.
- **Observability**: Unified dashboards and OpenTelemetry-compatible telemetry for tracing, debugging, and monitoring agent performance.

#### Common use cases
- **Equip agents with built-in tools and capabilities**: Add browser automation and code interpretation; integrate internal and external tools; provide memory across interactions.
- **Deploy securely at scale**: Run dynamic agents without managing infrastructure; leverage built-in identity and secure access delegation.
- **Test and monitor agents**: Track token usage, latency, session duration, and error rates to maintain quality in production.

#### Works with your stack
- Use with open-source frameworks like LangGraph, CrewAI, and Strands Agents.
- Bring your own protocol and model; AgentCore is framework- and model-agnostic.

#### Runtime highlights
- Purpose-built for agentic workloads and tool execution.
- Fast cold starts and extended runtime support.
- True session isolation for secure concurrent workloads.

#### Identity highlights
- Integrates with existing identity providers—no user migration needed.
- Secure token vault to reduce consent fatigue.
- Fine-grained permission delegation for tools and resources.

#### Memory highlights
- Short-term memory for conversational context.
- Long-term memory shareable across agents/sessions.
- Developer control of what the agent remembers.

#### Built-in tools
- **Code Interpreter**: Execute code safely in a sandbox.
- **Browser**: Interact with external websites at scale.

#### Gateway
- Standardized tool discovery and invocation.
- Quickly wrap APIs and services as agent-friendly tools.

#### Observability
- End-to-end traces of agent steps and tool calls.
- Metrics for tokens, latency, sessions, and errors.

#### Get started
1. Host an agent or tool with AgentCore Runtime.
2. Add Memory to provide contextual continuity.
3. Integrate built-in tools or connect external tools via Gateway.
4. Monitor and iterate with Observability.

#### Learn more
- What is Amazon Bedrock AgentCore? [AWS Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html)

Note: AgentCore is in preview and features are subject to change.


