# 招乎渠道需求文档

## 1. 概述

### 1.1 项目背景

招乎是中国招商银行的内部即时通讯平台。本需求旨在为 CoPaw 智能助手实现招乎渠道集成，使企业员工能够通过招乎平台与 AI 助手进行交互。

### 1.2 目标用户

- 招商银行内部员工（招乎用户）
- 运维管理人员

### 1.3 项目目标

1. 实现招乎平台与 CoPaw 的双向消息通信
2. 支持 AI 智能对话功能
3. 支持定时任务主动推送
4. 实现用户身份映射和会话管理

---

## 2. 功能需求

### 2.1 消息接收（入站回调）

#### 2.1.1 功能描述

接收招乎平台推送的用户消息，调用 AI 模型处理后返回回复。

#### 2.1.2 接口定义

| 项目 | 说明 |
|------|------|
| 端点 | `POST /api/zhaohu/callback` |
| 认证 | 无（内网调用） |
| 超时 | 需在 5 秒内响应 |

#### 2.1.3 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| msgId | string | 是 | 消息唯一标识（用于去重） |
| fromId | string | 是 | 发送者 openId |
| toId | string | 是 | 接收者（机器人）ID |
| groupId | int | 否 | 群组 ID（私聊为空） |
| groupName | string | 否 | 群组名称 |
| msgType | string | 是 | 消息类型（text/image 等） |
| msgContent | string | 是 | 消息内容 |
| timestamp | int | 是 | 时间戳（毫秒） |
| customInfo | object | 否 | 自定义扩展信息 |

#### 2.1.4 处理流程

```
招乎平台 → 回调接口 → 消息去重 → 用户查询 → AI处理 → 推送回复
```

详细步骤：

1. **消息去重**：基于 `msgId` 进行去重，TTL 5分钟
2. **用户查询**：通过 `openId` 查询用户信息获取 `sapId`
3. **会话生成**：生成会话 ID `zhaohu:callback:{sapId}`
4. **上下文设置**：设置用户上下文，加载用户配置
5. **AI 处理**：调用 LLM 生成回复
6. **消息推送**：通过招乎推送接口发送回复

#### 2.1.5 响应格式

```json
{
  "status": "success",
  "message": "processed"
}
```

错误响应：
```json
{
  "status": "error",
  "message": "channel disabled"
}
```

---

### 2.2 消息发送（出站推送）

#### 2.2.1 功能描述

向招乎平台推送消息，用于回复用户或定时任务通知。

#### 2.2.2 推送接口

| 项目 | 说明 |
|------|------|
| URL | 配置项 `push_url` |
| Method | POST |
| Content-Type | application/json |

#### 2.2.3 推送载荷结构

```json
{
  "baseInfo": {
    "sysId": "系统ID",
    "channel": "ZH",
    "robotOpenId": "机器人ID",
    "sendAddrs": [
      {
        "sendAddr": "用户ystId",
        "sendPk": "扩展字段"
      }
    ],
    "net": "DMZ"
  },
  "msgContent": {
    "summary": "消息摘要",
    "pushContent": "推送内容",
    "message": [
      {
        "type": "txt",
        "value": [
          {"text": "消息内容段落1"},
          {"text": "消息内容段落2"}
        ]
      }
    ]
  }
}
```

#### 2.2.4 文本处理规则

- 单条消息限制 200 字符
- 超长文本自动分割为多条
- 保留段落换行格式

---

### 2.3 用户身份映射

#### 2.3.1 功能描述

将招乎平台的 `openId` 映射为业务系统的 `sapId`。

#### 2.3.2 用户查询接口

| 项目 | 说明 |
|------|------|
| URL | 配置项 `user_query_url` |
| Method | POST |
| Content-Type | application/json |

#### 2.3.3 查询请求

```json
{
  "compareType": "EQ",
  "matchFields": ["openId"],
  "keyWord": "用户的openId"
}
```

#### 2.3.4 返回字段

| 字段 | 说明 |
|------|------|
| sapId | 用户 SAP ID（业务主键） |
| ystId | 用户 YST ID（推送目标） |
| userName | 用户名称 |

#### 2.3.5 ID 用途

| ID 类型 | 用途 |
|---------|------|
| openId | 招乎平台用户标识 |
| sapId | 会话管理、用户目录隔离 |
| ystId | 消息推送目标地址 |

---

### 2.4 会话管理

#### 2.4.1 会话 ID 格式

```
zhaohu:callback:{sapId}
```

示例：`zhaohu:callback:12345678`

#### 2.4.2 会话隔离设计

| 会话类型 | ID 格式 | 说明 |
|----------|---------|------|
| 招乎回调 | zhaohu:callback:{sapId} | 用户发消息触发 |
| 招乎推送 | 配置指定 | 定时任务触发 |
| 前端会话 | UUID 格式 | Web 界面 |

#### 2.4.3 上下文保持

- 同一 `sapId` 的会话共享历史记录
- 用户目录隔离（`~/.copaw/{sapId}/`）
- 技能配置独立

---

### 2.5 定时任务集成

#### 2.5.1 功能描述

支持通过定时任务向招乎用户主动推送消息。

#### 2.5.2 任务配置

定时任务 `dispatch` 配置：

```json
{
  "channel": "zhaohu",
  "user_id": "12345678",
  "session_id": "zhaohu:callback:12345678"
}
```

#### 2.5.3 任务类型支持

| 类型 | 说明 |
|------|------|
| text | 直接推送预设文本 |
| agent | 调用 AI 生成内容后推送 |

#### 2.5.4 执行流程

```
定时触发 → 加载任务配置 → 获取招乎渠道 → 构建消息 → 推送到用户
```

---

### 2.6 配置管理

#### 2.6.1 配置项

| 配置项 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| enabled | bool | 否 | false | 是否启用 |
| push_url | string | 是 | - | 消息推送地址 |
| sys_id | string | 是 | - | 系统ID |
| robot_open_id | string | 是 | - | 机器人ID |
| channel | string | 否 | ZH | 渠道代码 |
| net | string | 否 | DMZ | 网络类型 |
| request_timeout | float | 否 | 15.0 | 请求超时（秒） |
| user_query_url | string | 是 | - | 用户查询地址 |
| bot_prefix | string | 否 | "" | 机器人唤醒前缀 |
| dm_policy | string | 否 | open | 私聊策略 |
| group_policy | string | 否 | open | 群聊策略 |
| allow_from | list | 否 | [] | 白名单用户 |
| deny_message | string | 否 | "" | 拒绝消息 |

#### 2.6.2 环境变量支持

配置项可通过环境变量覆盖，优先级：**环境变量 > 配置文件**

| 环境变量 | 对应配置项 |
|----------|------------|
| ZHAOHU_CHANNEL_ENABLED | enabled |
| ZHAOHU_PUSH_URL | push_url |
| ZHAOHU_SYS_ID | sys_id |
| ZHAOHU_ROBOT_OPEN_ID | robot_open_id |
| ZHAOHU_CHANNEL | channel |
| ZHAOHU_NET | net |
| ZHAOHU_REQUEST_TIMEOUT | request_timeout |
| ZHAOHU_USER_QUERY_URL | user_query_url |
| ZHAOHU_BOT_PREFIX | bot_prefix |
| ZHAOHU_DM_POLICY | dm_policy |
| ZHAOHU_GROUP_POLICY | group_policy |
| ZHAOHU_ALLOW_FROM | allow_from |
| ZHAOHU_DENY_MESSAGE | deny_message |

#### 2.6.3 配置文件示例

```json
{
  "channels": {
    "zhaohu": {
      "enabled": true,
      "push_url": "https://zhaofoo.cmbchina.com/api/push",
      "sys_id": "COPAW",
      "robot_open_id": "robot_001",
      "user_query_url": "https://zhaofoo.cmbchina.com/api/user/query",
      "request_timeout": 15.0,
      "dm_policy": "open",
      "group_policy": "restricted"
    }
  }
}
```

---

### 2.7 访问控制

#### 2.7.1 私聊策略（dm_policy）

| 值 | 说明 |
|----|------|
| open | 允许所有用户私聊 |
| restricted | 仅允许白名单用户 |
| closed | 禁止私聊 |

#### 2.7.2 群聊策略（group_policy）

| 值 | 说明 |
|----|------|
| open | 允许所有群聊 |
| restricted | 仅允许白名单群组 |
| closed | 禁止群聊 |

#### 2.7.3 白名单格式

```json
{
  "allow_from": ["user:12345678", "group:1001"]
}
```

---

## 3. 非功能需求

### 3.1 性能要求

| 指标 | 要求 |
|------|------|
| 回调响应时间 | < 5 秒 |
| 推送成功率 | > 99% |
| 并发处理能力 | > 100 QPS |

### 3.2 可靠性要求

| 指标 | 要求 |
|------|------|
| 消息去重 | 5 分钟 TTL |
| 错误重试 | 不重试（避免重复推送） |
| 日志记录 | 完整请求/响应日志 |

### 3.3 安全要求

| 项目 | 说明 |
|------|------|
| 网络隔离 | 内网部署，DMZ 网络访问 |
| 敏感信息 | 环境变量存储密钥 |
| 用户隔离 | 按 sapId 隔离用户数据 |

---

## 4. 接口清单

### 4.1 入站接口

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/zhaohu/callback | POST | 招乎消息回调 |

### 4.2 出站接口

| 接口 | 说明 |
|------|------|
| push_url | 消息推送 |
| user_query_url | 用户查询 |

---

## 5. 错误码

| HTTP 状态码 | 错误信息 | 说明 |
|-------------|----------|------|
| 200 | processed | 处理成功 |
| 200 | duplicate ignored | 重复消息已忽略 |
| 400 | invalid request | 请求参数错误 |
| 503 | channel disabled | 渠道未启用 |
| 503 | channel not available | 渠道不可用 |
| 500 | internal error | 内部错误 |

---

## 6. 部署要求

### 6.1 环境变量

```bash
# 启用招乎渠道
export ZHAOHU_CHANNEL_ENABLED=1

# 推送配置
export ZHAOHU_PUSH_URL=https://zhaofoo.cmbchina.com/api/push
export ZHAOHU_SYS_ID=COPAW
export ZHAOHU_ROBOT_OPEN_ID=robot_001

# 用户查询
export ZHAOHU_USER_QUERY_URL=https://zhaofoo.cmbchina.com/api/user/query

# 网络配置
export ZHAOHU_NET=DMZ
```

### 6.2 依赖服务

- 招乎推送服务
- 招乎用户查询服务
- AI 模型服务

---

## 7. 测试要点

### 7.1 功能测试

- [ ] 私聊消息收发
- [ ] 群聊消息收发
- [ ] 长文本分割
- [ ] 消息去重
- [ ] 用户查询
- [ ] 定时任务推送

### 7.2 异常测试

- [ ] 渠道未启用
- [ ] 推送服务不可用
- [ ] 用户查询失败
- [ ] AI 服务超时

### 7.3 安全测试

- [ ] 白名单校验
- [ ] 用户数据隔离
- [ ] 敏感信息保护

---

## 8. 附录

### 8.1 相关文档

- 招乎开放平台 API 文档
- CoPaw 系统架构文档
- 渠道开发指南

### 8.2 变更记录

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| 1.0 | 2026-03-30 | CoPaw Team | 初始版本 |