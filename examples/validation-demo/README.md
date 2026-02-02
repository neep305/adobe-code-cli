# Week 0: Schema Upload & Validation MVP - Demo

This demo showcases the end-to-end workflow: Schema creation → AEP upload → Data validation → AI-powered insights.

## Files

- `sample_customers.json` - Clean sample data used to generate the schema
- `actual_customers.json` - Real-world data with various issues:
  - Type mismatches (age as string instead of integer)
  - Format violations (invalid email format)
  - Missing fields (some records lack fields present in others)
  - Extra fields (loyalty_points, phone, premium_member not in schema)

## Running the Demo

### Basic Usage

```bash
adobe aep schema upload-and-validate \
  --name "Customer Profile Demo" \
  --from-sample examples/validation-demo/sample_customers.json \
  --validate-data examples/validation-demo/actual_customers.json \
  --use-ai
```

### Without AI (faster, basic validation only)

```bash
adobe aep schema upload-and-validate \
  --name "Customer Profile Demo" \
  --from-sample examples/validation-demo/sample_customers.json \
  --validate-data examples/validation-demo/actual_customers.json \
  --no-ai
```

### Custom Class (ExperienceEvent instead of Profile)

```bash
adobe aep schema upload-and-validate \
  --name "Customer Events Demo" \
  --from-sample examples/validation-demo/sample_customers.json \
  --validate-data examples/validation-demo/actual_customers.json \
  --class-id "https://ns.adobe.com/xdm/context/experienceevent" \
  --use-ai
```

## Expected Output

### Workflow Steps

```
╭─────────────────────────────────────────────────╮
│ Schema Upload & Validation Workflow            │
│ Step 1: Generate Schema                        │
│ Step 2: Upload to AEP                          │
│ Step 3: Validate Data                          │
│ Step 4: Show Report                            │
╰─────────────────────────────────────────────────╯
```

### Validation Report

The command will show:

1. **Overall Status** - Passed/Failed/Passed with Warnings
2. **Statistics** - Total records, critical/warning/info counts
3. **AI Analysis** - Summary of main issues and recommendations
4. **Detailed Issues Table** - Grouped by severity:
   - **CRITICAL** (red) - Type mismatches, schema violations
   - **WARNING** (yellow) - Format issues, potential problems
   - **INFO** (blue) - Extra fields, suggestions

### Example Issues Detected

```
CRITICAL Issues:
┌─────────────┬───────────────┬─────────────────────────┬────────────────────────┐
│ Field       │ Issue Type    │ Message                 │ Suggestion             │
├─────────────┼───────────────┼─────────────────────────┼────────────────────────┤
│ age         │ type_mismatch │ Type mismatch in 'age'  │ Convert 'age' to       │
│             │               │                         │ integer                │
└─────────────┴───────────────┴─────────────────────────┴────────────────────────┘

WARNING Issues:
┌─────────────┬─────────────────┬───────────────────────────┬──────────────────────┐
│ Field       │ Issue Type      │ Message                   │ Suggestion           │
├─────────────┼─────────────────┼───────────────────────────┼──────────────────────┤
│ email       │ format_mismatch │ Field 'email' does not    │ Update schema or fix │
│             │                 │ match expected format     │ data format          │
└─────────────┴─────────────────┴───────────────────────────┴──────────────────────┘

INFO Issues:
┌─────────────────┬─────────────┬───────────────────────────────┬───────────────────┐
│ Field           │ Issue Type  │ Message                       │ Suggestion        │
├─────────────────┼─────────────┼───────────────────────────────┼───────────────────┤
│ loyalty_points  │ extra_field │ Field exists in data but not  │ Add field to      │
│                 │             │ in schema                     │ schema            │
│ phone           │ extra_field │ Field exists in data but not  │ Add field to      │
│                 │             │ in schema                     │ schema            │
└─────────────────┴─────────────┴───────────────────────────────┴───────────────────┘
```

## What's Validated

- ✅ **Type Correctness** - String, number, integer, boolean, object, array
- ✅ **Format Compliance** - Email, URI, date, date-time
- ✅ **Schema Completeness** - Missing fields in data
- ✅ **Data Completeness** - Extra fields not in schema
- ✅ **AI Insights** - Contextual recommendations (when --use-ai)

## Next Steps

After validation, you can:
1. Fix data issues identified in the report
2. Update schema to accommodate new fields
3. Use JSON Patch to modify schema (coming in Week 2)
4. Set up continuous validation with `--watch` mode (coming in Week 4)

## Troubleshooting

### "Schema already exists"
The schema is uploaded to AEP, so running the same command twice will fail. Either:
- Delete the schema from AEP first
- Change the `--name` parameter

### "Authentication failed"
Ensure your `.env` file has valid credentials:
```bash
adobe auth test
```

### "AI summary not generated"
Check that your Anthropic API key is configured:
```bash
adobe ai list-keys
```
