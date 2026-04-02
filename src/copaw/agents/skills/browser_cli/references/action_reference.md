# browser_use 动作参考

本文档列出所有browser_use工具支持的动作及其参数。

---

## 浏览器管理动作

### start - 启动浏览器

启动Playwright浏览器实例。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `headed` | boolean | false | 是否显示浏览器窗口 |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "start", "headed": false}
{"action": "start", "headed": true}
```

---

### stop - 关闭浏览器

关闭浏览器实例及其所有页面。

**参数：** 无

**示例：**
```json
{"action": "stop"}
```

---

## 页面导航动作

### open / navigate - 打开URL

打开指定的URL。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | string | 必填 | 要打开的URL |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "open", "url": "https://example.com"}
{"action": "navigate", "url": "https://github.com/login"}
```

---

### navigate_back - 返回上一页

返回上一个页面。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "navigate_back"}
```

---

## 元素交互动作

### snapshot - 获取页面快照

获取页面的可访问性快照，生成元素引用(refs)。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page_id` | string | "default" | 页面标识 |
| `filename` | string | null | 保存快照的文件路径 |

**结果：** 返回refs映射，用于后续click/type等操作。

**示例：**
```json
{"action": "snapshot"}
{"action": "snapshot", "filename": "page_snapshot.txt"}
```

---

### click - 点击元素

点击页面元素。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ref` | string | - | snapshot中的元素引用(e1, e2...) |
| `selector` | string | - | CSS选择器 |
| `page_id` | string | "default" | 页面标识 |

**注意：** ref和selector至少提供一个。

**示例：**
```json
{"action": "click", "ref": "e3"}
{"action": "click", "selector": "button.submit"}
```

---

### type - 输入文本

在输入框中输入文本。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ref` | string | - | snapshot中的元素引用 |
| `selector` | string | - | CSS选择器 |
| `text` | string | 必填 | 要输入的文本 |
| `clear_first` | boolean | false | 是否先清空输入框 |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "type", "ref": "e1", "text": "{username}"}
{"action": "type", "selector": "input[name='password']", "text": "{password}", "clear_first": true}
```

---

### fill_form - 填充表单

一次性填充多个表单字段。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fields` | object | 必填 | 字段映射 {ref/selector: value} |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "fill_form", "fields": {"e1": "username", "e2": "password"}}
```

---

### hover - 鼠标悬停

悬停在元素上。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ref` | string | - | 元素引用 |
| `selector` | string | - | CSS选择器 |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "hover", "ref": "e5"}
```

---

### drag - 拖拽元素

拖拽元素到目标位置。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `source_ref` | string | - | 源元素引用 |
| `target_ref` | string | - | 目标元素引用 |
| `source_selector` | string | - | 源CSS选择器 |
| `target_selector` | string | - | 目标CSS选择器 |

**示例：**
```json
{"action": "drag", "source_ref": "e1", "target_ref": "e2"}
```

---

### select_option - 选择下拉选项

选择下拉列表中的选项。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ref` | string | - | 元素引用 |
| `selector` | string | - | CSS选择器 |
| `value` | string | 必填 | 选项值 |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "select_option", "ref": "e4", "value": "option1"}
```

---

### press_key - 按键

发送键盘按键。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `key` | string | 必填 | 按键名称(Enter, Escape, Tab等) |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "press_key", "key": "Enter"}
{"action": "press_key", "key": "Escape"}
```

---

## 高级动作

### eval / evaluate - 执行JavaScript

在页面中执行JavaScript代码。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `code` | string | 必填 | JavaScript代码 |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "eval", "code": "document.querySelector('.title').textContent"}
{"action": "evaluate", "code": "window.scrollTo(0, document.body.scrollHeight)"}
```

---

### run_code - 执行页面JS

在页面上下文中执行更复杂的JavaScript。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `code` | string | 必填 | JavaScript代码块 |
| `page_id` | string | "default" | 页面标识 |

---

### wait_for - 等待条件

等待特定条件满足。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `selector` | string | - | 等待元素出现 |
| `timeout` | number | 30000 | 超时时间(ms) |
| `state` | string | "visible" | 状态(visible, hidden, attached) |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "wait_for", "selector": ".result", "timeout": 5000}
```

---

## 文件和截图动作

### screenshot - 截图

截取页面截图。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `filename` | string | 必填 | 保存文件路径 |
| `full_page` | boolean | false | 是否截取完整页面 |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "screenshot", "filename": "page.png"}
{"action": "screenshot", "filename": "full.png", "full_page": true}
```

---

### pdf - 导出PDF

将页面导出为PDF。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `filename` | string | 必填 | 保存文件路径 |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "pdf", "filename": "document.pdf"}
```

---

### file_upload - 文件上传

上传文件到input[type=file]元素。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ref` | string | - | 元素引用 |
| `selector` | string | - | CSS选择器 |
| `files` | array | 必填 | 文件路径列表 |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "file_upload", "ref": "e6", "files": ["~/Downloads/file.pdf"]}
```

---

## 对话框和弹窗处理

### handle_dialog - 处理对话框

处理alert/confirm/prompt对话框。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `accept` | boolean | true | 是否接受对话框 |
| `text` | string | - | prompt对话框的输入文本 |
| `page_id` | string | "default" | 页面标识 |

**示例：**
```json
{"action": "handle_dialog", "accept": true}
{"action": "handle_dialog", "accept": false}
```

---

## 标签页管理

### tabs - 标签页操作

管理多个标签页。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `operation` | string | 必填 | 操作类型(list, switch, close, new) |
| `page_id` | string | - | 要切换/关闭的页面ID |

**示例：**
```json
{"action": "tabs", "operation": "list"}
{"action": "tabs", "operation": "switch", "page_id": "tab2"}
{"action": "tabs", "operation": "close", "page_id": "tab1"}
```

---

### close - 关闭页面

关闭指定页面。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page_id` | string | "default" | 要关闭的页面ID |

**示例：**
```json
{"action": "close", "page_id": "tab1"}
```

---

## 调试和信息动作

### console_messages - 获取控制台日志

获取页面的控制台输出。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page_id` | string | "default" | 页面标识 |
| `filename` | string | - | 保存日志的文件路径 |

**示例：**
```json
{"action": "console_messages"}
```

---

### network_requests - 获取网络请求

获取页面的网络请求记录。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page_id` | string | "default" | 页面标识 |
| `filename` | string | - | 保存请求的文件路径 |

**示例：**
```json
{"action": "network_requests"}
```

---

### resize - 调整窗口大小

调整浏览器窗口大小。

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `width` | number | 1280 | 窗口宽度 |
| `height` | number | 720 | 窗口高度 |

**示例：**
```json
{"action": "resize", "width": 1920, "height": 1080}
```

---

### install - 安装Playwright

安装Playwright浏览器。

**参数：** 无

**示例：**
```json
{"action": "install"}
```