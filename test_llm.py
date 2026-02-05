# ============ 公司环境：强制全局禁用 SSL 验证（必须在其他导入之前） ============
import os
import ssl

os.environ["PYTHONHTTPSVERIFY"] = "0"
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["SSL_CERT_FILE"] = ""
os.environ["SSL_CERT_DIR"] = ""

try:
    _unverified_context = ssl.create_default_context()
    _unverified_context.check_hostname = False
    _unverified_context.verify_mode = ssl.CERT_NONE
    ssl._create_default_https_context = lambda: _unverified_context
except Exception:
    pass

# ============ 正常导入 ============
import json
import sys
from pathlib import Path

import httpx
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


def load_config():
    """加载配置文件"""
    config_path = os.getenv("DEEPAGENTS_CONFIG", "./config.json")
    path = Path(config_path)
    if not path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return {}
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"❌ 配置文件解析失败: {e}")
        return {}


def apply_env(config):
    """应用环境变量"""
    env = config.get("env")
    if isinstance(env, dict):
        for key, value in env.items():
            if key and value is not None and key not in os.environ:
                os.environ[str(key)] = str(value)


def test_llm():
    """测试 LLM 连接"""
    print("=" * 50)
    print("🔧 LLM 连接测试脚本")
    print("=" * 50)
    
    # 加载配置
    config = load_config()
    apply_env(config)
    
    model_config = config.get("model", {})
    model_name = model_config.get("name", "gpt-5")
    
    # 去掉可能的 openai: 前缀
    if model_name.startswith("openai:"):
        model_name = model_name.split(":", 1)[1]
    
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "")
    
    print(f"\n📋 配置信息:")
    print(f"   模型: {model_name}")
    print(f"   API Base: {base_url or '(默认 OpenAI)'}")
    print(f"   API Key: {'***' + api_key[-4:] if len(api_key) > 4 else '(未设置)'}")
    
    # 准备 headers
    default_headers = {"apikey": api_key} if base_url else {}
    accesscode = model_config.get("accesscode") or model_config.get("authorization") or os.environ.get("ACCESSCODE", "")
    if accesscode:
        default_headers["Authorization"] = accesscode
        print(f"   AccessCode: ***{accesscode[-4:] if len(accesscode) > 4 else '(已设置)'}")
    
    print(f"\n🚀 正在测试连接...")
    
    try:
        # 创建 LLM
        http_client = httpx.Client(verify=False)
        http_async_client = httpx.AsyncClient(verify=False)
        
        llm_kwargs = {
            "model": model_name,
            "api_key": api_key,
            "http_client": http_client,
            "http_async_client": http_async_client,
            "max_retries": 0,
        }
        
        if base_url:
            llm_kwargs["base_url"] = base_url
            llm_kwargs["default_headers"] = default_headers
        
        llm = ChatOpenAI(**llm_kwargs)
        
        # 发送测试消息
        test_message = "请用一句话回复：你好"
        print(f"\n📤 发送测试消息: \"{test_message}\"")
        
        response = llm.invoke([HumanMessage(content=test_message)])
        
        print(f"\n✅ 连接成功!")
        print(f"📥 模型回复: {response.content}")
        print("\n" + "=" * 50)
        return True
        
    except Exception as e:
        print(f"\n❌ 连接失败!")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误信息: {e}")
        print("\n💡 排查建议:")
        print("   1. 检查 OPENAI_API_KEY 是否正确")
        print("   2. 检查 OPENAI_BASE_URL 是否可访问")
        print("   3. 检查模型名称是否正确")
        print("   4. 如需 accesscode，请在 config.json 的 model.accesscode 中配置")
        print("\n" + "=" * 50)
        return False


if __name__ == "__main__":
    success = test_llm()
    sys.exit(0 if success else 1)
