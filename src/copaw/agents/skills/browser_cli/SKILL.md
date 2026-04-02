---
name: browser_cli
description: "将浏览器操作沉淀为可复用的CLI命令。录制浏览器操作序列，生成参数化Shell脚本，把浏览网站变成CLI应用。触发条件：用户提到'录制浏览器'、'保存浏览器操作'、'浏览器脚本'、'重复浏览器操作'、'把网站变成命令'、'浏览器CLI'、'生成浏览器命令'。"
metadata:
  copaw:
    emoji: "🌐"
    requires:
      packages: ["playwright"]
---

# 浏览器CLI录制器

## 概述

本skill提供浏览器操作的录制、脚本生成和回放功能，让用户可以把常用的浏览器操作变成可复用的CLI命令。

**核心功能：**
1. **操作录制**：记录browser_use的action序列，保存为配置文件
2. **脚本生成**：转换为参数化Shell脚本，支持CLI参数
3. **回放执行**：使用已保存脚本自动化浏览器操作

---

## 适用场景

- 用户说"帮我录制这个登录流程"
- 用户说"把查询操作变成一个命令"
- 用户说"保存浏览器操作，下次直接调用"
- 用户说"生成一个浏览器脚本"
- 需要重复执行相同的网页操作

---

## 工作目录结构

```
~/.copaw/
├── browser_recordings/           # 录制存储目录
│   ├── login_github/
│   │   ├── recording.json        # 操作序列
│   │   ├── metadata.json         # 参数定义
│   │   └── refs_mapping.json     # 元素引用映射
│   └── search_products/
│       ├── recording.json
│       └── metadata.json
├── browser_scripts/              # 生成的脚本目录
│   ├── login_github.sh           # 可执行Shell脚本
│   ├── login_github.json         # 脚本配置
│   └── search_products.sh
```

---

## 快速开始

### 1. 录制操作

```bash
# 开始录制
python scripts/recorder.py --start --name login_github

# Agent执行browser_use操作序列...

# 结束录制
python scripts/recorder.py --stop --name login_github
```

### 2. 定义参数

创建 `~/.copaw/browser_recordings/login_github/metadata.json`：

```json
{
  "name": "login_github",
  "description": "登录GitHub",
  "parameters": [
    {
      "name": "username",
      "type": "string",
      "required": true,
      "description": "GitHub用户名",
      "cli_flag": "--username",
      "cli_short": "-u"
    },
    {
      "name": "password",
      "type": "string",
      "required": true,
      "description": "GitHub密码",
      "cli_flag": "--password",
      "cli_short": "-p",
      "sensitive": true
    }
  ],
  "cli_command": "github-login"
}
```

### 3. 生成脚本

```bash
python scripts/generator.py --recording login_github
```

### 4. 执行脚本

```bash
# 使用生成的Shell脚本
~/.copaw/browser_scripts/login_github.sh --username myuser --password mypass

# 或使用runner.py直接执行
python scripts/runner.py --recording login_github --param username=myuser --param password=mypass
```

---

## 录制模式详解

### 开始录制

```bash
python scripts/recorder.py --start --name <录制名称>
```

这会创建 `~/.copaw/browser_recordings/<名称>/` 目录。

### 记录操作

Agent执行browser_use操作时，调用recorder记录：

```bash
python scripts/recorder.py --record --name <录制名称> --action '{"action":"open","params":{"url":"https://example.com"}}'
```

### 结束录制

```bash
python scripts/recorder.py --stop --name <录制名称>
```

保存完整的recording.json文件。

---

## 录制文件格式

### recording.json

```json
{
  "name": "login_github",
  "created_at": "2026-04-01T10:00:00Z",
  "actions": [
    {
      "step": 1,
      "action": "start",
      "params": {"headed": false},
      "result_summary": "Browser started"
    },
    {
      "step": 2,
      "action": "open",
      "params": {"url": "https://github.com/login", "page_id": "default"},
      "result_summary": "Page opened"
    },
    {
      "step": 3,
      "action": "snapshot",
      "params": {"page_id": "default"},
      "refs_saved": true
    },
    {
      "step": 4,
      "action": "type",
      "params": {
        "ref": "e1",
        "text": "{username}",
        "selector": "input[name='login']",
        "element_hint": {"role": "textbox", "name": "Username"}
      }
    },
    {
      "step": 5,
      "action": "type",
      "params": {
        "ref": "e2",
        "text": "{password}",
        "selector": "input[name='password']",
        "element_hint": {"role": "textbox", "name": "Password"}
      }
    },
    {
      "step": 6,
      "action": "click",
      "params": {
        "ref": "e3",
        "selector": "input[type='submit']",
        "element_hint": {"role": "button", "name": "Sign in"}
      }
    }
  ],
  "total_steps": 6
}
```

### 元素定位策略（混合策略）

每个交互action保存三种定位方式：
- **ref**: snapshot生成的元素引用（如e1, e2）
- **selector**: CSS选择器（如`input[name="login"]`）
- **element_hint**: 元素特征（role, name, text）

执行时优先使用selector，失效时通过element_hint匹配新refs。

---

## Agent工作流程

### 录制流程

1. 用户请求录制浏览器操作
2. Agent调用 `recorder.py --start` 开始录制
3. Agent执行browser_use操作序列
4. 每个操作后调用 `recorder.py --record` 记录
5. Agent调用 `recorder.py --stop` 结束录制
6. Agent帮助用户定义metadata.json中的参数
7. Agent调用 `generator.py` 生成脚本

### 回放流程

1. 用户请求执行已保存的脚本
2. Agent确认脚本名称和参数
3. Agent调用生成的Shell脚本或直接调用runner.py
4. 脚本执行browser_use操作序列
5. Agent汇报执行结果

---

## 命令参考

### recorder.py

```bash
# 开始录制
python scripts/recorder.py --start --name <名称>

# 记录操作
python scripts/recorder.py --record --name <名称> --action '<JSON>'

# 结束录制
python scripts/recorder.py --stop --name <名称>

# 查看录制状态
python scripts/recorder.py --status --name <名称>

# 列出所有录制
python scripts/recorder.py --list
```

### generator.py

```bash
# 生成脚本
python scripts/generator.py --recording <名称>

# 指定输出目录
python scripts/generator.py --recording <名称> --output <目录>

# 强制覆盖
python scripts/generator.py --recording <名称> --force
```

### runner.py

```bash
# 执行录制
python scripts/runner.py --recording <名称>

# 传递参数
python scripts/runner.py --recording <名称> --param key=value

# 多个参数
python scripts/runner.py --recording <名称> --param username=user1 --param password=pass1

# 显示浏览器窗口
python scripts/runner.py --recording <名称> --headed

# 查看帮助
python scripts/runner.py --help
```

---

## 参数化说明

### 占位符格式

使用 `{参数名}` 作为占位符：

```json
{"action": "type", "params": {"text": "{username}"}}
```

### 参数定义

在metadata.json中定义每个参数：

| 字段 | 说明 |
|------|------|
| `name` | 参数名称 |
| `type` | 参数类型：string, number, boolean |
| `required` | 是否必需 |
| `description` | 参数说明 |
| `cli_flag` | CLI长选项（如--username） |
| `cli_short` | CLI短选项（如-u） |
| `default` | 默认值 |
| `sensitive` | 是否敏感（密码等），不在日志中显示 |

---

## 生成的Shell脚本示例

```bash
#!/bin/bash
# Generated by browser_cli skill
# Description: 登录GitHub

set -e

# Default values
USERNAME=""
PASSWORD=""
HEADLESS=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --username|-u)
            USERNAME="$2"
            shift 2
            ;;
        --password|-p)
            PASSWORD="$2"
            shift 2
            ;;
        --headed)
            HEADLESS=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 --username USER --password PASS [--headed]"
            echo "  --username, -u  GitHub用户名 (必需)"
            echo "  --password, -p  GitHub密码 (必需)"
            echo "  --headed        显示浏览器窗口"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$USERNAME" ]]; then
    echo "Error: --username is required"
    exit 1
fi
if [[ -z "$PASSWORD" ]]; then
    echo "Error: --password is required"
    exit 1
fi

# Execute via runner
SCRIPT_DIR="$(dirname "$0")"
python "$SCRIPT_DIR/runner.py" \
    --recording login_github \
    --param username="$USERNAME" \
    --param password="$PASSWORD" \
    ${HEADLESS:+--headless}
```

---

## 注意事项

1. **元素定位稳定性**：页面结构变化可能导致脚本失效，建议使用稳定的selector
2. **敏感信息**：密码等敏感参数标记为sensitive，不在日志中显示
3. **执行环境**：脚本需要在CoPaw环境中执行，依赖browser_use工具
4. **页面等待**：复杂页面建议添加wait_for action确保元素加载完成