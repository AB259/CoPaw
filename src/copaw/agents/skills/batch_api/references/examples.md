# 批量API调用示例

## 示例1：客户信息查询

### 创建任务目录
```bash
mkdir -p batch_tasks/customer_query_20240115
```

### 输入文件 (batch_tasks/customer_query_20240115/input.json)
```json
[
  {"customer_id": "C001", "name": "张三"},
  {"customer_id": "C002", "name": "李四"},
  {"customer_id": "C003", "name": "王五"}
]
```

### 配置文件 (batch_tasks/customer_query_20240115/config.json)
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

### 执行命令
```bash
python scripts/batch_request.py --workdir batch_tasks/customer_query_20240115
```

### 输出文件 (batch_tasks/customer_query_20240115/results.json)
```json
{
  "status": "completed",
  "total": 3,
  "success": 3,
  "failed": 0,
  "results": [
    {
      "input": {"customer_id": "C001", "name": "张三"},
      "output": {"id": "C001", "email": "zhangsan@company.com", "phone": "138-0000-0001"},
      "status": "success"
    },
    {
      "input": {"customer_id": "C002", "name": "李四"},
      "output": {"id": "C002", "email": "lisi@company.com", "phone": "138-0000-0002"},
      "status": "success"
    },
    {
      "input": {"customer_id": "C003", "name": "王五"},
      "output": {"id": "C003", "email": "wangwu@company.com", "phone": "138-0000-0003"},
      "status": "success"
    }
  ]
}
```

---

## 示例2：产品搜索（POST请求）

### 任务目录结构
```
batch_tasks/product_search_20240116/
├── config.json
├── input.json
└── results.json  (脚本生成)
```

### 输入文件 (input.json)
```json
[
  {"product_name": "iPhone 15", "category": "电子产品"},
  {"product_name": "MacBook Pro", "category": "电子产品"},
  {"product_name": "AirPods", "category": "电子产品"}
]
```

### 配置文件 (config.json)
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

### 执行命令
```bash
python scripts/batch_request.py --workdir batch_tasks/product_search_20240116
```

---

## 示例3：订单状态更新（CSV输入）

### 任务目录结构
```
batch_tasks/order_update_20240117/
├── config.json
├── input.csv
└── results.json
```

### 输入文件 (input.csv)
```csv
order_id,new_status,updated_by
ORD-001,已发货,系统
ORD-002,已签收,系统
ORD-003,已取消,管理员
```

### 配置文件 (config.json)
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

### 执行命令
```bash
python scripts/batch_request.py --workdir batch_tasks/order_update_20240117
```

---

## 示例4：中断恢复

当批量任务被中断（Ctrl+C或崩溃）时，可以从中断处继续：

```bash
# 第一次运行（被中断）
python scripts/batch_request.py --workdir batch_tasks/large_task_20240118
# 输出: 进度: 150/500 (150 成功, 0 失败) ... (Ctrl+C)
# 进度保存到 batch_tasks/large_task_20240118/results.json.progress.json

# 恢复执行
python scripts/batch_request.py --workdir batch_tasks/large_task_20240118 --resume
# 输出: 从进度恢复: 已处理 150 个项目
#       正在处理 350 个项目（总数: 500，已完成: 150）
```

---

## 示例5：错误处理与重试

### 配置重试参数 (config.json)
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

### 带错误的输出结果 (results.json)
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

错误同时记录在`results.json.errors.jsonl`文件中。

---

## 示例6：复杂模板替换

### 输入文件 (input.json)
```json
[
  {
    "api_token": "token123",
    "org_id": "ORG001",
    "user_id": "USER001",
    "query_text": "搜索关键词"
  }
]
```

### 配置文件 (config.json)
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

所有`{字段}`占位符都会被输入数据中对应的值替换。

---

## 完整任务目录示例

```
batch_tasks/
├── customer_query_20240115/
│   ├── config.json
│   ├── input.json
│   └── results.json
├── product_search_20240116/
│   ├── config.json
│   ├── input.json
│   ├── results.json
│   └── results.json.errors.jsonl   # 有错误时生成
├── order_update_20240117/
│   ├── config.json
│   ├── input.csv
│   └── results.json
└── large_task_20240118/
    ├── config.json
    ├── input.json
    ├── results.json
    └── results.json.progress.json   # 未完成任务存在
```