---
name: batch_api
description: "当用户需要对大量外部接口进行批量调用时使用此skill。例如：查询数百个客户的信息、获取产品列表数据、或任何需要重复调用API且参数不同的场景。该skill通过脚本自动处理批量执行、进度追踪、错误恢复，并将结果存储到独立任务目录中，不占用模型上下文。触发条件：用户提到'批量'、'循环'、'逐个查询'，或有一个列表需要通过API处理。"
---

# 批量API调用指南

## 概述

本skill提供了一个高效的批量API请求执行脚本，主要功能：
- 从JSON/CSV文件读取输入数据
- 基于模板构建URL和请求体
- 进度追踪，支持中断恢复
- 错误处理和自动重试
- **强制独立任务目录，避免污染工作空间**
- 结果存储到文件

**适用场景：**
- 需要为10个以上项目调用API查询数据（客户、产品、订单等）
- 用户提到"批量"、"循环处理"、"逐个查询"
- 从文件读取列表并通过API处理
- 长时间运行的API任务需要进度追踪

## 工作目录结构

**每个批量任务必须放在独立目录中。**

目录结构：
```
batch_tasks/
├── customer_query_20240115/     # 任务目录（任务名+日期命名）
│   ├── config.json              # 配置文件（必需）
│   ├── input.json               # 输入数据（必需）
│   ├── results.json             # 输出结果（脚本生成）
│   ├── results.json.progress.json  # 进度文件（脚本生成，完成后删除）
│   └── results.json.errors.jsonl   # 错误日志（有错误时生成）
├── product_query_20240116/
│   ├── config.json
│   ├── input.csv
│   └── results.json
└── ...
```

## 快速开始

### 第一步：创建任务目录

```bash
mkdir -p batch_tasks/customer_query_20240115
```

### 第二步：准备输入文件

在任务目录中创建`input.json`或`input.csv`：

**JSON格式：**
```json
[
  {"customer_id": "C001", "name": "张三"},
  {"customer_id": "C002", "name": "李四"}
]
```

**CSV格式：**
```csv
customer_id,name
C001,张三
C002,李四
```

### 第三步：创建配置文件

在任务目录中创建`config.json`：

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

### 第四步：执行脚本

```bash
python scripts/batch_request.py --workdir batch_tasks/customer_query_20240115
```

## 配置参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `base_url` | string | 必填 | API基础URL |
| `endpoint` | string | 必填 | 端点路径，支持`{字段}`占位符 |
| `method` | string | GET | HTTP方法：GET, POST, PUT, DELETE, PATCH |
| `headers` | object | {} | HTTP请求头，支持`{字段}`占位符 |
| `request_body` | object | null | POST/PUT/PATCH请求体 |
| `url_params` | object | {} | URL查询参数 |
| `response_data_path` | string | "$" | 从响应中提取数据的JSONPath |
| `id_field` | string | "id" | 用于进度追踪的字段名 |
| `timeout` | number | 30 | 请求超时时间（秒） |
| `retry_count` | number | 3 | 失败重试次数 |
| `retry_delay` | number | 1 | 重试间隔（秒） |
| `concurrency` | number | 1 | 并发请求数（最大10） |
| `delay_between_requests` | number | 0 | 请求间隔（秒） |

## 模板占位符

使用`{字段名}`从输入数据中替换值：

**URL路径：**
```
/customers/{customer_id}/orders/{order_id}
```

**请求头：**
```json
{
  "Authorization": "Bearer {api_token}",
  "X-Customer-ID": "{customer_id}"
}
```

**请求体：**
```json
{
  "query": "{name}",
  "filters": {"id": "{customer_id}"}
}
```

## 输出文件

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
      "input": {"customer_id": "C001", "name": "张三"},
      "output": {"id": "C001", "email": "zhangsan@example.com"},
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

### progress.json（自动生成）
追踪进度，用于中断恢复：
```json
{
  "processed_ids": ["C001", "C002"],
  "last_index": 50,
  "timestamp": "2024-01-15T10:35:00Z"
}
```

## 中断恢复

脚本自动追踪进度。如果中断：

1. 使用`--resume`参数重新执行
2. 脚本检测进度文件并从中断处继续

```bash
python scripts/batch_request.py --workdir batch_tasks/customer_query_20240115 --resume
```

## 错误处理

- **自动重试**：失败的请求根据`retry_count`自动重试
- **错误日志**：错误记录到`results.json.errors.jsonl`文件
- **继续执行**：出错后继续处理后续项目
- **汇总报告**：最终结果中包含所有错误信息

## 高级用法

### POST请求带请求体

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

### 并发请求

```json
{
  "concurrency": 5,
  "delay_between_requests": 0.1
}
```

### 自定义响应提取

使用JSONPath从响应中提取特定数据：
```json
{
  "response_data_path": "$.data.items"
}
```

## Agent工作流程

1. **明确需求**：确认API端点、输入数据来源、期望输出
2. **创建任务目录**：`mkdir -p batch_tasks/任务名_日期`
3. **准备配置**：在任务目录创建config.json
4. **准备输入**：在任务目录创建input.json或input.csv
5. **执行脚本**：使用`--workdir`参数执行
6. **检查结果**：读取任务目录中的results.json汇总结果
7. **向用户报告**：总结成功/失败数量和错误信息

## 命令参考

```bash
# 基本用法
python scripts/batch_request.py --workdir batch_tasks/customer_query_20240115

# 恢复中断的任务
python scripts/batch_request.py --workdir batch_tasks/customer_query_20240115 --resume

# 强制重新开始
python scripts/batch_request.py --workdir batch_tasks/customer_query_20240115 --force

# 自定义文件名（在workdir下，默认为config.json/input.json/results.json）
python scripts/batch_request.py --workdir batch_tasks/task1 -c my_config.json -i my_input.csv

# 查看帮助
python scripts/batch_request.py --help
```

## 示例场景

### 场景1：查询客户详情

用户："查询customer_list.json中所有200个客户的API信息"

步骤：
1. 创建任务目录：`mkdir -p batch_tasks/customer_query_20240115`
2. 将customer_list.json移动到任务目录并重命名为input.json
3. 在任务目录创建config.json，端点设为`/customers/{customer_id}`
4. 执行：`python scripts/batch_request.py --workdir batch_tasks/customer_query_20240115`
5. 从results.json汇总结果

### 场景2：从CSV批量查询产品

用户："获取products.csv中所有产品ID的产品信息"

步骤：
1. 创建任务目录：`mkdir -p batch_tasks/product_query_20240116`
2. 将products.csv移动到任务目录并重命名为input.csv
3. 在任务目录创建config.json配置适当的端点
4. 执行：`python scripts/batch_request.py --workdir batch_tasks/product_query_20240116`
5. 报告结果

### 场景3：批量POST请求

用户："更新orders.json中所有订单的状态"

步骤：
1. 创建任务目录：`mkdir -p batch_tasks/order_update_20240117`
2. 将orders.json移动到任务目录并重命名为input.json
3. 在任务目录创建config.json，使用POST方法和请求体模板
4. 执行：`python scripts/batch_request.py --workdir batch_tasks/order_update_20240117`
5. 报告结果

## 代码风格

- Python代码保持简洁
- 避免不必要的注释和冗长的变量名
- 专注于当前任务