"""MCP Tools loader - 简化版本，直接使用 langchain-mcp-adapters"""

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
          "server_name": "http://localhost:3000/sse",
          "another_server": "http://localhost:3001/sse"
        }
      }
    }
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
    
    # 方式1: 从 config.mcp.servers 读取 (简化格式: name -> url)
    servers_config = mcp_config.get("servers")
    if isinstance(servers_config, dict):
        for name, url in servers_config.items():
            if isinstance(url, str) and url:
                servers[name] = {
                    "url": url,
                    "transport": "sse",
                }
            elif isinstance(url, dict):
                # 也支持完整格式: name -> {url, transport, ...}
                servers[name] = {
                    "url": url.get("url", ""),
                    "transport": url.get("transport", "sse"),
                }
    
    # 方式2: 从环境变量 DEEPAGENTS_MCP_SERVERS 读取 (JSON 格式)
    env_servers = os.getenv("DEEPAGENTS_MCP_SERVERS")
    if env_servers:
        try:
            parsed = json.loads(env_servers)
            if isinstance(parsed, dict):
                for name, url in parsed.items():
                    if isinstance(url, str) and url:
                        servers[name] = {"url": url, "transport": "sse"}
        except Exception:
            pass

    if not servers:
        return []

    print(f"🔌 正在连接 MCP servers: {list(servers.keys())}")
    
    # 使用 MultiServerMCPClient 连接所有 server
    tools: List[BaseTool] = []
    
    try:
        # MultiServerMCPClient 需要特定格式的配置
        mcp_servers_config = {}
        for name, cfg in servers.items():
            mcp_servers_config[name] = {
                "url": cfg["url"],
                "transport": cfg.get("transport", "sse"),
            }
        
        # 同步加载 tools
        tools = asyncio.run(_load_tools_async(mcp_servers_config))
        print(f"✅ 已加载 {len(tools)} 个 MCP tools")
        
    except Exception as e:
        print(f"❌ MCP tools 加载失败: {e}")
        return []

    return tools


async def _load_tools_async(servers_config: Dict[str, Dict[str, Any]]) -> List[BaseTool]:
    """异步加载 MCP tools"""
    async with MultiServerMCPClient(servers_config) as client:
        tools = client.get_tools()
        return tools


def _test_mcp():
    """测试 MCP 连接"""
    config_path = Path("./config.json")
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        config = {}
    
    tools = load_mcp_tools(config)
    print(f"\n已加载的 tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:50]}..." if len(tool.description) > 50 else f"  - {tool.name}: {tool.description}")


if __name__ == "__main__":
    _test_mcp()
