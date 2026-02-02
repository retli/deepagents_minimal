# deepagents_minimal 技术架构说明

## 1. 目标与定位

`deepagents_minimal` 是一个“干净、零额外扩展”的 Deep Agents Chat 后端示例，目标是最小化实现：
- 统一的 Chat API（含非流式与 SSE 流式）
- 可复用的 skills 目录
- 可选 MCP 工具调用
- 以 `AGENTS.md` 为载体的长期记忆
- ReAct 风格的工具使用约束
- 可选结构化输出

## 2. 目录结构

```
 deepagents_minimal/
 ├─ main.py              # FastAPI 入口与 Agent 构建
 ├─ mcp_tools.py         # MCP 服务加载与工具封装
 ├─ config.json          # 配置文件（模型/MCP/记忆/响应格式）
 ├─ requirements.txt     # 依赖声明
 ├─ README.md            # 使用说明
 ├─ skills/              # Skills 目录（从 server/skills 复制）
 └─ memories/
    └─ AGENTS.md         # 长期记忆载体（md）
```

## 3. 关键模块与职责

### 3.1 FastAPI 入口
- 文件：[deepagents_minimal/main.py](deepagents_minimal/main.py)
- 提供路由：
  - `POST /chat`：非流式对话
  - `POST /chat/stream`：SSE 流式返回 token/final
  - `GET /health`：健康检查

### 3.2 Agent 构建逻辑
- 构建函数：`build_agent()`
- 主要输入：模型、skills、MCP tools、记忆后端、ReAct prompt、结构化输出
- Deep Agents 核心调用：`create_deep_agent(...)`

### 3.3 MCP 工具接入
- 文件：[deepagents_minimal/mcp_tools.py](deepagents_minimal/mcp_tools.py)
- 支持 MCP 配置来源：
  - `config.json` 的 `mcp.services`
  - `config.json` 的 `mcp.config_path`（支持 `.vscode/mcp.json`）
  - 环境变量 `DEEPAGENTS_MCP_SERVICES`
- MCP 工具封装：动态生成 `StructuredTool`（同步+异步）

### 3.4 Skills 机制
- skills 目录来自 `server/skills`，符合 Deep Agents 的按需加载规范
- `SKILL.md` 使用 YAML frontmatter 描述（name/description）

### 3.5 长短期记忆
- 记忆载体：`memories/AGENTS.md`
- 后端实现：`CompositeBackend`
  - 默认：`StateBackend`（短期，进程内）
  - 路由：`/memories/` → `FilesystemBackend`（长期落盘）
- Deep Agents 会在启动时加载 `memory_files` 中的文件

### 3.6 ReAct 风格约束
- 通过 `react_prompt` 系统提示注入：引导 Tool 使用遵循 ReAct 步骤
- 可通过环境变量或 config.json 覆盖

### 3.7 结构化输出
- `response_format` 支持 `auto/provider/tool`
- 采用 JSON Schema 定义输出结构

## 4. 数据流与执行流程

```
Client -> /chat or /chat/stream
   -> build_agent()
      -> load config.json / env
      -> init_chat_model
      -> load skills
      -> load MCP tools (optional)
      -> build backend (State + Filesystem)
      -> create_deep_agent(...)
   -> agent.invoke / agent.astream
   -> response (JSON or SSE)
```

## 5. 配置体系

- 入口配置：`config.json`（可用 `DEEPAGENTS_CONFIG` 覆盖路径）
- 主要字段：
  - `model.name`：模型标识
  - `skills_dir`：技能目录
  - `memories_dir`：长期记忆目录
  - `memory_files`：记忆文件列表（默认 `/memories/AGENTS.md`）
  - `mcp`：MCP 服务与配置文件路径
  - `response_format`：结构化输出
  - `env`：运行时注入环境变量（API Key/Base URL）

## 6. 当前能力清单

- ✅ 统一 Chat API（同步 / SSE）
- ✅ Skills 复用
- ✅ MCP 工具调用
- ✅ 长期记忆（md）
- ✅ ReAct 风格提示
- ✅ 结构化输出

## 7. 可扩展方向（后续）

- MCP 连接重试与超时优化
- LangSmith tracing 与监控
- 多租户与鉴权（目前未启用）
- 更细粒度工具授权

---

如需进一步输出“运行架构图”或“部署拓扑图”，可继续补充。