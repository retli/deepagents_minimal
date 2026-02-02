# DeepAgents 记忆系统技术文档

> 本文档详细说明 `deepagents_minimal` 项目中短期记忆和长期记忆的实现原理，以及虚拟路径与真实文件系统路径转换的技术细节。

---

## 目录

1. [概述](#概述)
2. [短期记忆 (Short-Term Memory)](#短期记忆-short-term-memory)
3. [长期记忆 (Long-Term Memory)](#长期记忆-long-term-memory)
4. [虚拟路径系统](#虚拟路径系统)
5. [关键配置说明](#关键配置说明)
6. [数据流图](#数据流图)
7. [记忆判断机制](#记忆判断机制)

---

## 概述

DeepAgents 框架提供了两种记忆机制：

| 类型 | 存储位置 | 生命周期 | 实现类 |
|------|----------|----------|--------|
| 短期记忆 | 内存 (LangGraph State) | 单次对话 / 单个 Thread | `StateBackend` |
| 长期记忆 | 本地文件系统 | 持久化，跨重启 | `FilesystemBackend` |

---

## 短期记忆 (Short-Term Memory)

### 实现原理

短期记忆由 `StateBackend` 实现，它将数据存储在 LangGraph 的 Agent State 中。

```python
# main.py 中的配置
def create_backend(rt):
    return CompositeBackend(
        default=StateBackend(rt),  # <- 短期记忆的默认后端
        routes={...}
    )
```

### 特点

- **存储介质**：内存中的 Python 字典 (`runtime.state["files"]`)
- **生命周期**：与 `thread_id` 绑定。同一 `thread_id` 内的多轮对话共享状态
- **重启行为**：服务重启后，所有短期记忆**丢失**
- **用途**：临时工作文件、对话上下文中的中间结果

### 代码路径

```
Agent 请求读/写 /temp/notes.txt (不匹配任何路由前缀)
    ↓
CompositeBackend._get_backend_and_key("/temp/notes.txt")
    ↓
返回 (StateBackend, "/temp/notes.txt")  # 使用默认后端
    ↓
StateBackend.write/read/edit 操作内存中的 state["files"]
```

---

## 长期记忆 (Long-Term Memory)

### 实现原理

长期记忆由 `FilesystemBackend` 实现，它将数据存储在本地文件系统中。

```python
# main.py 中的配置
routes = {
    "/memories/": FilesystemBackend(
        root_dir="./memories",
        virtual_mode=True  # 关键参数
    )
}
```

### 特点

- **存储介质**：本地磁盘文件 (`./memories/AGENTS.md`)
- **生命周期**：永久持久化，跨对话、跨重启
- **用途**：用户偏好、项目信息、重要事实

### 工作流程

1. **启动时加载**：`MemoryMiddleware` 在 Agent 启动时读取 `/memories/AGENTS.md` 的内容，注入到系统提示词中
2. **运行时更新**：Agent 通过调用 `edit_file` 工具修改虚拟路径 `/memories/AGENTS.md`
3. **持久化**：`FilesystemBackend` 将修改同步到本地文件 `./memories/AGENTS.md`

---

## 虚拟路径系统

### 核心概念

Agent 操作的是**虚拟路径**（如 `/memories/AGENTS.md`），而非真实的文件系统路径。这种设计提供了：

- **安全隔离**：Agent 无法访问虚拟路径之外的文件
- **路径统一**：无论部署在哪台机器，Agent 看到的路径始终一致
- **灵活映射**：可以将不同虚拟路径映射到不同存储后端

### 路径转换机制

#### 1. CompositeBackend 路由

```python
CompositeBackend(
    default=StateBackend(rt),      # 默认：内存
    routes={
        "/memories/": FilesystemBackend(root_dir="./memories", virtual_mode=True),
        "/skills/":   FilesystemBackend(root_dir="./skills",   virtual_mode=True),
    }
)
```

**路由规则**：
- 路径以 `/memories/` 开头 → 使用 memories 的 FilesystemBackend
- 路径以 `/skills/` 开头 → 使用 skills 的 FilesystemBackend
- 其他路径 → 使用默认的 StateBackend

#### 2. 路径剥离 (_get_backend_and_key)

当 Agent 请求操作 `/memories/AGENTS.md` 时：

```python
# CompositeBackend._get_backend_and_key("/memories/AGENTS.md")
prefix = "/memories/"
stripped_key = "/AGENTS.md"  # 剥离前缀，保留前导斜杠
return (memories_backend, "/AGENTS.md")
```

#### 3. FilesystemBackend 路径解析

在 `virtual_mode=True` 模式下，`FilesystemBackend` 将输入路径视为**相对于 root_dir 的路径**：

```python
# FilesystemBackend._resolve_path("/AGENTS.md")
# root_dir = "./memories"

# 步骤 1: 去除前导斜杠
relative_path = "AGENTS.md"

# 步骤 2: 与 root_dir 拼接
full_path = Path("./memories") / "AGENTS.md"

# 步骤 3: 解析为绝对路径
resolved = "/Users/***/Desktop/deepagents_minimal/memories/AGENTS.md"

# 步骤 4: 安全检查 - 确保路径在 root_dir 内
assert resolved.startswith(root_dir.resolve())  # 防止路径遍历攻击
```

### virtual_mode 参数详解

| 参数值 | 行为 | 安全性 |
|--------|------|--------|
| `False` (默认) | 输入路径被视为绝对路径，`root_dir` 仅作为默认工作目录 | ⚠️ 不安全，可能访问任意文件 |
| `True` | 输入路径被强制视为相对于 `root_dir`，禁止 `..` 和绝对路径 | ✅ 安全，沙箱隔离 |

**关键代码**（来自 `deepagents/backends/filesystem.py`）：

```python
def _resolve_path(self, path: str) -> Path:
    if self.virtual_mode:
        # 强制将路径视为相对路径
        path = path.lstrip("/")
        full = self.cwd / path
        
        # 安全检查：确保解析后的路径仍在 root_dir 内
        try:
            full.resolve().relative_to(self.cwd.resolve())
        except ValueError:
            raise ValueError(f"Path {full} is outside root directory")
        
        return full.resolve()
    else:
        # 非虚拟模式，直接使用绝对路径
        return Path(path)
```

---

## 关键配置说明

### config.json

```json
{
  "memory_files": ["/memories/AGENTS.md"]
}
```

- `memory_files`：指定需要加载到 Agent 上下文中的记忆文件列表
- 路径必须使用**虚拟路径**格式（以 `/` 开头）

### main.py 中的后端配置

```python
def create_backend(rt):
    routes = {
        "/memories/": FilesystemBackend(
            root_dir=memories_dir,      # 真实目录：./memories
            virtual_mode=True           # 必须启用！
        )
    }
    routes.update(skills_route)
    return CompositeBackend(
        default=StateBackend(rt),
        routes=routes,
    )
```

---

## 数据流图

### 读取记忆流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent 启动                                │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  MemoryMiddleware.before_agent()                                │
│  读取 memory_files: ["/memories/AGENTS.md"]                      │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  CompositeBackend.download_files(["/memories/AGENTS.md"])       │
│  → 匹配路由 "/memories/" → FilesystemBackend                     │
│  → 剥离前缀 → "/AGENTS.md"                                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  FilesystemBackend.download_files(["/AGENTS.md"])               │
│  → virtual_mode=True                                            │
│  → 解析路径: ./memories + AGENTS.md                              │
│  → 读取文件: /Users/.../memories/AGENTS.md                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  MemoryMiddleware 将内容注入 System Prompt                       │
│  Agent 现在知道记忆文件中的所有信息                                │
└─────────────────────────────────────────────────────────────────┘
```

### 写入记忆流程

```
┌─────────────────────────────────────────────────────────────────┐
│  用户: "记住项目代号是 Project Omega"                             │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Agent 决策: 需要调用 edit_file 工具                              │
│  Tool Call: edit_file(                                          │
│      file_path="/memories/AGENTS.md",                           │
│      old_string="...",                                          │
│      new_string="...\n- Project Omega 是项目代号"               │
│  )                                                              │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  CompositeBackend.edit("/memories/AGENTS.md", ...)              │
│  → 匹配路由 "/memories/" → FilesystemBackend                     │
│  → 剥离前缀 → "/AGENTS.md"                                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  FilesystemBackend.edit("/AGENTS.md", ...)                      │
│  → virtual_mode=True                                            │
│  → 解析路径: ./memories/AGENTS.md                                │
│  → 执行字符串替换                                                 │
│  → 写入文件 (Python open() + write())                            │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  本地文件 ./memories/AGENTS.md 已更新                             │
│  下次 Agent 启动时，新内容将被加载                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 记忆判断机制

### 核心原理

LLM 如何判断"该记忆什么、不该记忆什么"？

**答案：完全由 LLM 自己判断**，依据是 `MemoryMiddleware` 注入到系统提示词中的 `<memory_guidelines>` 指导原则。

这不是规则引擎或代码逻辑判断的，而是通过**提示词工程 (Prompt Engineering)** 让 LLM 自己做出判断。

### 系统提示词注入

当 Agent 启动时，`MemoryMiddleware` 会将以下指导原则注入到系统提示词中：

```xml
<agent_memory>
{加载的记忆文件内容}
</agent_memory>

<memory_guidelines>
    The above <agent_memory> was loaded in from files in your filesystem. 
    As you learn from your interactions with the user, you can save new 
    knowledge by calling the `edit_file` tool.
    
    **Learning from feedback:**
    - One of your MAIN PRIORITIES is to learn from your interactions...
    - When you need to remember something, updating memory must be your 
      FIRST, IMMEDIATE action - before responding to the user...
    
    **When to update memories / When to NOT update memories:**
    ...
</memory_guidelines>
```

### 应该记忆的情况 ✅

| 场景 | 示例 |
|------|------|
| 用户显式要求记住 | "记住我的邮箱"、"保存这个偏好" |
| 角色/行为定义 | "你是一个网络研究员"、"总是做 X" |
| 工作反馈与纠正 | 用户指出错误并说明如何改进 |
| 工具所需信息 | Slack 频道 ID、邮箱地址、用户名 |
| 未来有用的上下文 | 如何使用工具、特定情况下应采取的行动 |
| 发现的模式/偏好 | 编码风格、约定、工作流程 |
| 隐式偏好暴露 | 用户说"用 JavaScript 重写"→ 记住用户偏好 JS |

### 不应该记忆的情况 ❌

| 场景 | 示例 |
|------|------|
| 临时/短暂信息 | "我现在在路上"、"我在用手机" |
| 一次性任务请求 | "帮我找个菜谱"、"25×4 等于多少？" |
| 简单问题 | "今天星期几？"、"能解释一下 X 吗？" |
| 寒暄/确认 | "好的！"、"你好"、"谢谢" |
| 过时/无关信息 | 已经不再相关的历史信息 |
| **敏感信息** | API Key、密码、令牌（**绝对禁止存储**）|

### 记忆更新的优先级

框架对 LLM 的指导是：

> **"When you need to remember something, updating memory must be your FIRST, IMMEDIATE action - before responding to the user, before calling other tools, before doing anything else."**

也就是说，LLM 被指示在**回复用户之前**就先更新记忆，确保重要信息不会因为后续操作失败而丢失。

### 示例场景

**示例 1：记住显式提供的信息**
```
用户: 能连接我的 Google 账号吗？
Agent: 好的，请问你的 Google 邮箱是什么？
用户: john@example.com
Agent: [内部: 先更新记忆] → edit_file(...) 记录用户邮箱
Agent: 已记录，正在连接你的 Google 账号...
```

**示例 2：记住隐式偏好**
```
用户: 帮我写一个 LangChain 的 DeepAgent 示例
Agent: 好的，这是 Python 示例... <代码>
用户: 能改成 JavaScript 吗？
Agent: [内部: 用户偏好 JS] → edit_file(...) 记录用户偏好 JavaScript
Agent: 这是 JavaScript 版本... <代码>
```

**示例 3：不记忆临时信息**
```
用户: 我今晚要打篮球，会离线几小时
Agent: 好的，我帮你在日历上添加一个事项
Agent: [内部: 这是临时信息，不需要记忆]
```

### 自定义记忆策略

如果你想调整 LLM 的记忆判断策略，有以下方式：

1. **修改 `AGENTS.md`**：在记忆文件开头添加自定义指导
   ```markdown
   # AGENTS MEMORY
   
   ## 记忆规则
   - 始终记住用户提到的项目名称
   - 不要记住任何与工作无关的闲聊内容
   
   ## 已记录的信息
   ...
   ```

2. **自定义 `react_prompt`**：在 `config.json` 中覆盖默认的 ReAct 提示词

3. **扩展 MemoryMiddleware**：继承并重写 `MEMORY_SYSTEM_PROMPT` 常量

---

## 常见问题

### Q: 为什么必须设置 `virtual_mode=True`？

不设置时，`FilesystemBackend` 会将 `/AGENTS.md` 解释为系统根目录下的绝对路径，导致：
1. 权限错误（无法写入 `/AGENTS.md`）
2. 或更糟的安全问题（Agent 可能访问敏感系统文件）

### Q: Agent 如何知道要更新哪个文件？

`MemoryMiddleware` 在加载记忆时会注入一段系统提示词，告诉 Agent：
- 记忆文件的路径是 `/memories/AGENTS.md`
- 需要记住重要信息时，应使用 `edit_file` 工具更新该文件

### Q: 如何添加更多记忆文件？

在 `config.json` 中扩展 `memory_files` 数组：

```json
{
  "memory_files": [
    "/memories/AGENTS.md",
    "/memories/user_preferences.md",
    "/memories/project_notes.md"
  ]
}
```

---

## 相关源码参考

| 文件 | 路径 | 说明 |
|------|------|------|
| CompositeBackend | `deepagents/backends/composite.py` | 路由分发逻辑 |
| FilesystemBackend | `deepagents/backends/filesystem.py` | 文件系统操作 + 路径解析 |
| StateBackend | `deepagents/backends/state.py` | 内存状态存储 |
| MemoryMiddleware | `deepagents/middleware/memory.py` | 记忆加载与注入 |

---

*文档生成时间: 2026-02-02*
