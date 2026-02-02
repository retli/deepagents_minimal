# deepagents_minimal 代码检查与分析

## 1) 当前检查发现的问题

基于静态检查结果，当前有以下依赖未解析（通常是因为尚未安装依赖或环境未激活）：

- [deepagents_minimal/main.py](deepagents_minimal/main.py#L6): 无法解析导入 `fastapi`
- [deepagents_minimal/main.py](deepagents_minimal/main.py#L7): 无法解析导入 `pydantic`
- [deepagents_minimal/main.py](deepagents_minimal/main.py#L8): 无法解析导入 `langchain.chat_models`
- [deepagents_minimal/main.py](deepagents_minimal/main.py#L9): 无法解析导入 `deepagents`
- [deepagents_minimal/main.py](deepagents_minimal/main.py#L10): 无法解析导入 `deepagents.backends`
- [deepagents_minimal/main.py](deepagents_minimal/main.py#L11): 无法解析导入 `langgraph.store.memory`
- [deepagents_minimal/mcp_tools.py](deepagents_minimal/mcp_tools.py#L7): 无法解析导入 `pydantic`
- [deepagents_minimal/mcp_tools.py](deepagents_minimal/mcp_tools.py#L8): 无法解析导入 `langchain_core.tools`

> 说明：这些问题通常是因为当前 Python 环境没有安装依赖或未切到正确的虚拟环境。依赖清单在 [deepagents_minimal/requirements.txt](deepagents_minimal/requirements.txt)。

## 2) 当前已实现功能

1. **最小 Deep Agents Chat 服务**
   - `POST /chat` 与 `GET /health`。
   - 每次请求创建 Deep Agent 并执行 `invoke` 返回结果。
   - 入口代码见 [deepagents_minimal/main.py](deepagents_minimal/main.py)。

2. **Skills 支持**
   - 默认加载 `./skills` 目录（已从原项目复制）。
   - 依赖 Deep Agents 的技能机制进行按需加载。
   - 相关路径设置见 [deepagents_minimal/main.py](deepagents_minimal/main.py#L33-L36)。

3. **MCP 工具调用**
   - 支持从 config.json 或 `.vscode/mcp.json` 加载 MCP 服务。
   - 自动拉取工具并转换为 `StructuredTool` 注入 Agent。
   - 逻辑见 [deepagents_minimal/mcp_tools.py](deepagents_minimal/mcp_tools.py)。

4. **长短期记忆框架**
   - 使用 `CompositeBackend`：
     - 短期记忆：StateBackend
     - 长期记忆：`/memories/` 前缀走 StoreBackend
   - 当前 store 为 `InMemoryStore`（进程内）。
   - 实现见 [deepagents_minimal/main.py](deepagents_minimal/main.py#L38-L46)。

5. **ReAct 风格系统提示**
   - 通过系统提示强制 ReAct 风格工具调用行为。
   - 可用 `DEEPAGENTS_REACT_PROMPT` 或 config.json 覆盖。
   - 实现见 [deepagents_minimal/main.py](deepagents_minimal/main.py#L48-L58)。

6. **集中配置文件**
   - 支持 `config.json`（默认路径）或 `DEEPAGENTS_CONFIG` 指定。
   - 支持注入 `env`（模型 key/base url 等）。
   - 示例见 [deepagents_minimal/config.json](deepagents_minimal/config.json)。

## 3) 可优化与可增加功能

### 优先级 P0（稳定性/基础能力）
- **依赖安装与运行校验**：为 deepagents_minimal 提供独立的 Python 环境或启动脚本。
- **异步 MCP 调用**：目前 `StructuredTool` 内部使用 `asyncio.run`，在异步上下文中可能冲突，可改成异步工具。
- **连接超时与重试策略**：MCP 拉取与调用增加可配置的超时/重试。

### 优先级 P1（能力增强）
- **SSE 流式输出**：新增 `GET /chat/stream` 返回 token/tool 事件。
- **持久化 Store**：替换为 `PostgresStore` 或 `AsyncPostgresStore`，支持长期记忆跨进程。
- **结构化返回**：支持 `response_format` 或强约束输出，便于前端解析。

### 优先级 P2（企业级特性）
- **鉴权与多租户**：加入 token 校验与 profile 隔离。
- **Observability**：接入 LangSmith 追踪、工具调用统计与日志审计。
- **工具白名单/权限**：基于 skill 元数据或配置对工具进行细粒度授权。

## 4) 小结

当前实现已经覆盖了 Deep Agents 的核心能力（skills、工具、记忆框架、ReAct 风格提示），但仍属于最小服务形态。若要用于生产或真实业务场景，建议优先补齐依赖安装、流式输出、MCP 异步调用与持久化记忆。