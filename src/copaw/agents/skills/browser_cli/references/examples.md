# browser_cli 使用示例

本文档提供browser_cli技能的典型使用场景示例。

---

## 示例1: 录制网站登录流程

### 场景
用户经常需要登录某个网站，希望将登录流程自动化为可重复使用的CLI命令。

### 步骤

#### 1. 开始录制

```bash
python scripts/recorder.py --start --name login_example_site
```

#### 2. Agent执行浏览器操作并记录

Agent会执行以下browser_use操作：

```json
// 操作1: 启动浏览器
{"action": "start", "params": {"headed": false}}

// 操作2: 打开登录页面
{"action": "open", "params": {"url": "https://example.com/login"}}

// 操作3: 获取页面快照
{"action": "snapshot", "params": {}}

// 操作4: 输入用户名
{"action": "type", "params": {"ref": "e1", "text": "{username}", "selector": "input[name='username']"}}

// 操作5: 输入密码
{"action": "type", "params": {"ref": "e2", "text": "{password}", "selector": "input[name='password']"}}

// 操作6: 点击登录按钮
{"action": "click", "params": {"ref": "e3", "selector": "button[type='submit']"}}
```

每次操作后，Agent调用：

```bash
python scripts/recorder.py --record --name login_example_site --action '{"action":"open","params":{"url":"https://example.com/login"}}'
```

#### 3. 结束录制

```bash
python scripts/recorder.py --stop --name login_example_site
```

#### 4. 定义参数

创建 `~/.copaw/browser_recordings/login_example_site/metadata.json`：

```json
{
  "name": "login_example_site",
  "description": "登录example.com网站",
  "parameters": [
    {
      "name": "username",
      "type": "string",
      "required": true,
      "description": "用户名",
      "cli_flag": "--username",
      "cli_short": "-u"
    },
    {
      "name": "password",
      "type": "string",
      "required": true,
      "description": "密码",
      "cli_flag": "--password",
      "cli_short": "-p",
      "sensitive": true
    }
  ],
  "cli_command": "example-login"
}
```

#### 5. 生成脚本

```bash
python scripts/generator.py --recording login_example_site
```

生成文件：
- `~/.copaw/browser_scripts/login_example_site.sh`
- `~/.copaw/browser_scripts/login_example_site.json`

#### 6. 执行脚本

```bash
# 使用Shell脚本
~/.copaw/browser_scripts/login_example_site.sh --username myuser --password mypass

# 显示浏览器窗口
~/.copaw/browser_scripts/login_example_site.sh --username myuser --password mypass --headed

# 或使用runner.py
python scripts/runner.py --recording login_example_site --param username=myuser --param password=mypass
```

---

## 示例2: 录制数据查询流程

### 场景
用户需要定期查询某个网站的数据，希望将查询流程自动化。

### 步骤

#### 1. 开始录制

```bash
python scripts/recorder.py --start --name query_products
```

#### 2. Agent执行并记录操作

```json
// 打开搜索页面
{"action": "open", "params": {"url": "https://shop.example.com/search"}}

// 获取快照
{"action": "snapshot", "params": {}}

// 输入搜索关键词
{"action": "type", "params": {"ref": "e1", "text": "{keyword}", "selector": "input.search-box"}}

// 点击搜索按钮
{"action": "click", "params": {"ref": "e2", "selector": "button.search-btn"}}

// 等待结果加载
{"action": "wait_for", "params": {"selector": ".product-list", "timeout": 5000}}

// 截图保存结果
{"action": "screenshot", "params": {"filename": "search_result.png"}}
```

#### 3. 结束录制并定义参数

```bash
python scripts/recorder.py --stop --name query_products
```

metadata.json:
```json
{
  "name": "query_products",
  "description": "在shop.example.com搜索产品",
  "parameters": [
    {
      "name": "keyword",
      "type": "string",
      "required": true,
      "description": "搜索关键词",
      "cli_flag": "--keyword",
      "cli_short": "-k"
    }
  ],
  "cli_command": "product-search"
}
```

#### 4. 生成并执行

```bash
python scripts/generator.py --recording query_products
~/.copaw/browser_scripts/query_products.sh --keyword "laptop"
```

---

## 示例3: 录制表单填写流程

### 场景
用户需要定期填写相同的表单（如提交日报、申请表等）。

### 录制操作序列

```json
{"action": "start", "params": {"headed": false}}
{"action": "open", "params": {"url": "https://forms.example.com/daily-report"}}
{"action": "snapshot", "params": {}}
{"action": "type", "params": {"ref": "e1", "text": "{date}", "selector": "input[name='date']"}}
{"action": "type", "params": {"ref": "e2", "text": "{content}", "selector": "textarea[name='content']"}}
{"action": "select_option", "params": {"ref": "e3", "value": "{status}", "selector": "select[name='status']"}}
{"action": "click", "params": {"ref": "e4", "selector": "button.submit"}}
```

参数定义：
```json
{
  "parameters": [
    {"name": "date", "type": "string", "required": true, "cli_flag": "--date"},
    {"name": "content", "type": "string", "required": true, "cli_flag": "--content"},
    {"name": "status", "type": "string", "required": false, "default": "completed", "cli_flag": "--status"}
  ]
}
```

执行：
```bash
~/.copaw/browser_scripts/daily_report.sh --date "2026-04-01" --content "完成项目开发" --status "completed"
```

---

## 示例4: 多步骤流程（含等待和条件）

### 场景
复杂的业务流程，需要在每个步骤之间等待页面加载。

### 录制操作序列

```json
// 步骤1: 登录
{"action": "open", "params": {"url": "https://portal.example.com"}}
{"action": "snapshot", "params": {}}
{"action": "type", "params": {"ref": "e1", "text": "{username}"}}
{"action": "type", "params": {"ref": "e2", "text": "{password}"}}
{"action": "click", "params": {"ref": "e3"}}

// 步骤2: 等待登录完成并导航
{"action": "wait_for", "params": {"selector": ".dashboard", "timeout": 10000}}
{"action": "navigate", "params": {"url": "https://portal.example.com/reports"}}

// 步骤3: 生成报告
{"action": "snapshot", "params": {}}
{"action": "click", "params": {"ref": "e5", "selector": "button.generate-report"}}
{"action": "wait_for", "params": {"selector": ".report-ready", "timeout": 30000}}

// 步骤4: 下载报告
{"action": "click", "params": {"ref": "e6", "selector": "a.download-pdf"}}
```

---

## 示例5: 使用runner.py进行高级执行

### 干运行测试

在实际执行前，先测试脚本逻辑：

```bash
python scripts/runner.py --recording login_example_site --param username=test --param password=test --dry-run
```

输出会显示每个步骤的操作，但不实际执行。

### 直接执行

```bash
python scripts/runner.py --recording login_example_site --param username=myuser --param password=mypass --headed
```

---

## 示例6: 管理录制

### 查看所有录制

```bash
python scripts/recorder.py --list
```

输出：
```json
{
  "ok": true,
  "recordings": [
    {"name": "login_example_site", "status": "completed", "total_steps": 6},
    {"name": "query_products", "status": "completed", "total_steps": 5}
  ]
}
```

### 查看录制详情

```bash
python scripts/recorder.py --status --name login_example_site
```

### 删除录制

```bash
python scripts/recorder.py --delete --name old_recording
```

---

## 最佳实践

### 1. 元素定位稳定性

优先使用稳定的CSS选择器：
- `input[name='username']` - 比ref更稳定
- `button[type='submit']` - 不依赖具体文本
- `.class-name` - 语义化选择器

避免使用：
- 动态生成的class（如 `.css-abc123`）
- 依赖位置的选择器（如 `div:nth-child(3)`）

### 2. 添加等待动作

在关键步骤之间添加`wait_for`确保页面加载完成：
```json
{"action": "wait_for", "params": {"selector": ".result", "timeout": 5000}}
```

### 3. 参数命名规范

- 使用有意义的名字：`username`、`keyword`、`date`
- 避免特殊字符：使用`start_date`而非`start-date`
- 标记敏感参数：`password`、`token`设置`sensitive: true`

### 4. 调试技巧

- 先用`--dry-run`测试
- 用`--headed`显示浏览器观察执行过程
- 在关键位置添加`screenshot`保存状态