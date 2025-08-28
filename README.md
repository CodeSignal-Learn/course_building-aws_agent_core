# Building GenAI Applications with AWS

A comprehensive repository containing templates, scripts, and resources for the **"Building GenAI Applications with AWS"** learning path. This repository provides hands-on materials for setting up AWS Bedrock resources, knowledge bases, and agent deployments for GenAI applications.

## 🎯 Purpose

This repository is designed to provision AWS accounts with everything needed for the GenAI learning path. It includes:

- **Bedrock Setup Templates**: Enable Bedrock models and configure basic policies.
- **Knowledge Base Templates**: Set up RAG (Retrieval Augmented Generation) systems with vector databases
- **Agent Core Templates**: Deploy complete GenAI agents with guardrails and knowledge integration
- **Supporting Scripts**: Common functions for IAM management, resource provisioning, and model enablement
- **Utility Functions**: Helper scripts for cleanup and account management

## 🏗 Repository Structure

### 📋 Templates


| Template | Purpose | Used In | New Features |
|----------|---------|---------|----------|
| `bedrockBasic.py` | Basic Bedrock setup with model enablement | Course 1 | Model access, IAM policies |
| `bedrockKnowledgeBase.py` | RAG system with vector database (builds on Basic) | Courses 2 & 3 | Knowledge base, S3 vectors, embeddings |
| `bedrockAgentCore.py` | Complete agent deployment (builds on Knowledge Base) | Course 4 | Agent runtime, guardrails, knowledge integration |

> Note: Each template builds upon the previous ones.

### 🔧 Template Components

- **`common.py`**: Shared helper functions for templates including:
  - IAM user and policy management
  - Bedrock guardrail creation
  - Knowledge base setup and configuration
  - S3 vector bucket and index management
  - Resource cleanup utilities


### 🛠 Utilities

- **`utils/cleanup_account.py`**: Comprehensive cleanup of all resources created by templates

### 📦 Dependencies

- **`templates/requirements.txt`**: Dependencies needed to run the provision templates


## 🚀 Quick Start

### Prerequisites
- AWS Account with Bedrock access
- AWS CLI configured with appropriate permissions
- Python 3.10+

### Installation
```bash
# Install template dependencies
pip install -r templates/requirements.txt
```

### Usage

#### Course 1: Basics of GenAI Foundation Models with Amazon Bedrock
```bash
cd templates
python bedrockBasic.py
```
- Grants Bedrock full access to learner user
- Enables Claude Sonnet model (anthropic.claude-sonnet-4-20250514-v1:0)
- Sets up basic GenAI capabilities and safe AI interactions

#### Courses 2 & 3: Managing Data for GenAI / Strands Agents
```bash
cd templates  
python bedrockKnowledgeBase.py
```
- Sets up all basic Bedrock capabilities
- Creates S3 vector bucket and index for document storage
- Configures knowledge base with document ingestion and retrieval
- Enables RAG capabilities with embedding models

#### Course 4: Deploying Agents to AWS with Bedrock AgentCore
```bash
cd templates
python bedrockAgentCore.py
```
- Deploys full Agent Core runtime
- Creates execution roles and guardrails
- Integrates knowledge base with agent capabilities
- Sets up comprehensive GenAI agent infrastructure with conversation memory

## 🔄 Resource Management

### Cleanup

```bash
# Comprehensive account cleanup (all template resources)
python utils/cleanup_account.py
```


