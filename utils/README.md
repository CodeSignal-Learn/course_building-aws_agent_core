# Utils

This directory contains utility scripts for managing AWS resources created during the course.

## cleanup_kb_resources.py

Cleanup script for AWS resources created by `kb-test.py`.

### What it cleans up

The script removes the following resources (in order):
1. **Knowledge Bases** starting with `bedrock-knowledge-base-`
2. **Vector Indexes** starting with `bedrock-vector-index-`
3. **Vector Buckets** starting with `bedrock-vector-bucket-`

### Usage

```bash
# Dry run (recommended first) - shows what would be deleted
python utils/cleanup_kb_resources.py --dry-run

# Actually delete resources
python utils/cleanup_kb_resources.py

# Specify a different AWS region
python utils/cleanup_kb_resources.py --region us-west-2
```

### Prerequisites

- AWS credentials configured (via AWS CLI, environment variables, or IAM role)
- Required permissions for:
  - `s3vectors:ListVectorBuckets`
  - `s3vectors:ListIndexes`
  - `s3vectors:DeleteIndex`
  - `s3vectors:DeleteVectorBucket`
  - `bedrock-agent:ListKnowledgeBases`
  - `bedrock-agent:DeleteKnowledgeBase`

### Safety Features

- **Dry run mode**: Test what would be deleted without actually deleting
- **Specific naming patterns**: Only deletes resources with expected prefixes
- **Error handling**: Continues cleanup even if individual resources fail
- **Detailed logging**: Shows progress and any errors encountered

### Example Output

```
🧹 Starting cleanup of AWS resources (Region: us-east-1)
🔍 DRY RUN MODE - No resources will be actually deleted

🔍 Step 1: Finding Knowledge Bases to delete...
Found 2 Knowledge Base(s) to delete:
  - bedrock-knowledge-base-abc123 (ID: KB123)
  - bedrock-knowledge-base-def456 (ID: KB456)

🔍 [DRY RUN] Would delete Knowledge Base: bedrock-knowledge-base-abc123 (ID: KB123)
🔍 [DRY RUN] Would delete Knowledge Base: bedrock-knowledge-base-def456 (ID: KB456)

🔍 Step 2: Finding vector indexes to delete...
Found 2 vector index(es) in bucket bedrock-vector-bucket-abc123:
  - bedrock-vector-index-abc123

🔍 [DRY RUN] Would delete vector index: bedrock-vector-index-abc123 from bucket: bedrock-vector-bucket-abc123

🔍 Step 3: Finding vector buckets to delete...
Found 1 vector bucket(s) to delete:
  - bedrock-vector-bucket-abc123

🔍 [DRY RUN] Would delete vector bucket: bedrock-vector-bucket-abc123

📊 Cleanup Summary:
  Knowledge Bases deleted: 2
  Vector indexes deleted: 1
  Vector buckets deleted: 1
  Errors encountered: 0

🔍 This was a dry run. Use without --dry-run to actually delete resources.
```
