# Batch API Call Examples

## Example 1: Customer Information Query

### Input File (customers.json)
```json
[
  {"customer_id": "C001", "name": "Alice"},
  {"customer_id": "C002", "name": "Bob"},
  {"customer_id": "C003", "name": "Charlie"}
]
```

### Config File (config.json)
```json
{
  "base_url": "https://api.company.com",
  "endpoint": "/v1/customers/{customer_id}",
  "method": "GET",
  "headers": {
    "Authorization": "Bearer YOUR_API_TOKEN"
  },
  "id_field": "customer_id",
  "concurrency": 3,
  "retry_count": 2
}
```

### Execution
```bash
python scripts/batch_request.py -c config.json -i customers.json -o results.json
```

### Expected Output
```json
{
  "status": "completed",
  "total": 3,
  "success": 3,
  "failed": 0,
  "results": [
    {
      "input": {"customer_id": "C001", "name": "Alice"},
      "output": {"id": "C001", "email": "alice@company.com", "phone": "+1-555-001"},
      "status": "success"
    },
    {
      "input": {"customer_id": "C002", "name": "Bob"},
      "output": {"id": "C002", "email": "bob@company.com", "phone": "+1-555-002"},
      "status": "success"
    },
    {
      "input": {"customer_id": "C003", "name": "Charlie"},
      "output": {"id": "C003", "email": "charlie@company.com", "phone": "+1-555-003"},
      "status": "success"
    }
  ]
}
```

---

## Example 2: Product Search with POST

### Input File (products.json)
```json
[
  {"product_name": "iPhone 15", "category": "electronics"},
  {"product_name": "MacBook Pro", "category": "electronics"},
  {"product_name": "AirPods", "category": "electronics"}
]
```

### Config File (config.json)
```json
{
  "base_url": "https://search.api.com",
  "endpoint": "/v1/search",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "X-API-Key": "YOUR_API_KEY"
  },
  "request_body": {
    "query": "{product_name}",
    "category": "{category}",
    "limit": 10
  },
  "id_field": "product_name",
  "response_data_path": "$.results",
  "concurrency": 2
}
```

### Execution
```bash
python scripts/batch_request.py -c config.json -i products.json -o search_results.json
```

---

## Example 3: Order Status Update

### Input File (orders.csv)
```csv
order_id,new_status,updated_by
ORD-001,shipped,system
ORD-002,delivered,system
ORD-003,cancelled,admin
```

### Config File (config.json)
```json
{
  "base_url": "https://orders.api.com",
  "endpoint": "/v1/orders/{order_id}/status",
  "method": "PUT",
  "headers": {
    "Authorization": "Bearer YOUR_TOKEN",
    "Content-Type": "application/json"
  },
  "request_body": {
    "status": "{new_status}",
    "updated_by": "{updated_by}"
  },
  "id_field": "order_id",
  "timeout": 60
}
```

### Execution
```bash
python scripts/batch_request.py -c config.json -i orders.csv -o update_results.json
```

---

## Example 4: Resume Interrupted Task

When a batch is interrupted (Ctrl+C or crash), resume from where it stopped:

```bash
# First run (interrupted)
python scripts/batch_request.py -c config.json -i large_file.json -o results.json
# Output: Progress: 150/500... (Ctrl+C)
# Saved to results.json.progress.json

# Resume
python scripts/batch_request.py -c config.json -i large_file.json -o results.json --resume
# Output: Resuming from progress: 150 items already processed
#         Processing 350 items...
```

---

## Example 5: Error Handling and Retry

### Config with Retry Settings
```json
{
  "base_url": "https://unstable.api.com",
  "endpoint": "/data/{id}",
  "method": "GET",
  "headers": {"Authorization": "Bearer TOKEN"},
  "id_field": "id",
  "retry_count": 5,
  "retry_delay": 2,
  "timeout": 60
}
```

### Output with Errors
```json
{
  "status": "completed",
  "total": 100,
  "success": 95,
  "failed": 5,
  "errors": [
    {
      "input": {"id": "ERR001"},
      "error": "HTTP 404: Not Found",
      "status": "failed"
    },
    {
      "input": {"id": "ERR002"},
      "error": "Connection timeout after 60s",
      "status": "failed"
    }
  ]
}
```

Errors are also logged to `results.json.errors.jsonl` for further analysis.

---

## Example 6: Complex Template Substitution

### Input File
```json
[
  {
    "api_token": "token123",
    "org_id": "ORG001",
    "user_id": "USER001",
    "query_text": "search term"
  }
]
```

### Config File
```json
{
  "base_url": "https://api.service.com",
  "endpoint": "/orgs/{org_id}/users/{user_id}/search",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer {api_token}",
    "X-Org-ID": "{org_id}"
  },
  "url_params": {
    "user": "{user_id}"
  },
  "request_body": {
    "query": "{query_text}",
    "org": "{org_id}"
  },
  "id_field": "user_id"
}
```

All `{field}` placeholders are replaced with values from each input item.