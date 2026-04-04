# CoPaw 目录结构分析报告

## 分析日期
2026-04-03

## 分析目标
理解 CoPaw 项目的目录结构设计，以及代码设计与实际目录结构的对应关系。

---

## 一、设计 vs 实际对应表

| 设计概念 | 代码定义路径 | 实际目录 | 状态 |
|---------|-------------|---------|------|
| **全局工作目录** (`WORKING_DIR`) | `~/.copaw/` | `/Users/shixiangyi/.copaw/` | ✅ 存在 |
| **租户目录** (`tenant_id="default"`) | `~/.copaw/default/` | `/Users/shixiangyi/.copaw/default/` | ✅ 存在 |
| **全局 Skill Pool** | `~/.copaw/skill_pool/` | `/Users/shixiangyi/.copaw/skill_pool/` | ✅ 存在 |
| **租户 Skill Pool** | `~/.copaw/{tenant}/skill_pool/` | `/Users/shixiangyi/.copaw/default/skill_pool/` | ✅ 存在 |
| **全局 Workspaces** | `~/.copaw/workspaces/` | `/Users/shixiangyi/.copaw/workspaces/` | ✅ 存在 |
| **租户 Workspaces** | `~/.copaw/{tenant}/workspaces/` | `/Users/shixiangyi/.copaw/default/workspaces/` | ✅ 存在 |
| **全局 Secrets** | `~/.copaw/.secret/` | - | ❌ 不存在 |
| **租户 Secrets** | `~/.copaw/{tenant}/secrets/` | `/Users/shixiangyi/.copaw/default/secrets/` | ✅ 存在(空) |
| **租户 Config** | `~/.copaw/{tenant}/config.json` | `/Users/shixiangyi/.copaw/default/config.json` | ✅ 存在 |
| **全局 Config** | `~/.copaw/config.json` | `/Users/shixiangyi/.copaw/config.json` | ✅ 存在 |

---

## 二、关键发现

### 2.1 两套系统并存
实际目录同时存在**全局级别**和**租户级别**的结构：
- `~/.copaw/workspaces/` 和 `~/.copaw/default/workspaces/`
- `~/.copaw/skill_pool/` 和 `~/.copaw/default/skill_pool/`

### 2.2 `default` 租户的特殊性
`/Users/shixiangyi/.copaw/default/` 是实际活跃使用的租户目录，包含完整的功能结构。

### 2.3 缺少全局 .secret 目录
代码设计中 `SECRET_DIR = ~/.copaw/.secret/`，但实际不存在。可能已迁移到租户级 `secrets/` 目录。

---

## 三、实际目录结构详解

### 3.1 全局级 (`~/.copaw/`)
```
~/.copaw/
├── config.json              # 全局配置
├── copaw.log               # 日志文件
├── skill_pool/             # 全局技能池
│   ├── skill.json
│   └── {skill_name}/
│       └── SKILL.md
├── workspaces/             # 全局 workspaces
│   ├── CoPaw_QA_Agent_0.1beta1/
│   └── default/
├── default/                # default 租户（主要使用）
│   └── ...
└── test/                   # test 租户
```

### 3.2 租户级 (`~/.copaw/default/`)
```
~/.copaw/default/
├── config.json              # 租户级配置（channels, agents.profiles, mcp）
├── HEARTBEAT.md            # 心跳任务文件
├── chats.json              # 对话记录
├── skill.json              # 租户级技能清单（当前为空）
├── cold_joke.sh            # 定时任务脚本
├── skill_pool/             # 租户级技能池（主要使用）
│   ├── skill.json          # 技能清单
│   ├── browser_cdp/
│   ├── browser_visible/
│   ├── channel_message/
│   ├── copaw_source_index/
│   ├── cron/
│   ├── dingtalk_channel/
│   ├── docx/
│   ├── file_reader/
│   ├── guidance/
│   ├── himalaya/
│   ├── multi_agent_collaboration/
│   ├── news/
│   ├── pdf/
│   ├── pptx/
│   └── xlsx/
├── workspaces/             # Workspace 集合
│   ├── default/            # 默认 agent workspace
│   └── CoPaw_QA_Agent_0.1beta1/
├── media/                  # 媒体文件
├── memory/                 # 记忆目录（空）
├── secrets/                # 租户秘密（空）
├── sessions/               # 会话数据
├── skills/                 # 技能目录（空）
├── dialog/                 # 对话数据
├── embedding_cache/        # 嵌入缓存
├── file_store/             # 文件存储
└── tool_result/            # 工具结果
```

### 3.3 Workspace 级 (`~/.copaw/default/workspaces/default/`)
```
~/.copaw/default/workspaces/default/
├── AGENTS.md               # Agent 定义
├── BOOTSTRAP.md            # 启动指令
├── SOUL.md                 # Agent 个性定义
├── MEMORY.md               # 记忆配置
├── PROFILE.md              # 配置文件
├── HEARTBEAT.md            # 心跳任务
├── skill.json              # Workspace 技能清单（16134 bytes，活跃使用）
├── chats.json              # 对话记录
├── jobs.json               # Cron 任务
├── skills/                 # 私有技能目录（17个子目录）
├── memory/                 # 记忆存储（空）
├── media/                  # 媒体文件（空）
├── dialog/                 # 对话数据（空）
├── embedding_cache/        # 嵌入缓存（空）
├── file_store/             # 文件存储
└── tool_result/            # 工具结果（空）
```

---

## 四、配置和数据存储位置

### 4.1 配置层级

| 配置类型 | 代码获取函数 | 实际路径 | 用途 |
|---------|------------|---------|------|
| 全局 Config | `get_config_path()` | `~/.copaw/config.json` | 全局默认配置 |
| 租户 Config | `get_tenant_config_path()` | `~/.copaw/default/config.json` | 租户级配置 |
| 租户 Jobs | `get_tenant_jobs_path()` | `~/.copaw/default/jobs.json` | 定时任务 |
| 租户 Chats | `get_tenant_chats_path()` | `~/.copaw/default/chats.json` | 对话记录 |

### 4.2 Skill Pool 层级

| Skill Pool 类型 | 代码获取函数 | 实际路径 |
|----------------|------------|---------|
| 全局 Skill Pool | `get_skill_pool_dir()` | `~/.copaw/skill_pool/` |
| 租户 Skill Pool | `get_skill_pool_dir(working_dir)` | `~/.copaw/default/skill_pool/` |
| Workspace Skills | `get_workspace_skills_dir()` | `~/.copaw/default/workspaces/default/skills/` |

### 4.3 其他目录

| 目录类型 | 代码获取函数 | 实际路径 |
|---------|------------|---------|
| 租户 Memory | `get_tenant_memory_dir()` | `~/.copaw/default/memory/` |
| 租户 Media | `get_tenant_media_dir()` | `~/.copaw/default/media/` |
| 租户 Secrets | `get_tenant_secrets_dir()` | `~/.copaw/default/.secret/` (代码设计) → `secrets/` (实际) |
| 租户 Heartbeat | `get_tenant_heartbeat_path()` | `~/.copaw/default/HEARTBEAT.md` |

---

## 五、关键结论

### 5.1 不是全部放在 workspace 中
配置和数据是**分层存储**的：

1. **租户级配置**（`config.json`）包含 channels、agents.profiles、MCP 等全局配置
2. **Skill Pool** 主要在租户级（`~/.copaw/default/skill_pool/`），包含所有可用技能
3. **Workspace 级**主要存放 Agent 特定的定义文件（AGENTS.md、SOUL.md 等）和私有技能

### 5.2 混合模式
实际目录结构是一个**混合模式**：
- **全局级** (`~/.copaw/`)：保留了一些旧版兼容结构
- **租户级** (`~/.copaw/default/`)：新的多租户结构，是当前活跃使用的主体

### 5.3 default 租户是默认单用户模式
`default` 租户是默认的单用户模式实现，所有数据都隔离在这个目录下，与 CLAUDE.md 中描述的 "Multi-User Concurrent Support" 设计一致。

### 5.4 Skill Pool 使用逻辑
代码中 `get_skill_pool_dir()` 在不传参数时默认使用全局路径 `~/.copaw/skill_pool`，但很多代码会传入 `working_dir` 参数来使用租户级路径。

---

## 六、代码参考

### 6.1 关键函数定义位置

| 函数 | 文件路径 | 行号 |
|-----|---------|------|
| `get_config_path()` | `src/copaw/config/utils.py` | 386 |
| `get_tenant_config_path()` | `src/copaw/config/utils.py` | 659 |
| `get_skill_pool_dir()` | `src/copaw/agents/skills_manager.py` | 117 |
| `get_workspace_skills_dir()` | `src/copaw/agents/skills_manager.py` | 128 |
| `get_tenant_memory_dir()` | `src/copaw/config/utils.py` | 695 |
| `get_tenant_secrets_dir()` | `src/copaw/config/utils.py` | 719 |

### 6.2 目录常量定义

```python
# src/copaw/constant.py
WORKING_DIR = Path("~/.copaw").expanduser().resolve()
SECRET_DIR = Path("~/.copaw.secret").expanduser().resolve()
DEFAULT_MEDIA_DIR = WORKING_DIR / "media"
DEFAULT_LOCAL_PROVIDER_DIR = WORKING_DIR / "local_models"
MEMORY_DIR = WORKING_DIR / "memory"
CUSTOM_CHANNELS_DIR = WORKING_DIR / "custom_channels"
MODELS_DIR = WORKING_DIR / "models"
```

---

## 七、附：多租户路径计算示例

```python
# 获取当前租户的 working_dir
get_tenant_working_dir("default")  # → ~/.copaw/default/

# 获取 config 路径
get_tenant_config_path("default")  # → ~/.copaw/default/config.json

# Skill Pool 路径
get_skill_pool_dir(working_dir=WORKING_DIR / "default")  # → ~/.copaw/default/skill_pool/
```
