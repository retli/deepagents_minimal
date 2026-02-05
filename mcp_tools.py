"""MCP Tools loader - 使用 langchain-mcp-adapters"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool

# 尝试导入 langchain-mcp-adapters
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False
    MultiServerMCPClient = None  # type: ignore


def load_mcp_tools(config: Optional[Dict[str, Any]] = None) -> List[BaseTool]:
    """
    从 config 加载 MCP tools。
    
    config.json 格式:
    {
      "mcp": {
        "disabled": false,
        "servers": {
          "server_name": "http://localhost:3000/mcp",
          "another": {
            "url": "http://localhost:3001/mcp",
            "transport": "http"
          }
        }
      }
    }
    
    transport 支持: "http" (SSE/HTTP), "stdio" (本地进程)
    """
    if not _MCP_AVAILABLE:
        print("⚠️  langchain-mcp-adapters 未安装，跳过 MCP tools 加载")
        print("   安装命令: pip install langchain-mcp-adapters")
        return []

    config = config or {}
    mcp_config = config.get("mcp") if isinstance(config.get("mcp"), dict) else {}

    # 检查是否禁用
    disabled = os.getenv("DEEPAGENTS_MCP_DISABLED")
    if disabled is None:
        disabled = str(mcp_config.get("disabled", ""))
    if str(disabled).lower() in {"1", "true", "yes"}:
        return []

    # 收集所有 server 配置
    servers: Dict[str, Dict[str, Any]] = {}
    
    # 从 config.mcp.servers 读取
    servers_config = mcp_config.get("servers")
    if isinstance(servers_config, dict):
        for name, value in servers_config.items():
            if isinstance(value, str) and value:
                # 简化格式: name -> url
                servers[name] = {
                    "url": value,
                    "transport": "http",  # HTTP/SSE transport
                }
            elif isinstance(value, dict):
                # 完整格式
                if value.get("url"):
                    servers[name] = {
                        "url": value["url"],
                        "transport": value.get("transport", "http"),
                    }
                elif value.get("command"):
                    # stdio 模式
                    servers[name] = {
                        "command": value["command"],
                        "args": value.get("args", []),
                        "transport": "stdio",
                    }
    
    # 从环境变量读取
    env_servers = os.getenv("DEEPAGENTS_MCP_SERVERS")
    if env_servers:
        try:
            parsed = json.loads(env_servers)
            if isinstance(parsed, dict):
                for name, url in parsed.items():
                    if isinstance(url, str) and url:
                        servers[name] = {"url": url, "transport": "http"}
        except Exception:
            pass

    if not servers:
        return []

    print(f"🔌 正在连接 MCP servers: {list(servers.keys())}")
    
    tools: List[BaseTool] = []
    
    try:
        tools = asyncio.run(_load_tools_async(servers))
        if tools:
            print(f"✅ 已加载 {len(tools)} 个 MCP tools")
        else:
            print("⚠️  没有加载到任何 MCP tools")
        
    except ExceptionGroup as eg:
        # Python 3.11+ TaskGroup 异常
        print(f"❌ MCP 连接失败:")
        for exc in eg.exceptions:
            print(f"   - {type(exc).__name__}: {exc}")
        return []
    except Exception as e:
        print(f"❌ MCP tools 加载失败: {type(e).__name__}: {e}")
        return []

    return tools


async def _load_tools_async(servers_config: Dict[str, Dict[str, Any]]) -> List[BaseTool]:
    """异步加载 MCP tools"""
    client = MultiServerMCPClient(servers_config)
    tools = await client.get_tools()
    return tools


def _test_mcp():
    """测试 MCP 连接"""
    print("=" * 50)
    print("🔧 MCP 连接测试")
    print("=" * 50)
    
    config_path = Path("./config.json")
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        mcp_cfg = config.get("mcp", {})
        servers = mcp_cfg.get("servers", {})
        print(f"\n📋 配置的 servers:")
        for name, value in servers.items():
            if isinstance(value, str):
                print(f"   {name}: {value}")
            elif isinstance(value, dict):
                print(f"   {name}: {value.get('url') or value.get('command')}")
    else:
        config = {}
        print("\n⚠️  config.json 不存在")
    
    print()
    tools = load_mcp_tools(config)
    
    if tools:
        print(f"\n📦 已加载的 tools:")
        for tool in tools:
            desc = tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
            print(f"   - {tool.name}: {desc}")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    _test_mcp()
