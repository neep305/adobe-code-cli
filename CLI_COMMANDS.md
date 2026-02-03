# CLI Commands Reference

**Adobe Experience Cloud CLI v0.2.0**

Complete command reference with practical examples using sample data.

---

## Table of Contents

1. [Global Commands](#global-commands)
   - [adobe init](#adobe-init)
   - [adobe version](#adobe-version)

2. [AEP Commands](#aep-commands)
   - [adobe aep init](#adobe-aep-init)
   - [adobe aep info](#adobe-aep-info)

3. [Authentication Commands](#authentication-commands)
   - [adobe auth test](#adobe-auth-test)
   - [adobe auth status](#adobe-auth-status)

4. [AI Configuration Commands](#ai-configuration-commands)
   - [adobe ai set-key](#adobe-ai-set-key)
   - [adobe ai list-keys](#adobe-ai-list-keys)
   - [adobe ai remove-key](#adobe-ai-remove-key)
   - [adobe ai set-default](#adobe-ai-set-default)

5. [Schema Management Commands](#schema-management-commands)
   - [adobe aep schema create](#adobe-aep-schema-create)
   - [adobe aep schema list](#adobe-aep-schema-list)
   - [adobe aep schema get](#adobe-aep-schema-get)
   - [adobe aep schema list-fieldgroups](#adobe-aep-schema-list-fieldgroups)
   - [adobe aep schema get-fieldgroup](#adobe-aep-schema-get-fieldgroup)
   - [adobe aep schema upload-and-validate](#adobe-aep-schema-upload-and-validate)
   - [adobe aep schema analyze-dataset](#adobe-aep-schema-analyze-dataset)

6. [Dataset Management Commands](#dataset-management-commands)
   - [adobe aep dataset list](#adobe-aep-dataset-list)
   - [adobe aep dataset create](#adobe-aep-dataset-create)
   - [adobe aep dataset get](#adobe-aep-dataset-get)
   - [adobe aep dataset delete](#adobe-aep-dataset-delete)
   - [adobe aep dataset enable-profile](#adobe-aep-dataset-enable-profile)
   - [adobe aep dataset enable-identity](#adobe-aep-dataset-enable-identity)
   - [adobe aep dataset create-batch](#adobe-aep-dataset-create-batch)
   - [adobe aep dataset batch-status](#adobe-aep-dataset-batch-status)
   - [adobe aep dataset list-batches](#adobe-aep-dataset-list-batches)
   - [adobe aep dataset complete-batch](#adobe-aep-dataset-complete-batch)
   - [adobe aep dataset abort-batch](#adobe-aep-dataset-abort-batch)

7. [Data Ingestion Commands](#data-ingestion-commands)
   - [adobe aep ingest upload-file](#adobe-aep-ingest-upload-file)
   - [adobe aep ingest upload-batch](#adobe-aep-ingest-upload-batch)
   - [adobe aep ingest upload-directory](#adobe-aep-ingest-upload-directory)
   - [adobe aep ingest status](#adobe-aep-ingest-status)

8. [Onboarding & Tutorial Commands](#onboarding--tutorial-commands)
   - [adobe onboarding start](#adobe-onboarding-start)
   - [adobe onboarding status](#adobe-onboarding-status)
   - [adobe onboarding next](#adobe-onboarding-next)
   - [adobe onboarding skip](#adobe-onboarding-skip)
   - [adobe onboarding back](#adobe-onboarding-back)
   - [adobe onboarding resume](#adobe-onboarding-resume)
   - [adobe onboarding achievements](#adobe-onboarding-achievements)
   - [adobe onboarding reset](#adobe-onboarding-reset)
   - [adobe onboarding ask](#adobe-onboarding-ask)
   - [adobe onboarding clear-cache](#adobe-onboarding-clear-cache)
   - [adobe onboarding cache-stats](#adobe-onboarding-cache-stats)

9. [Sample Data Files](#sample-data-files)

---

## Global Commands

### adobe init

Initialize Adobe CLI configuration (global init).

**Usage:**
```bash
adobe init
```

**Example:**
```bash
# Initialize configuration
adobe init

# Output:
# ✅ Adobe CLI configuration initialized
# Configuration stored in: ~/.adobe/config.json
```

---

### adobe version

Display CLI version information.

**Usage:**
```bash
adobe version
```

**Example:**
```bash
# Check version
adobe version

# Output:
# Adobe Experience Cloud CLI v0.2.0
```

---

## AEP Commands

### adobe aep init

Initialize Adobe Experience Platform configuration.

**Usage:**
```bash
adobe aep init [OPTIONS]
```

**Options:**
- `--client-id TEXT`: Adobe API Client ID
- `--client-secret TEXT`: Adobe API Client Secret
- `--org-id TEXT`: Adobe Organization ID
- `--technical-account-id TEXT`: Technical Account ID
- `--sandbox TEXT`: Sandbox name (default: prod)

**Examples:**

1. **Interactive initialization:**
```bash
adobe aep init

# Prompts you for:
# - Client ID
# - Client Secret
# - Organization ID
# - Technical Account ID
# - Sandbox name
```

2. **Non-interactive with all credentials:**
```bash
adobe aep init \
  --client-id "abc123xyz456" \
  --client-secret "p8e-xxx-yyy-zzz" \
  --org-id "ABC123@AdobeOrg" \
  --technical-account-id "tech_acct_123@techacct.adobe.com" \
  --sandbox "dev"

# Output:
# ✅ AEP configuration saved to ~/.adobe/credentials.json
```

---

### adobe aep info

Display current AEP configuration information.

**Usage:**
```bash
adobe aep info
```

**Example:**
```bash
adobe aep info

# Output:
# ╭─ Adobe Experience Platform Configuration ─╮
# │                                            │
# │ Organization: ABC123@AdobeOrg              │
# │ Sandbox: dev                               │
# │ Client ID: abc123xyz456                    │
# │ Technical Account: tech_acct_123@...       │
# │                                            │
# ╰────────────────────────────────────────────╯
```

---

## Authentication Commands

### adobe auth test

Test Adobe API authentication.

**Usage:**
```bash
adobe auth test
```

**Example:**
```bash
adobe auth test

# Output (success):
# ✅ Authentication successful
# Token obtained: eyJhbGciOiJSUzI1NiIsIng1d...
# Token expires in: 86400 seconds

# Output (failure):
# ❌ Authentication failed
# Error: invalid_client - Client credentials are invalid
```

---

### adobe auth status

Check Adobe API authentication status.

**Usage:**
```bash
adobe auth status
```

**Example:**
```bash
adobe auth status

# Output:
# ╭─ Authentication Status ─╮
# │                          │
# │ Status: ✅ Authenticated │
# │ Token: Valid             │
# │ Expires: 2026-02-03      │
# │ Sandbox: dev             │
# │                          │
# ╰──────────────────────────╯
```

---

## AI Configuration Commands

### adobe ai set-key

Configure AI provider API keys for AI-powered features.

**Usage:**
```bash
adobe ai set-key [OPTIONS]
```

**Options:**
- `--provider TEXT`: AI provider (anthropic, openai) [required]
- `--key TEXT`: API key
- `--interactive`: Interactive key entry (secure)

**Examples:**

1. **Set Anthropic API key (interactive):**
```bash
adobe ai set-key --provider anthropic --interactive

# Prompt:
# Enter your Anthropic API key: [hidden input]
# ✅ Anthropic API key stored securely
```

2. **Set OpenAI API key (direct):**
```bash
adobe ai set-key --provider openai --key "sk-proj-abc123xyz456..."

# Output:
# ⚠️  Warning: Key passed via command line (visible in shell history)
# ✅ OpenAI API key stored securely
```

---

### adobe ai list-keys

List configured AI provider keys (masked).

**Usage:**
```bash
adobe ai list-keys
```

**Example:**
```bash
adobe ai list-keys

# Output:
# ╭─ Configured AI Providers ─╮
# │                            │
# │ ✅ Anthropic               │
# │    Key: sk-ant-api03-***   │
# │    Default: Yes            │
# │                            │
# │ ✅ OpenAI                  │
# │    Key: sk-proj-***        │
# │    Default: No             │
# │                            │
# ╰────────────────────────────╯
```

---

### adobe ai remove-key

Remove an AI provider API key.

**Usage:**
```bash
adobe ai remove-key --provider TEXT
```

**Example:**
```bash
adobe ai remove-key --provider openai

# Prompt:
# Remove OpenAI API key? [y/N]: y
# ✅ OpenAI API key removed
```

---

### adobe ai set-default

Set default AI provider.

**Usage:**
```bash
adobe ai set-default --provider TEXT
```

**Example:**
```bash
adobe ai set-default --provider anthropic

# Output:
# ✅ Default AI provider set to: anthropic
```

---

## Schema Management Commands

### adobe aep schema create

Create XDM schema from sample data using AI.

**Usage:**
```bash
adobe aep schema create [OPTIONS]
```

**Options:**
- `--from-sample PATH`: Path to sample data file (JSON/CSV)
- `--name TEXT`: Schema name
- `--interactive`: Interactive schema builder
- `--output PATH`: Output file path
- `--upload`: Upload schema to AEP after creation

**Examples:**

1. **Create schema from JSON sample:**
```bash
adobe aep schema create \
  --from-sample examples/sample-data/customers.json \
  --name "CustomerProfile" \
  --output customer_schema.json

# Output:
# 🤖 Analyzing sample data...
# ✅ Schema generated successfully
# Schema saved to: customer_schema.json
```

2. **Create and upload to AEP:**
```bash
adobe aep schema create \
  --from-sample examples/sample-data/orders.json \
  --name "OrderEvents" \
  --upload

# Output:
# 🤖 Analyzing sample data...
# ✅ Schema generated successfully
# 📤 Uploading to Adobe Experience Platform...
# ✅ Schema created: https://ns.adobe.com/your-tenant/schemas/order-events-v1
# Schema ID: https://ns.adobe.com/your-tenant/schemas/abc123xyz456
```

3. **Interactive schema builder:**
```bash
adobe aep schema create --interactive

# Prompts:
# Schema name: CustomerProfile
# Description: Customer profile data for marketing segmentation
# Base class: [1] XDM Individual Profile [2] XDM ExperienceEvent
# Select: 1
# Add field groups? [y/N]: y
# ...
```

---

### adobe aep schema list

List all schemas in AEP.

**Usage:**
```bash
adobe aep schema list [OPTIONS]
```

**Options:**
- `--limit INTEGER`: Number of schemas to return (default: 10)
- `--class TEXT`: Filter by schema class

**Example:**
```bash
adobe aep schema list --limit 5

# Output:
# ╭─ Schemas ───────────────────────────────────────────────╮
# │                                                          │
# │ 1. CustomerProfile                                       │
# │    ID: https://ns.adobe.com/tenant/schemas/customer-v1  │
# │    Class: XDM Individual Profile                         │
# │    Created: 2026-01-15                                   │
# │                                                          │
# │ 2. OrderEvents                                           │
# │    ID: https://ns.adobe.com/tenant/schemas/orders-v1    │
# │    Class: XDM ExperienceEvent                            │
# │    Created: 2026-01-20                                   │
# │                                                          │
# ╰──────────────────────────────────────────────────────────╯
```

---

### adobe aep schema get

Get detailed information about a specific schema.

**Usage:**
```bash
adobe aep schema get --schema-id TEXT [OPTIONS]
```

**Options:**
- `--schema-id TEXT`: Schema ID [required]
- `--output PATH`: Save schema to file

**Examples:**

1. **Display schema details:**
```bash
adobe aep schema get \
  --schema-id "https://ns.adobe.com/tenant/schemas/customer-v1"

# Output:
# ╭─ Schema: CustomerProfile ─╮
# │                            │
# │ Title: CustomerProfile     │
# │ Class: XDM Individual...   │
# │ Version: 1.2               │
# │ Fields: 15                 │
# │                            │
# │ Field Groups:              │
# │  - Profile Core            │
# │  - Personal Details        │
# │  - Loyalty Details         │
# │                            │
# ╰────────────────────────────╯
```

2. **Save schema to file:**
```bash
adobe aep schema get \
  --schema-id "https://ns.adobe.com/tenant/schemas/customer-v1" \
  --output downloaded_schema.json

# Output:
# ✅ Schema saved to: downloaded_schema.json
```

---

### adobe aep schema list-fieldgroups

List available XDM field groups.

**Usage:**
```bash
adobe aep schema list-fieldgroups [OPTIONS]
```

**Options:**
- `--limit INTEGER`: Number of field groups to return (default: 10)

**Example:**
```bash
adobe aep schema list-fieldgroups --limit 5

# Output:
# ╭─ Field Groups ──────────────────────────────────╮
# │                                                  │
# │ 1. Profile Personal Details                      │
# │    ID: https://ns.adobe.com/xdm/context/profile  │
# │                                                  │
# │ 2. Loyalty Details                               │
# │    ID: https://ns.adobe.com/xdm/mixins/loyalty   │
# │                                                  │
# │ 3. Commerce Details                              │
# │    ID: https://ns.adobe.com/xdm/context/commerce │
# │                                                  │
# ╰──────────────────────────────────────────────────╯
```

---

### adobe aep schema get-fieldgroup

Get details of a specific field group.

**Usage:**
```bash
adobe aep schema get-fieldgroup --fieldgroup-id TEXT
```

**Example:**
```bash
adobe aep schema get-fieldgroup \
  --fieldgroup-id "https://ns.adobe.com/xdm/mixins/loyalty"

# Output:
# ╭─ Field Group: Loyalty Details ─╮
# │                                 │
# │ Title: Loyalty Details          │
# │ Fields:                         │
# │  - loyaltyId (string)           │
# │  - loyaltyPoints (integer)      │
# │  - memberSince (date)           │
# │  - tier (enum)                  │
# │                                 │
# ╰─────────────────────────────────╯
```

---

### adobe aep schema upload-and-validate

Upload local schema file to AEP and validate.

**Usage:**
```bash
adobe aep schema upload-and-validate --file PATH [OPTIONS]
```

**Options:**
- `--file PATH`: Path to schema JSON file [required]
- `--validate-only`: Only validate, don't upload

**Examples:**

1. **Validate and upload:**
```bash
adobe aep schema upload-and-validate \
  --file examples/sample-data/sample_schema.json

# Output:
# 🔍 Validating schema...
# ✅ Schema is valid
# 📤 Uploading to AEP...
# ✅ Schema created: https://ns.adobe.com/tenant/schemas/abc123
```

2. **Validate only:**
```bash
adobe aep schema upload-and-validate \
  --file customer_schema.json \
  --validate-only

# Output:
# 🔍 Validating schema...
# ✅ Schema is valid XDM format
# ℹ️  Skipping upload (validate-only mode)
```

---

### adobe aep schema analyze-dataset

Analyze dataset and generate XDM schema recommendations.

**Usage:**
```bash
adobe aep schema analyze-dataset --dataset-path PATH [OPTIONS]
```

**Options:**
- `--dataset-path PATH`: Path to dataset directory or file [required]
- `--output PATH`: Output directory for analysis
- `--format TEXT`: Output format (json, markdown)

**Examples:**

1. **Analyze JSON dataset:**
```bash
adobe aep schema analyze-dataset \
  --dataset-path examples/sample-data/customers.json \
  --format markdown

# Output:
# 🤖 Analyzing dataset structure...
# 📊 Found 5 records
# ✅ Analysis complete
# 
# Recommendations:
#  - Detected fields: 10
#  - Suggested XDM class: XDM Individual Profile
#  - Recommended field groups: Profile Personal Details, Loyalty Details
# 
# Report saved to: .adobe-workspace/output/ai-analysis/analysis.md
```

2. **Analyze CSV dataset:**
```bash
adobe aep schema analyze-dataset \
  --dataset-path examples/sample-data/customers.csv \
  --output ./analysis \
  --format json

# Output:
# 🤖 Analyzing dataset structure...
# 📊 Found 5 records, 10 columns
# ✅ Analysis complete
# Report saved to: ./analysis/analysis.json
```

---

## Dataset Management Commands

### adobe aep dataset list

List all datasets in AEP.

**Usage:**
```bash
adobe aep dataset list [OPTIONS]
```

**Options:**
- `--limit INTEGER`: Number of datasets to return (default: 10)

**Example:**
```bash
adobe aep dataset list --limit 5

# Output:
# ╭─ Datasets ───────────────────────────────────────────╮
# │                                                       │
# │ 1. Customer Profiles Dataset                          │
# │    ID: 5f2a8b1c4d3e2f1a2b3c4d5e                      │
# │    Schema: CustomerProfile                            │
# │    Records: 15,234                                    │
# │    Created: 2026-01-10                                │
# │                                                       │
# │ 2. Order Events Dataset                               │
# │    ID: 6a3b9c2d5e4f3g2b3d4e5f6g                      │
# │    Schema: OrderEvents                                │
# │    Records: 48,921                                    │
# │    Created: 2026-01-15                                │
# │                                                       │
# ╰───────────────────────────────────────────────────────╯
```

---

### adobe aep dataset create

Create a new dataset in AEP.

**Usage:**
```bash
adobe aep dataset create [OPTIONS]
```

**Options:**
- `--name TEXT`: Dataset name [required]
- `--schema-id TEXT`: Schema ID [required]
- `--description TEXT`: Dataset description

**Example:**
```bash
adobe aep dataset create \
  --name "Customer Profiles Jan 2026" \
  --schema-id "https://ns.adobe.com/tenant/schemas/customer-v1" \
  --description "Customer profile data ingested in January 2026"

# Output:
# ✅ Dataset created successfully
# Dataset ID: 7b4c0d3e6f5g4h3c4e5f6g7h
# Name: Customer Profiles Jan 2026
```

---

### adobe aep dataset get

Get detailed information about a specific dataset.

**Usage:**
```bash
adobe aep dataset get --dataset-id TEXT
```

**Example:**
```bash
adobe aep dataset get --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e"

# Output:
# ╭─ Dataset Details ─────────────────────────╮
# │                                            │
# │ Name: Customer Profiles Dataset            │
# │ ID: 5f2a8b1c4d3e2f1a2b3c4d5e              │
# │ Schema: CustomerProfile                    │
# │ Status: enabled                            │
# │ Profile Enabled: Yes                       │
# │ Identity Enabled: Yes                      │
# │ Total Records: 15,234                      │
# │ Created: 2026-01-10T08:30:00Z              │
# │ Modified: 2026-02-01T14:22:00Z             │
# │                                            │
# ╰────────────────────────────────────────────╯
```

---

### adobe aep dataset delete

Delete a dataset from AEP.

**Usage:**
```bash
adobe aep dataset delete --dataset-id TEXT [--force]
```

**Options:**
- `--dataset-id TEXT`: Dataset ID [required]
- `--force`: Skip confirmation

**Example:**
```bash
adobe aep dataset delete --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e"

# Prompt:
# ⚠️  Delete dataset 'Customer Profiles Dataset'? This cannot be undone. [y/N]: y
# ✅ Dataset deleted successfully
```

---

### adobe aep dataset enable-profile

Enable Real-Time Customer Profile for a dataset.

**Usage:**
```bash
adobe aep dataset enable-profile --dataset-id TEXT
```

**Example:**
```bash
adobe aep dataset enable-profile \
  --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e"

# Output:
# ✅ Profile enabled for dataset: Customer Profiles Dataset
# Data will now contribute to unified customer profiles
```

---

### adobe aep dataset enable-identity

Enable Identity Service for a dataset.

**Usage:**
```bash
adobe aep dataset enable-identity --dataset-id TEXT
```

**Example:**
```bash
adobe aep dataset enable-identity \
  --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e"

# Output:
# ✅ Identity Service enabled for dataset
# Identity graphs will be built from this data
```

---

### adobe aep dataset create-batch

Create a new batch for data ingestion.

**Usage:**
```bash
adobe aep dataset create-batch --dataset-id TEXT
```

**Example:**
```bash
adobe aep dataset create-batch \
  --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e"

# Output:
# ✅ Batch created successfully
# Batch ID: batch-20260203-a1b2c3d4
# Status: loading
# 
# Use this batch ID to upload data files
```

---

### adobe aep dataset batch-status

Check the status of a batch ingestion.

**Usage:**
```bash
adobe aep dataset batch-status --batch-id TEXT
```

**Example:**
```bash
adobe aep dataset batch-status --batch-id "batch-20260203-a1b2c3d4"

# Output:
# ╭─ Batch Status ──────────────────────────╮
# │                                          │
# │ Batch ID: batch-20260203-a1b2c3d4        │
# │ Status: ✅ success                       │
# │ Records Ingested: 5,234                  │
# │ Records Failed: 0                        │
# │ Started: 2026-02-03T10:15:00Z            │
# │ Completed: 2026-02-03T10:18:45Z          │
# │ Duration: 3m 45s                         │
# │                                          │
# ╰──────────────────────────────────────────╯
```

---

### adobe aep dataset list-batches

List all batches for a dataset.

**Usage:**
```bash
adobe aep dataset list-batches --dataset-id TEXT [OPTIONS]
```

**Options:**
- `--dataset-id TEXT`: Dataset ID [required]
- `--limit INTEGER`: Number of batches to return (default: 10)

**Example:**
```bash
adobe aep dataset list-batches \
  --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e" \
  --limit 5

# Output:
# ╭─ Batches ───────────────────────────────────────╮
# │                                                  │
# │ 1. batch-20260203-a1b2c3d4                       │
# │    Status: success | Records: 5,234              │
# │    Date: 2026-02-03                              │
# │                                                  │
# │ 2. batch-20260201-x9y8z7w6                       │
# │    Status: success | Records: 3,120              │
# │    Date: 2026-02-01                              │
# │                                                  │
# │ 3. batch-20260130-m5n4o3p2                       │
# │    Status: failed | Records: 0                   │
# │    Date: 2026-01-30                              │
# │                                                  │
# ╰──────────────────────────────────────────────────╯
```

---

### adobe aep dataset complete-batch

Mark a batch as complete after uploading data.

**Usage:**
```bash
adobe aep dataset complete-batch --batch-id TEXT
```

**Example:**
```bash
adobe aep dataset complete-batch --batch-id "batch-20260203-a1b2c3d4"

# Output:
# ✅ Batch marked as complete
# Batch ID: batch-20260203-a1b2c3d4
# AEP will now process the uploaded data
# 
# Use 'adobe aep dataset batch-status' to monitor progress
```

---

### adobe aep dataset abort-batch

Abort a batch ingestion process.

**Usage:**
```bash
adobe aep dataset abort-batch --batch-id TEXT [--reason TEXT]
```

**Example:**
```bash
adobe aep dataset abort-batch \
  --batch-id "batch-20260203-a1b2c3d4" \
  --reason "Data quality issues detected"

# Prompt:
# ⚠️  Abort batch 'batch-20260203-a1b2c3d4'? [y/N]: y
# ✅ Batch aborted
# Reason: Data quality issues detected
```

---

## Data Ingestion Commands

### adobe aep ingest upload-file

Upload a single data file to AEP dataset.

**Usage:**
```bash
adobe aep ingest upload-file [OPTIONS]
```

**Options:**
- `--file PATH`: Path to data file (JSON/CSV/Parquet) [required]
- `--dataset-id TEXT`: Target dataset ID [required]
- `--batch-id TEXT`: Existing batch ID (optional, creates new if not provided)

**Examples:**

1. **Upload JSON file (auto-create batch):**
```bash
adobe aep ingest upload-file \
  --file examples/sample-data/customers.json \
  --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e"

# Output:
# 📦 Creating new batch...
# ✅ Batch created: batch-20260203-a1b2c3d4
# 📤 Uploading customers.json...
# ✅ Upload complete (5 records)
# 🔄 Marking batch as complete...
# ✅ Batch processing started
# 
# Monitor status: adobe aep dataset batch-status --batch-id batch-20260203-a1b2c3d4
```

2. **Upload to existing batch:**
```bash
adobe aep ingest upload-file \
  --file examples/sample-data/orders.json \
  --dataset-id "6a3b9c2d5e4f3g2b3d4e5f6g" \
  --batch-id "batch-20260203-xyz789"

# Output:
# 📤 Uploading orders.json to batch-20260203-xyz789...
# ✅ Upload complete (5 records)
# ℹ️  Remember to complete the batch when done
```

---

### adobe aep ingest upload-batch

Upload multiple files as a single batch.

**Usage:**
```bash
adobe aep ingest upload-batch [OPTIONS]
```

**Options:**
- `--files PATH [PATH ...]`: Paths to data files [required]
- `--dataset-id TEXT`: Target dataset ID [required]

**Example:**
```bash
adobe aep ingest upload-batch \
  --files examples/sample-data/customers.json examples/sample-data/orders.json \
  --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e"

# Output:
# 📦 Creating batch...
# ✅ Batch created: batch-20260203-multi
# 
# 📤 Uploading 2 files...
# [1/2] customers.json... ✅ (5 records)
# [2/2] orders.json... ✅ (5 records)
# 
# 🔄 Completing batch...
# ✅ Batch ingestion started
# Total records: 10
```

---

### adobe aep ingest upload-directory

Upload all data files from a directory.

**Usage:**
```bash
adobe aep ingest upload-directory [OPTIONS]
```

**Options:**
- `--directory PATH`: Path to directory containing data files [required]
- `--dataset-id TEXT`: Target dataset ID [required]
- `--pattern TEXT`: File pattern to match (default: *.json)

**Examples:**

1. **Upload all JSON files:**
```bash
adobe aep ingest upload-directory \
  --directory examples/sample-data \
  --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e"

# Output:
# 🔍 Scanning directory: examples/sample-data
# Found 3 JSON files
# 
# 📦 Creating batch...
# ✅ Batch created: batch-20260203-dir
# 
# 📤 Uploading files...
# [1/3] customers.json... ✅ (5 records)
# [2/3] orders.json... ✅ (5 records)
# [3/3] events.json... ✅ (8 records)
# 
# ✅ Upload complete: 18 total records
```

2. **Upload CSV files only:**
```bash
adobe aep ingest upload-directory \
  --directory ./data \
  --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e" \
  --pattern "*.csv"

# Output:
# 🔍 Scanning for *.csv files...
# Found 1 CSV file
# 
# 📤 Uploading customers.csv... ✅ (5 records)
```

---

### adobe aep ingest status

Check overall ingestion status for a dataset.

**Usage:**
```bash
adobe aep ingest status --dataset-id TEXT
```

**Example:**
```bash
adobe aep ingest status --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e"

# Output:
# ╭─ Ingestion Status ──────────────────────────╮
# │                                              │
# │ Dataset: Customer Profiles Dataset           │
# │ Total Batches: 15                            │
# │ Successful: 14                               │
# │ Failed: 1                                    │
# │ In Progress: 0                               │
# │                                              │
# │ Recent Batches:                              │
# │  - batch-20260203-a1b2c3d4: success          │
# │  - batch-20260201-x9y8z7w6: success          │
# │  - batch-20260130-m5n4o3p2: failed           │
# │                                              │
# ╰──────────────────────────────────────────────╯
```

---

## Onboarding & Tutorial Commands

### adobe onboarding start

Start interactive onboarding tutorial.

**Usage:**
```bash
adobe onboarding start [OPTIONS]
```

**Options:**
- `--scenario TEXT`: Onboarding scenario (basic, data-engineer, marketer)
- `--dry-run`: Preview without executing actions
- `--lang TEXT`: Language (en, ko) [default: en]

**Examples:**

1. **Start basic onboarding:**
```bash
adobe onboarding start --scenario basic

# Output:
# 🎓 Welcome to Adobe Experience Cloud CLI!
# 
# This tutorial will guide you through:
#  1. Initial setup and configuration
#  2. Authentication with Adobe APIs
#  3. Basic schema operations
#  4. Dataset creation
#  5. Data ingestion
# 
# Press Enter to begin...
```

2. **Start data engineer onboarding (dry-run):**
```bash
adobe onboarding start --scenario data-engineer --dry-run

# Output:
# 🎓 Data Engineer Onboarding (Dry Run Mode)
# 
# ℹ️  No actual changes will be made
# 
# Step 1/9: Configure AI Providers
# This step would: Set up Anthropic/OpenAI API keys
# 
# Continue? [y/N]:
```

3. **Start in Korean:**
```bash
adobe onboarding start --scenario basic --lang ko

# Output:
# 🎓 Adobe Experience Cloud CLI에 오신 것을 환영합니다!
# 
# 이 튜토리얼은 다음을 안내합니다:
#  1. 초기 설정 및 구성
#  ...
```

---

### adobe onboarding status

Check onboarding progress.

**Usage:**
```bash
adobe onboarding status
```

**Example:**
```bash
adobe onboarding status

# Output:
# ╭─ Onboarding Progress ───────────────────────╮
# │                                              │
# │ Scenario: data-engineer                      │
# │ Current Step: 3/9 - Upload Sample Schema     │
# │ Progress: ████████░░░░░░░░░░░ 33%           │
# │                                              │
# │ Completed Steps:                             │
# │  ✅ 1. Configure AI Providers                │
# │  ✅ 2. Initialize AEP Configuration          │
# │  🔄 3. Upload Sample Schema (current)        │
# │  ⬜ 4. Create Dataset                        │
# │  ⬜ 5. Ingest Data                           │
# │                                              │
# │ Achievements: 🏆 First Login, ⚙️ Setup Pro   │
# │                                              │
# ╰──────────────────────────────────────────────╯
```

---

### adobe onboarding next

Proceed to next onboarding step.

**Usage:**
```bash
adobe onboarding next
```

**Example:**
```bash
adobe onboarding next

# Output:
# ✅ Step 3 completed: Upload Sample Schema
# 
# 📋 Step 4/9: Create Dataset
# 
# You'll now create a dataset linked to your schema...
# [Tutorial continues...]
```

---

### adobe onboarding skip

Skip current onboarding step.

**Usage:**
```bash
adobe onboarding skip [--reason TEXT]
```

**Example:**
```bash
adobe onboarding skip --reason "Already configured manually"

# Output:
# ⏭️  Skipped Step 3: Upload Sample Schema
# Reason: Already configured manually
# 
# Moving to Step 4/9: Create Dataset
```

---

### adobe onboarding back

Go back to previous onboarding step.

**Usage:**
```bash
adobe onboarding back
```

**Example:**
```bash
adobe onboarding back

# Output:
# ⬅️  Returning to Step 2: Initialize AEP Configuration
# 
# [Previous step content displayed...]
```

---

### adobe onboarding resume

Resume interrupted onboarding session.

**Usage:**
```bash
adobe onboarding resume
```

**Example:**
```bash
adobe onboarding resume

# Output:
# 🔄 Resuming onboarding...
# Scenario: data-engineer
# Last completed: Step 3 - Upload Sample Schema
# 
# Continue from Step 4? [y/N]: y
```

---

### adobe onboarding achievements

View earned achievements.

**Usage:**
```bash
adobe onboarding achievements
```

**Example:**
```bash
adobe onboarding achievements

# Output:
# ╭─ Achievements ─────────────────────────────╮
# │                                             │
# │ 🏆 First Login                              │
# │    Completed initial CLI setup              │
# │    Earned: 2026-02-01                       │
# │                                             │
# │ ⚙️  Setup Pro                               │
# │    Configured all AEP credentials           │
# │    Earned: 2026-02-01                       │
# │                                             │
# │ 📊 Schema Master                            │
# │    Created first XDM schema                 │
# │    Earned: 2026-02-02                       │
# │                                             │
# │ 🚀 Data Ingestion Beginner                  │
# │    Successfully ingested first batch        │
# │    Earned: 2026-02-03                       │
# │                                             │
# │ Total: 4/12 achievements unlocked           │
# │                                             │
# ╰─────────────────────────────────────────────╯
```

---

### adobe onboarding reset

Reset onboarding progress.

**Usage:**
```bash
adobe onboarding reset [--keep-config]
```

**Options:**
- `--keep-config`: Keep AEP/AI configuration (only reset tutorial progress)

**Example:**
```bash
adobe onboarding reset

# Prompt:
# ⚠️  Reset all onboarding progress? This will:
#  - Clear tutorial progress
#  - Remove achievements
#  - Delete configuration (unless --keep-config)
# 
# Continue? [y/N]: y
# ✅ Onboarding reset complete
```

---

### adobe onboarding ask

Ask questions during onboarding (AI-powered).

**Usage:**
```bash
adobe onboarding ask --question TEXT
```

**Example:**
```bash
adobe onboarding ask --question "What is an XDM schema?"

# Output:
# 🤖 AI Assistant:
# 
# An XDM (Experience Data Model) schema is Adobe's standard way to 
# structure customer data. Think of it as a blueprint that defines:
# 
#  - What fields your data has (e.g., email, name, age)
#  - Data types (string, number, date)
#  - Required vs optional fields
#  - Relationships between data
# 
# XDM ensures all data in Adobe Experience Platform follows a 
# consistent format, making it easier to:
#  ✓ Combine data from different sources
#  ✓ Build unified customer profiles
#  ✓ Share data across Adobe products
# 
# Want to learn more? Try: adobe onboarding ask --question "How do I create a schema?"
```

---

### adobe onboarding clear-cache

Clear Q&A cache used in onboarding.

**Usage:**
```bash
adobe onboarding clear-cache
```

**Example:**
```bash
adobe onboarding clear-cache

# Output:
# 🗑️  Clearing Q&A cache...
# ✅ Cache cleared
# Cached questions: 0
```

---

### adobe onboarding cache-stats

View Q&A cache statistics.

**Usage:**
```bash
adobe onboarding cache-stats
```

**Example:**
```bash
adobe onboarding cache-stats

# Output:
# ╭─ Q&A Cache Statistics ─────────────────────╮
# │                                             │
# │ Total Questions Cached: 12                  │
# │ Cache Size: 45 KB                           │
# │ Last Updated: 2026-02-03 10:30:00           │
# │                                             │
# │ Most Asked Questions:                       │
# │  1. What is an XDM schema? (5 times)        │
# │  2. How do I ingest data? (3 times)         │
# │  3. What is a dataset? (2 times)            │
# │                                             │
# │ Cache Hit Rate: 85%                         │
# │                                             │
# ╰─────────────────────────────────────────────╯
```

---

## Sample Data Files

All sample data files are available in `examples/sample-data/`:

### customers.json
```json
[
  {
    "customer_id": "CUST-001",
    "email": "alice.johnson@example.com",
    "first_name": "Alice",
    "last_name": "Johnson",
    "date_of_birth": "1985-03-15",
    "account_created": "2024-01-10T08:30:00Z",
    "customer_tier": "gold",
    "lifetime_value": 4250.75
  }
  // ... 4 more records
]
```

### orders.json
```json
[
  {
    "order_id": "ORD-2026-001",
    "customer_id": "CUST-001",
    "order_date": "2026-01-15T10:30:00Z",
    "order_total": 249.99,
    "order_status": "delivered"
  }
  // ... 4 more records
]
```

### events.json
```json
[
  {
    "event_id": "EVT-001",
    "event_type": "page_view",
    "timestamp": "2026-02-01T10:15:30Z",
    "customer_id": "CUST-001",
    "page_url": "/products/wireless-headphones"
  }
  // ... 7 more records
]
```

### customers.csv
```csv
customer_id,email,first_name,last_name,customer_tier,lifetime_value
CUST-001,alice.johnson@example.com,Alice,Johnson,gold,4250.75
CUST-002,bob.smith@example.com,Bob,Smith,silver,1850.50
...
```

### sample_schema.json
XDM-compliant Customer Profile schema template

---

## Quick Start Examples

### Complete Workflow: Schema → Dataset → Ingest

```bash
# 1. Configure AI and AEP
adobe ai set-key --provider anthropic --interactive
adobe aep init

# 2. Create schema from sample data
adobe aep schema create \
  --from-sample examples/sample-data/customers.json \
  --name "CustomerProfile" \
  --upload

# 3. Create dataset
adobe aep dataset create \
  --name "Customer Data Feb 2026" \
  --schema-id "https://ns.adobe.com/tenant/schemas/customer-v1"

# 4. Ingest data
adobe aep ingest upload-file \
  --file examples/sample-data/customers.json \
  --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e"

# 5. Check status
adobe aep ingest status --dataset-id "5f2a8b1c4d3e2f1a2b3c4d5e"
```

---

## Common ID Formats Reference

- **Schema IDs**: `https://ns.adobe.com/{tenant}/schemas/{name}-{version}`
- **Dataset IDs**: 24-character hex string (e.g., `5f2a8b1c4d3e2f1a2b3c4d5e`)
- **Batch IDs**: `batch-{YYYYMMDD}-{random}` (e.g., `batch-20260203-a1b2c3d4`)
- **Field Group IDs**: `https://ns.adobe.com/xdm/context/{name}`
- **Organization IDs**: `{CODE}@AdobeOrg` (e.g., `ABC123@AdobeOrg`)

---

## Additional Resources

- **Installation**: See [INSTALL.md](INSTALL.md)
- **Adobe Setup**: See [docs/ADOBE_SETUP.md](docs/ADOBE_SETUP.md)
- **API Documentation**: https://developer.adobe.com/experience-platform-apis/
- **GitHub**: https://github.com/neep305/adobe-code-cli
- **Issues**: https://github.com/neep305/adobe-code-cli/issues

---

**Last Updated**: 2026-02-03  
**CLI Version**: 0.2.0
