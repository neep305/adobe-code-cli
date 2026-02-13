# Troubleshooting: upload-and-validate Command

## Pre-flight Checklist

Before running `aep schema upload-and-validate`, verify:

### 1. Authentication Setup

```bash
# Test your AEP credentials
adobe auth test
```

**Expected output:**
```
✓ Authentication successful!
```

**If failed:**
- Check `.env` file exists and has valid credentials
- Verify credentials in Adobe Developer Console
- Ensure OAuth Server-to-Server is configured

### 2. AI Configuration (if using --use-ai)

```bash
# List configured AI keys
adobe ai list-keys
```

**Expected output:**
```
openai: ✓ Configured
anthropic: ✓ Configured  
```

**If AI key missing:**
```bash
# Add Anthropic key (recommended for schema work)
adobe ai set-key anthropic

# Or add OpenAI key
adobe ai set-key openai
```

### 3. File Paths

```bash
# Verify sample files exist
ls examples/validation-demo/sample_customers.json
ls examples/validation-demo/actual_customers.json
```

## Common Errors & Solutions

### Error: "401 Unauthorized" or "Authentication failed"

**Problem:** Invalid or expired AEP credentials

**Solution:**
1. Run `adobe auth test` to verify
2. Check `.env` file:
   ```bash
   cat .env | grep AEP_
   ```
3. Regenerate credentials in Adobe Developer Console if needed
4. Ensure these are present:
   - `AEP_CLIENT_ID`
   - `AEP_CLIENT_SECRET`
   - `AEP_ORG_ID`
   - `AEP_TECHNICAL_ACCOUNT_ID`

### Error: "403 Forbidden"

**Problem:** Missing Schema Registry permissions

**Solution:**
1. Go to Adobe Developer Console
2. Select your project
3. Navigate to APIs & Services
4. Check "Experience Platform API" permissions
5. Ensure "Manage Schemas" is enabled

### Error: "Anthropic API key not configured"

**Problem:** Missing AI API key when using `--use-ai`

**Solution Option 1 (Quick - skip AI):**
```bash
# Run without AI
aep schema upload-and-validate \
  --name "Test" \
  --from-sample examples/validation-demo/sample_customers.json \
  --validate-data examples/validation-demo/actual_customers.json \
  --no-ai
```

**Solution Option 2 (Configure AI):**
```bash
# Add Anthropic key
adobe ai set-key anthropic
# Then retry with --use-ai
```

### Error: "Schema already exists"

**Problem:** Schema with same name already uploaded to AEP

**Solution Option 1 (Change name):**
```bash
aep schema upload-and-validate \
  --name "Customer Profile Demo v2" \  # Different name
  --from-sample examples/validation-demo/sample_customers.json \
  --validate-data examples/validation-demo/actual_customers.json
```

**Solution Option 2 (Delete existing schema):**
```bash
# List schemas to find ID
aep schema list

# Get full schema details
aep schema get <SCHEMA_ID>

# Delete (if you're sure)
# Note: This cannot be undone!
# (Delete command not yet implemented - use AEP UI for now)
```

### Error: "File not found"

**Problem:** Incorrect file path

**Solution:**
```bash
# Check current directory
pwd

# Use absolute paths if needed
aep schema upload-and-validate \
  --name "Test" \
  --from-sample "C:/full/path/to/sample.json" \
  --validate-data "C:/full/path/to/actual.json"

# Or navigate to project root first
cd C:/dev/ai-project/adobe-code
```

### Error: "Sandbox not found"

**Problem:** Invalid sandbox name in `.env`

**Solution:**
1. Check current sandbox:
   ```bash
   cat .env | grep SANDBOX
   ```
2. List available sandboxes in AEP UI
3. Update `.env`:
   ```
   AEP_SANDBOX_NAME=your-sandbox-name
   ```

## Debugging Tips

### Enable Verbose Output

The command already shows detailed errors. For more info:

```bash
# Run with Python directly to see full stack trace
python -m adobe_experience.cli.main aep schema upload-and-validate \
  --name "Test" \
  --from-sample examples/validation-demo/sample_customers.json \
  --validate-data examples/validation-demo/actual_customers.json
```

### Test Individual Steps

Break down the workflow:

```bash
# Step 1: Test schema creation (without upload)
aep schema create \
  --name "Test Schema" \
  --from-sample examples/validation-demo/sample_customers.json \
  --output test-schema.json

# Step 2: Test upload manually (not yet implemented)
# Coming in future version

# Step 3: Test validation separately (not yet standalone command)
# Coming in Week 1
```

### Check Logs

```powershell
# Check recent errors in PowerShell
$Error[0] | Format-List * -Force
```

## Minimal Working Example

If everything fails, try this minimal test:

```bash
# 1. Verify auth
adobe auth test

# 2. Create tiny test file
echo '[{"id": 1, "name": "test"}]' > test.json

# 3. Run without AI
aep schema upload-and-validate \
  --name "Minimal Test" \
  --from-sample test.json \
  --validate-data test.json \
  --no-ai
```

If this works, the issue is with your data files or AI configuration.

## Getting Help

If none of these solutions work:

1. Capture full error output
2. Check configuration:
   ```bash
   adobe auth status
   adobe ai list-keys
   ```
3. Try the minimal working example above
4. Note which step fails (Generate/Upload/Validate/Report)
