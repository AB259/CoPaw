---
name: batch_api
description: "Use this skill when the user needs to make API calls to many endpoints in bulk - such as querying customer data for hundreds of customers, fetching product info for a product list, or any task requiring repeated API calls with different parameters. The skill handles batch execution, progress tracking, error recovery, and result storage without occupying model context. Trigger when user mentions 'batch', 'bulk', 'loop through', or has a list of items to query via API."
---

# Batch API Call Guide

## Overview

This skill provides a script for executing bulk API requests efficiently. The script handles:
- Reading input data from JSON/CSV files
- Template-based URL and request body construction
- Progress tracking with interrupt/resume support
- Error handling and automatic retry
- Result storage to files

**When to use:**
- Querying data for 10+ items via API (customers, products, orders, etc.)
- User mentions "batch", "bulk", "loop through all"
- Processing a list from a file with API calls
- Need progress tracking for long-running API tasks

## Quick Start

### Step 1: Prepare Input File

Create a JSON or CSV file with the items to process.

**JSON format (input.json):**
```json
[
  {"customer_id": "C001", "name": "Alice"},
  {"customer_id": "C002", "name": "Bob"}
]
```

**CSV format (input.csv):**
```csv
customer_id,name
C001,Alice
C002,Bob
```

### Step 2: Create Config File

Create a config JSON file specifying the API endpoint and parameters:

```json
{
  "base_url": "https://api.example.com",
  "endpoint": "/customers/{customer_id}",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer YOUR_TOKEN"
  },
  "id_field": "customer_id"
}
```

### Step 3: Run the Script

```bash
python scripts/batch_request.py --config config.json --input input.json --output results.json
```

## Configuration Reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `base_url` | string | required | API base URL |
| `endpoint` | string | required | Endpoint path with `{field}` placeholders |
| `method` | string | GET | HTTP method: GET, POST, PUT, DELETE, PATCH |
| `headers` | object | {} | HTTP headers (supports `{field}` placeholders) |
| `request_body` | object | null | Request body for POST/PUT/PATCH |
| `url_params` | object | {} | URL query parameters |
| `response_data_path` | string | "$" | JSONPath to extract data from response |
| `id_field` | string | "id" | Field name for progress tracking |
| `timeout` | number | 30 | Request timeout in seconds |
| `retry_count` | number | 3 | Number of retries on failure |
| `retry_delay` | number | 1 | Delay between retries in seconds |
| `concurrency` | number | 1 | Concurrent requests (max: 10) |
| `delay_between_requests` | number | 0 | Delay between requests in seconds |

## Template Placeholders

Use `{field_name}` to substitute values from input data:

**URL Path:**
```
/customers/{customer_id}/orders/{order_id}
```

**Headers:**
```json
{
  "Authorization": "Bearer {api_token}",
  "X-Customer-ID": "{customer_id}"
}
```

**Request Body:**
```json
{
  "query": "{name}",
  "filters": {"id": "{customer_id}"}
}
```

## Output Files

### results.json
```json
{
  "status": "completed",
  "total": 200,
  "success": 198,
  "failed": 2,
  "start_time": "2024-01-15T10:30:00Z",
  "end_time": "2024-01-15T10:45:00Z",
  "duration_seconds": 900,
  "results": [
    {
      "input": {"customer_id": "C001", "name": "Alice"},
      "output": {"id": "C001", "email": "alice@example.com"},
      "status": "success"
    }
  ],
  "errors": [
    {
      "input": {"customer_id": "C199"},
      "error": "404 Not Found",
      "status": "failed"
    }
  ]
}
```

### progress.json (auto-generated)
Tracks progress for interrupt/resume:
```json
{
  "processed_ids": ["C001", "C002"],
  "last_index": 50,
  "timestamp": "2024-01-15T10:35:00Z"
}
```

## Progress Tracking

The script automatically tracks progress. If interrupted:

1. Re-run with `--resume` flag
2. Script detects progress file and continues from where it stopped

```bash
# Resume interrupted batch
python scripts/batch_request.py --config config.json --input input.json --output results.json --resume
```

## Error Handling

- **Automatic Retry**: Failed requests retry based on `retry_count`
- **Error Logging**: Errors logged to `output.errors.jsonl`
- **Continue on Error**: Processing continues after failures
- **Final Summary**: All errors summarized in results.json

## Advanced Usage

### POST with Request Body

```json
{
  "base_url": "https://api.example.com",
  "endpoint": "/search",
  "method": "POST",
  "headers": {"Content-Type": "application/json"},
  "request_body": {
    "query": "{search_term}",
    "limit": 10
  }
}
```

### Concurrent Requests

```json
{
  "concurrency": 5,
  "delay_between_requests": 0.1
}
```

### Custom Response Extraction

Use JSONPath in `response_data_path`:
```json
{
  "response_data_path": "$.data.items"
}
```

## Workflow for Agent

1. **Clarify requirements**: Confirm API endpoint, input data source, expected output
2. **Prepare config**: Create config.json with endpoint details
3. **Prepare input**: Create or identify input data file
4. **Run script**: Execute batch_request.py
5. **Check results**: Read results.json to summarize
6. **Report to user**: Summarize success/failure counts and errors

## Command Reference

```bash
# Basic usage
python scripts/batch_request.py --config CONFIG --input INPUT --output OUTPUT

# Resume interrupted task
python scripts/batch_request.py -c config.json -i input.json -o results.json --resume

# Force overwrite existing output
python scripts/batch_request.py -c config.json -i input.json -o results.json --force

# Custom progress/errors file paths
python scripts/batch_request.py -c config.json -i input.json -o results.json \
  --progress my_progress.json --errors my_errors.jsonl

# Show help
python scripts/batch_request.py --help
```

## Example Scenarios

### Scenario 1: Query Customer Details

User: "Query the customer API for all 200 customers in customer_list.json"

Steps:
1. Read customer_list.json to understand structure
2. Create config.json with endpoint `/customers/{customer_id}`
3. Run: `python scripts/batch_request.py -c config.json -i customer_list.json -o customer_details.json`
4. Summarize results from customer_details.json

### Scenario 2: Bulk Product Lookup from CSV

User: "Get product info for all product IDs in products.csv"

Steps:
1. Read products.csv header
2. Create config.json with appropriate endpoint
3. Run: `python scripts/batch_request.py -c config.json -i products.csv -o product_info.json`
4. Report results

### Scenario 3: Batch POST Requests

User: "Update status for all orders in orders.json"

Steps:
1. Read orders.json structure
2. Create config.json with POST method and request body template
3. Run: `python scripts/batch_request.py -c config.json -i orders.json -o update_results.json --method POST`
4. Report results

## Code Style Guidelines

- Keep Python code minimal and concise
- Avoid unnecessary comments and verbose variable names
- Focus on the task at hand