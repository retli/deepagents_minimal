import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langchain.agents.structured_output import AutoStrategy, ProviderStrategy, ToolStrategy
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend

from mcp_tools import load_mcp_tools


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    thread_id: Optional[str] = Field(default="default")


app = FastAPI(title="deepagents-minimal", version="0.1.0")


def _load_config() -> Dict[str, Any]:
    config_path = os.getenv("DEEPAGENTS_CONFIG", "./config.json")
    path = Path(config_path)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _apply_env_from_config(config: Dict[str, Any]) -> None:
    env = config.get("env")
    if not isinstance(env, dict):
        return

    for key, value in env.items():
        if key and value is not None and key not in os.environ:
            os.environ[str(key)] = str(value)


def build_agent():
    config = _load_config()
    _apply_env_from_config(config)

    model_name = os.getenv("DEEPAGENTS_MODEL", "openai:gpt-5")
    model_name = config.get("model", {}).get("name", model_name)
    model = init_chat_model(model=model_name)

    skills_dir = os.getenv("DEEPAGENTS_SKILLS_DIR", "./skills")
    skills_dir = config.get("skills_dir", skills_dir)
    skills = [skills_dir] if os.path.isdir(skills_dir) else None

    mcp_tools = load_mcp_tools(config=config)

    memories_dir = os.getenv("DEEPAGENTS_MEMORIES_DIR", "./memories")
    memories_dir = config.get("memories_dir", memories_dir)
    os.makedirs(memories_dir, exist_ok=True)
    backend = lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={"/memories/": FilesystemBackend(root_dir=memories_dir)},
    )

    memory_files = config.get("memory_files")
    if not isinstance(memory_files, list):
        memory_files = ["/memories/AGENTS.md"]

    response_format = None
    rf = config.get("response_format") if isinstance(config.get("response_format"), dict) else None
    if rf:
        schema = rf.get("schema")
        mode = (rf.get("mode") or "auto").lower()
        if schema:
            if mode == "provider":
                response_format = ProviderStrategy(schema, strict=rf.get("strict"))
            elif mode == "tool":
                response_format = ToolStrategy(
                    schema,
                    tool_message_content=rf.get("tool_message_content"),
                    handle_errors=rf.get("handle_errors", True),
                )
            else:
                response_format = AutoStrategy(schema)

    default_react_prompt = """Use ReAct-style reasoning for tool use. Internally follow Thought -> Action -> Observation.
Return only the final answer to the user and do not reveal hidden reasoning. If a tool is needed, call it.
""".strip()
    react_prompt = os.getenv("DEEPAGENTS_REACT_PROMPT", default_react_prompt)
    react_prompt = config.get("react_prompt", react_prompt)

    return create_deep_agent(
        model=model,
        skills=skills,
        tools=mcp_tools or None,
        backend=backend,
        memory=memory_files,
        response_format=response_format,
        system_prompt=react_prompt,
    )


@app.post("/chat")
def chat(req: ChatRequest) -> Dict[str, Any]:
    agent = build_agent()
    result = agent.invoke(
        {"messages": [m.model_dump() for m in req.messages]},
        config={"configurable": {"thread_id": req.thread_id}},
    )
    last = result["messages"][-1]
    return {"content": last.content}


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    async def event_stream():
        agent = build_agent()
        prev = ""
        async for state in agent.astream(
            {"messages": [m.model_dump() for m in req.messages]},
            config={"configurable": {"thread_id": req.thread_id}},
        ):
            messages = None
            if isinstance(state, dict):
                messages = state.get("messages")
            if not messages:
                continue

            last = messages[-1]
            content = getattr(last, "content", None) or last.get("content")
            if not content:
                continue

            delta = content[len(prev):] if content.startswith(prev) else content
            prev = content

            payload = json.dumps({"type": "token", "content": delta}, ensure_ascii=False)
            yield f"data: {payload}\n\n"

        final_payload = json.dumps({"type": "final", "content": prev}, ensure_ascii=False)
        yield f"data: {final_payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
def health() -> Dict[str, bool]:
    return {"ok": True}
