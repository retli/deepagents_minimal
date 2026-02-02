import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, create_model
from langchain_core.tools import StructuredTool

from server.models import MCPServiceConfig, ToolSummary
from server.services.mcp_adapter import get_mcp_adapter


DEFAULT_MCP_CONFIG_PATHS = [
    Path(__file__).resolve().parent.parent / ".vscode" / "mcp.json",
]


def _load_mcp_services_from_file(path: Path) -> List[MCPServiceConfig]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    servers = data.get("servers") or {}
    services: List[MCPServiceConfig] = []
    for name, config in servers.items():
        url = config.get("url")
        if not url:
            continue
        services.append(
            MCPServiceConfig(
                name=name,
                sse_url=url,
                enabled=True,
            )
        )
    return services


def _json_schema_to_model(name: str, schema: Optional[Dict[str, Any]]) -> Type[BaseModel]:
    if not schema:
        return create_model(f"{name}Args", __config__=ConfigDict(extra="allow"))

    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])

    fields: Dict[str, Any] = {}
    for prop, spec in properties.items():
        py_type = _json_type_to_py(spec)
        default = ... if prop in required else None
        fields[prop] = (py_type, default)

    if not fields:
        return create_model(f"{name}Args", __config__=ConfigDict(extra="allow"))

    return create_model(f"{name}Args", __config__=ConfigDict(extra="allow"), **fields)


def _json_type_to_py(spec: Any) -> Any:
    if not isinstance(spec, dict):
        return Any

    json_type = spec.get("type")
    if isinstance(json_type, list):
        # choose first non-null type
        json_type = next((t for t in json_type if t != "null"), None)

    if json_type == "string":
        return str
    if json_type == "integer":
        return int
    if json_type == "number":
        return float
    if json_type == "boolean":
        return bool
    if json_type == "object":
        return Dict[str, Any]
    if json_type == "array":
        item_spec = spec.get("items") or {}
        return List[_json_type_to_py(item_spec)]
    return Any


def _tool_from_summary(adapter, summary: ToolSummary, profile_id: str) -> StructuredTool:
    args_schema = _json_schema_to_model(summary.name, summary.input_schema)

    async def _acall(**kwargs):
        return await adapter.call_tool(summary.name, kwargs, profile_id=profile_id)

    def _call(**kwargs):
        return asyncio.run(_acall(**kwargs))

    return StructuredTool.from_function(
        func=_call,
        coroutine=_acall,
        name=summary.name,
        description=summary.desc or f"MCP tool: {summary.name}",
        args_schema=args_schema,
    )


def load_mcp_tools(config: Optional[Dict[str, Any]] = None, profile_id: str = "default") -> List[StructuredTool]:
    config = config or {}
    mcp_config = config.get("mcp") if isinstance(config.get("mcp"), dict) else {}

    disabled = os.getenv("DEEPAGENTS_MCP_DISABLED")
    if disabled is None:
        disabled = str(mcp_config.get("disabled", ""))
    if str(disabled).lower() in {"1", "true", "yes"}:
        return []

    services: List[MCPServiceConfig] = []

    inline = os.getenv("DEEPAGENTS_MCP_SERVICES")
    if inline:
        try:
            for item in json.loads(inline):
                services.append(MCPServiceConfig(**item))
        except Exception:
            pass
    else:
        inline_config = mcp_config.get("services")
        if isinstance(inline_config, list):
            for item in inline_config:
                if isinstance(item, dict):
                    services.append(MCPServiceConfig(**item))

    config_path = os.getenv("DEEPAGENTS_MCP_CONFIG")
    if not config_path:
        config_path = mcp_config.get("config_path")
    if config_path:
        services.extend(_load_mcp_services_from_file(Path(config_path)))
    else:
        for candidate in DEFAULT_MCP_CONFIG_PATHS:
            services.extend(_load_mcp_services_from_file(candidate))

    if not services:
        return []

    adapter = get_mcp_adapter()
    for svc in services:
        adapter.upsert_service(svc, profile_id=profile_id)

    tools: List[StructuredTool] = []
    try:
        summaries = asyncio.run(adapter.list_tools(profile_id=profile_id))
        for summary in summaries:
            tools.append(_tool_from_summary(adapter, summary, profile_id))
    except Exception:
        return []

    return tools
