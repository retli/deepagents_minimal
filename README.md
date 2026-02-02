# deepagents_minimal

最小 Deep Agents Chat 后端（零额外扩展逻辑）。

## 运行

1) 安装依赖

- `pip install -r requirements.txt`

2) 启动

- `uvicorn main:app --host 0.0.0.0 --port 8001`

## 环境变量

- `DEEPAGENTS_MODEL`：模型标识（示例：`openai:gpt-5`）
- `DEEPAGENTS_SKILLS_DIR`：skills 目录（默认 `./skills`，不存在则不加载）
- `DEEPAGENTS_REACT_PROMPT`：ReAct 风格系统提示（默认内置）
- `DEEPAGENTS_CONFIG`：配置文件路径（默认 `./config.json`）
- `DEEPAGENTS_MEMORIES_DIR`：长期记忆目录（默认 `./memories`）

### MCP

- `DEEPAGENTS_MCP_SERVICES`：JSON 列表（数组）形式的 MCP 服务配置
  - 例如：`[{"name":"mcp-1","sse_url":"https://host/sse","enabled":true}]`
- `DEEPAGENTS_MCP_CONFIG`：MCP 配置文件路径（支持 VS Code 的 mcp.json 格式）
- `DEEPAGENTS_MCP_DISABLED`：禁用 MCP 工具加载（`true/1`）

默认会尝试读取上级目录的 `.vscode/mcp.json`。

### 长短期记忆

使用 Filesystem 后端实现：
- 短期记忆：默认写入状态内存（StateBackend）
- 长期记忆：写入 `/memories/` 前缀路径时，会落盘到 `./memories/`

默认会加载 `/memories/AGENTS.md` 作为长期记忆（可在 config.json 中调整）。

## config.json（推荐）

示例：

```
{
  "model": {
    "name": "openai:gpt-5"
  },
  "skills_dir": "./skills",
  "memories_dir": "./memories",
  "memory_files": ["/memories/AGENTS.md"],
  "react_prompt": "Use ReAct-style reasoning...",
  "response_format": {
    "mode": "auto",
    "schema": {
      "type": "object",
      "properties": {
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["answer"]
    }
  },
  "mcp": {
    "disabled": false,
    "config_path": "../.vscode/mcp.json",
    "services": [
      {"name": "mcp-1", "sse_url": "https://host/sse", "enabled": true}
    ]
  },
  "env": {
    "OPENAI_API_KEY": "your-key",
    "OPENAI_BASE_URL": "https://your-gateway/v1"
  }
}
```

说明：
- `env` 会在启动时注入环境变量（若当前进程未设置同名变量）。
- 如需兼容不同厂商模型，请在 `env` 里填写对应 provider 的 key/base_url 环境变量。

## API

- `POST /chat`
  - body: `{ "messages": [{"role": "user", "content": "..."}], "thread_id": "optional" }`
  - resp: `{ "content": "..." }`

- `POST /chat/stream`
  - body: `{ "messages": [{"role": "user", "content": "..."}], "thread_id": "optional" }`
  - SSE event: `data: {"type":"token","content":"..."}`
  - SSE event: `data: {"type":"final","content":"..."}`

- `GET /health`
