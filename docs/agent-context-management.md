# Agent 上下文管理技术方案

> Agent 调用 Skills 执行 MCP Tools 时的上下文控制最佳实践

## 目录

- [概述](#概述)
- [架构总览](#架构总览)
- [Skills 加载机制](#skills-加载机制)
- [MCP Tools 输出处理](#mcp-tools-输出处理)
- [上下文截断策略](#上下文截断策略)
- [大数据处理方案](#大数据处理方案)
- [MCP Server 设计最佳实践](#mcp-server-设计最佳实践)
- [参考资料](#参考资料)

---

## 概述

现代 IDE Agent（如 VS Code Copilot、Cursor、Claude Code）本质上是一个综合型 Agent 系统，其核心挑战之一是 **上下文窗口管理**。当 Agent 通过 Skills 指导调用 MCP Tools 时，如何高效处理工具返回的大量数据，是系统设计的关键。

### 核心问题

```
用户请求 → Agent 读取 Skills → 调用 MCP Tools → 返回 1MB 数据 → ???
                                                              ↑
                                            上下文窗口可能爆炸
```

---

## 架构总览

### Agent 系统的三层结构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LLM (大语言模型)                             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    System Prompt                                │ │
│  │  • 身份设定                                                     │ │
│  │  • Skills 内容（渐进加载）                                       │ │
│  │  • 用户规则                                                     │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Tools 列表                                   │ │
│  │  • IDE 内置工具 (view_file, run_command, etc.)                 │ │
│  │  • MCP Server 提供的工具                                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    对话历史 (Messages)                          │ │
│  │  • 用户消息                                                     │ │
│  │  • 助手回复                                                     │ │
│  │  • 工具调用结果 ← 这里是上下文爆炸的高风险区                     │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Skills vs MCP Tools 的关系

| 组件 | 本质 | 注入位置 | 作用 |
|------|------|----------|------|
| **Skills** | 指导性文档 | System Prompt | 告诉 LLM "如何"使用工具 |
| **MCP Tools** | 可执行函数 | Tools 列表 | 提供 LLM "能力"去执行操作 |

**关键理解**：Skills 不能执行任何操作，只是影响 LLM 如何调用 Tools。

---

## Skills 加载机制

### GitHub Copilot 的三级加载架构

根据 VS Code 官方文档，Copilot 使用 **渐进式加载** 而非全量加载：

```
┌─────────────────────────────────────────────────────────────────────┐
│  Level 1: Skill Discovery (技能发现)                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  • 只读取 SKILL.md 的 YAML frontmatter (name + description)         │
│  • 轻量级，快速判断相关性                                            │
│  • 触发条件：用户 prompt 与 description 语义匹配                     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ 匹配成功
┌─────────────────────────────────────────────────────────────────────┐
│  Level 2: Instructions Loading (指令加载)                            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  • 加载 SKILL.md 完整内容到 context                                  │
│  • 详细的执行指导可用                                                 │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ 需要额外资源
┌─────────────────────────────────────────────────────────────────────┐
│  Level 3: Resource Access (资源访问)                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  • 只在指令明确引用时加载：scripts/, examples/, docs/                │
│  • 按需加载，节省 context window                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Skills 存储位置

| 类型 | 路径 | 说明 |
|------|------|------|
| 项目级 | `.github/skills/` | 仓库特定 |
| 个人级 | `~/.copilot/skills/` | 跨项目共享 |
| Gemini | `~/.gemini/skills/` | Gemini Code Assist |

### SKILL.md 结构示例

```markdown
---
name: thehive-alert-analysis
description: 分析 TheHive 平台上的安全告警，包括告警分类、严重程度评估和响应建议
---

## 使用场景
当用户需要分析安全告警时，使用此 Skill。

## 工作流程
1. 使用 `get_alerts_summary` 获取概览
2. 根据严重程度筛选需要关注的告警
3. 使用 `get_alert_detail` 获取具体信息
4. 生成分析报告

## 注意事项
- 不要一次性获取所有告警，使用分页
- 优先处理 critical 和 high 级别
```

---

## MCP Tools 输出处理

### MCP 传输机制

MCP 支持两种传输方式：

| 传输方式 | 场景 | 输出模式 | 说明 |
|----------|------|----------|------|
| **STDIO** | 本地工具 | 批量返回 | 一次性返回完整 JSON |
| **Streamable HTTP** | 远程工具 | 可流式 | 支持 SSE，需主动实现 |

### 工具返回数据流

```
MCP Server                    Agent 框架                      LLM
     │                              │                           │
     │  tool 执行完成               │                           │
     │  返回完整结果                │                           │
     │─────────────────────────────>│                           │
     │                              │                           │
     │                              │  ⚡ 截断/处理             │
     │                              │  (框架层实现)             │
     │                              │                           │
     │                              │  处理后的结果             │
     │                              │──────────────────────────>│
     │                              │                           │
```

---

## 上下文截断策略

### 各大厂实现对比

#### Anthropic Claude

Claude Code CLI 使用 **动态截断**：

```python
# Claude Code 的截断逻辑（反编译推测）
def truncate_output(output: str) -> str:
    length = len(output)
    
    if length < 10_000:
        return output  # 不截断
    elif 10_000 <= length < 30_000:
        return output[:8_000] + "\n[truncated]"
    elif 30_000 <= length < 50_000:
        return output[:4_000] + "\n[truncated]"
    else:
        return output[:4_000] + "\n[truncated]"
```

**已知问题**：
- JSON 截断导致解析失败
- MCP tool responses 限制约 700 字符显示
- 可能产生 "context low" 错误

**高级方案 - Programmatic Tool Calling**：
- Claude 写 Python 代码编排多个工具调用
- 中间结果保持在代码变量中，不进入主上下文
- 只有最终筛选后的结果返回给 LLM

> 参考：[Anthropic Tool Use Documentation](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)

#### OpenAI GPT

硬截断限制：

| 输出类型 | 截断限制 |
|----------|----------|
| messages/tool outputs | ~32,768 字符 |
| code interpreter | ~20,000 字符 |
| GPT-4o JSON outputs | ~7,800 字符 (16K tokens) |

**推荐的开发者处理方式**：
- 使用 `on_tool_end` hook 预处理
- 条件性截断：保留关键部分
- 工具端预截断

> 参考：[OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)

---

## 大数据处理方案

### 方案 1: MapReduce 摘要

适用于需要处理完整大数据集的场景。

```
1MB 数据 → 分成 N 个 chunks
              ↓
每个 chunk 独立用 LLM 摘要 → N 个小摘要
              ↓
合并所有小摘要 → 最终摘要 → 进入主上下文

额外 LLM 调用：N+1 次
```

**实现参考**：[LangChain MapReduce Summarization](https://python.langchain.com/docs/tutorials/summarization/)

```python
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitter import CharacterTextSplitter

# 分块
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
docs = text_splitter.create_documents([large_text])

# MapReduce 摘要
chain = load_summarize_chain(llm, chain_type="map_reduce")
summary = chain.run(docs)
```

### 方案 2: 外部存储 + 引用

适用于数据需要持久化或多次访问的场景。

```
1MB 数据 → 存储到向量数据库/文件系统
              ↓
返回给 LLM 的只是：
"数据已存储，共 1000 条记录，ID: xxx"
"需要详情时请查询 get_detail(id)"
              ↓
LLM 按需检索具体条目
```

**实现参考**：[LangChain RAG](https://python.langchain.com/docs/tutorials/rag/)

### 方案 3: 多层上下文管理

最全面的方案，结合多种策略。

```
第 1 层：工具输出压缩（源头控制）
    ↓
第 2 层：滑动窗口裁剪旧消息（会话管理）
    ↓
第 3 层：LLM 摘要（最后手段）
```

**实现参考**：[LangChain Memory Management](https://python.langchain.com/docs/how_to/chatbots_memory/)

---

## MCP Server 设计最佳实践

### ❌ 错误示例

```python
@server.tool()
async def get_all_alerts() -> str:
    """获取所有告警"""
    alerts = await api.get_all_alerts()  # 可能有 10000 条
    return json.dumps(alerts)  # 可能 10MB+
```

### ✅ 正确示例

```python
from mcp import Server
import json

server = Server("thehive-mcp")

@server.tool()
async def get_alerts(
    limit: int = 10,
    offset: int = 0,
    severity: str = None,
    fields: list[str] = None
) -> str:
    """获取告警列表（支持分页和过滤）
    
    Args:
        limit: 最多返回条数，默认 10，最大 50
        offset: 偏移量，用于分页
        severity: 过滤条件 - critical/high/medium/low
        fields: 返回字段，默认 ["id", "title", "severity", "date"]
    
    Returns:
        JSON 格式的告警列表，包含分页信息
    """
    limit = min(limit, 50)  # 强制上限
    fields = fields or ["id", "title", "severity", "date"]
    
    alerts = await api.get_alerts(
        limit=limit,
        offset=offset,
        severity=severity
    )
    
    # 只返回需要的字段
    result = [{k: a.get(k) for k in fields} for a in alerts]
    
    return json.dumps({
        "items": result,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": await api.get_total_count(severity=severity),
            "hasMore": len(alerts) == limit
        }
    }, ensure_ascii=False)


@server.tool()
async def get_alert_detail(alert_id: str) -> str:
    """获取单个告警的完整详情
    
    Args:
        alert_id: 告警 ID
    
    Returns:
        JSON 格式的告警详情
    """
    alert = await api.get_alert(alert_id)
    
    # 限制某些大字段
    if len(alert.get("raw_log", "")) > 5000:
        alert["raw_log"] = alert["raw_log"][:5000] + "\n[truncated, use get_alert_raw_log for full content]"
    
    return json.dumps(alert, ensure_ascii=False)


@server.tool()
async def get_alerts_summary() -> str:
    """获取告警统计摘要（推荐首先调用）
    
    Returns:
        JSON 格式的统计摘要，不包含详细数据
    """
    stats = await api.get_stats()
    
    return json.dumps({
        "overview": {
            "total": stats["total"],
            "unresolved": stats["unresolved"],
            "last_24h": stats["last_24h"]
        },
        "by_severity": {
            "critical": stats["critical"],
            "high": stats["high"],
            "medium": stats["medium"],
            "low": stats["low"]
        },
        "top_categories": stats["top_categories"][:5],
        "recommendation": "使用 get_alerts(severity='critical') 查看需要立即处理的告警"
    }, ensure_ascii=False)
```

### 设计原则

| 原则 | 说明 |
|------|------|
| **分页必须** | 所有列表接口必须支持 `limit` 和 `offset` |
| **字段可选** | 允许指定返回字段，减少数据量 |
| **过滤优先** | 在服务端过滤，不返回无关数据 |
| **摘要接口** | 提供统计/摘要接口，让 Agent 先了解全貌 |
| **强制上限** | 即使用户传入大数字，也要有硬上限 |
| **大字段截断** | 超大字段（如 raw_log）主动截断并提示 |

---

## 参考资料

### 官方文档

| 资源 | 链接 |
|------|------|
| Model Context Protocol 规范 | https://modelcontextprotocol.io/ |
| MCP TypeScript SDK | https://github.com/modelcontextprotocol/typescript-sdk |
| MCP Python SDK | https://github.com/modelcontextprotocol/python-sdk |
| Anthropic Tool Use | https://docs.anthropic.com/en/docs/build-with-claude/tool-use |
| OpenAI Function Calling | https://platform.openai.com/docs/guides/function-calling |
| VS Code Copilot Skills | https://code.visualstudio.com/docs/copilot/copilot-extensibility-overview |

### 框架实现

| 框架 | 链接 | 说明 |
|------|------|------|
| LangChain | https://python.langchain.com/ | 提供完整的上下文管理方案 |
| LlamaIndex | https://docs.llamaindex.ai/ | 擅长大文档处理 |
| OpenAI Agents SDK | https://github.com/openai/openai-agents-python | 提供 `on_tool_end` hook |

### 社区讨论

| 主题 | 链接 |
|------|------|
| Claude Code 截断问题 | https://github.com/anthropics/claude-code/issues (搜索 truncation) |
| GPT Function Output 截断 | https://community.openai.com/ (搜索 function output truncated) |

---

## 总结

### 核心要点

1. **Skills 是渐进加载的**
   - 基于 description 语义匹配触发
   - 不会全量加载到上下文

2. **MCP Tools 输出是批量返回的**
   - STDIO 模式下一次性返回完整结果
   - 截断发生在 Agent 框架层，不可控

3. **截断是简单粗暴的**
   - 按字符数截断，会破坏 JSON 结构
   - 各厂商实现不同，但都很简单

4. **责任在 MCP Server 开发者**
   - 必须在工具层就控制输出大小
   - 提供分页、过滤、摘要接口

### 推荐架构

```
用户请求
    ↓
Skills 提供指导（渐进加载）
    ↓
Agent 决定调用工具策略
    ↓
先调用 summary 接口了解全貌
    ↓
按需调用 detail 接口获取具体数据
    ↓
生成分析结果
```

---

*文档版本：1.0*
*最后更新：2026-02-05*
