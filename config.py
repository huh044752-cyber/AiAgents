"""
AI Agent 全局配置模块
从环境变量和 .env 文件加载配置
支持运行时热加载：调用 reload() 后重新读取 .env 文件

路径配置规则:
  - 环境变量为空或未设置 → 使用 PROJECT_ROOT 下的默认相对路径
  - 环境变量为绝对路径   → 直接使用（部署环境推荐）
  - 环境变量为相对路径   → 基于 PROJECT_ROOT 解析

所有可配置参数统一在此管理，不在业务代码中写死
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录（config.py 所在目录的绝对路径，开发和部署均可靠）
PROJECT_ROOT = Path(__file__).resolve().parent

# 加载 .env 文件
load_dotenv(PROJECT_ROOT / ".env", override=True)


# ── 辅助函数 ──────────────────────────────────────────────

def _getenv(key: str, default: str = "") -> str:
    """获取环境变量，空字符串视为未设置，返回默认值"""
    val = os.getenv(key, "")
    return val.strip() if val.strip() else default


def _resolve_path(env_key: str, default_relative: str) -> str:
    """获取路径配置，支持绝对 / 相对 / 留空三种写法

    - 环境变量为空或未设置 → PROJECT_ROOT / default_relative
    - 环境变量为绝对路径   → 直接使用（如 /data/kb 或 D:\\data\\kb）
    - 环境变量为相对路径   → 基于 PROJECT_ROOT 解析
    """
    val = os.getenv(env_key, "").strip()
    if not val:
        return str(PROJECT_ROOT / default_relative)
    p = Path(val)
    if p.is_absolute():
        return str(p)
    return str((PROJECT_ROOT / p).resolve())


# ── 热加载 ────────────────────────────────────────────────

def reload():
    """热加载：重新读取 .env 文件并刷新所有配置实例
    在 UI 中修改配置保存后调用此函数，无需重启
    """
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    sim_engine._reload()
    llm._reload()
    agent._reload()
    rag._reload()
    log._reload()
    replay._reload()


# ── 配置类 ────────────────────────────────────────────────

class SimEngineConfig:
    """C++ 仿真引擎连接配置"""

    def __init__(self):
        self._reload()

    def _reload(self):
        self.HOST: str = _getenv("SIM_ENGINE_HOST", "localhost")
        self.PORT: int = int(_getenv("SIM_ENGINE_PORT", "8080"))
        self.HTTP_TIMEOUT: float = float(_getenv("SIM_ENGINE_HTTP_TIMEOUT", "10.0"))

    @property
    def base_url(self) -> str:
        return f"http://{self.HOST}:{self.PORT}"


class LLMConfig:
    """LLM 模型配置"""

    def __init__(self):
        self._reload()

    def _reload(self):
        self.DASHSCOPE_API_KEY: str = _getenv("DASHSCOPE_API_KEY", "")
        self.MODEL_NAME: str = _getenv("QWEN_MODEL_NAME", "qwen-plus")
        self.TEMPERATURE: float = float(_getenv("LLM_TEMPERATURE", "0.3"))
        self.TOP_P: float = float(_getenv("LLM_TOP_P", "0.8"))


class AgentConfig:
    """Agent 行为配置"""

    def __init__(self):
        self._reload()

    def _reload(self):
        self.MAX_ITERATIONS: int = int(_getenv("AGENT_MAX_ITERATIONS", "50"))
        self.TIMEOUT_SECONDS: int = int(_getenv("AGENT_TIMEOUT_SECONDS", "30"))


class RAGConfig:
    """RAG 检索配置"""

    def __init__(self):
        self._reload()

    def _reload(self):
        self.EMBEDDING_MODEL: str = _getenv("RAG_EMBEDDING_MODEL", "text-embedding-v3")
        self.CHUNK_SIZE: int = int(_getenv("RAG_CHUNK_SIZE", "800"))
        self.CHUNK_OVERLAP: int = int(_getenv("RAG_CHUNK_OVERLAP", "100"))
        self.RETRIEVE_TOP_K: int = int(_getenv("RAG_RETRIEVE_TOP_K", "3"))
        self.KNOWLEDGE_BASE_DIR: str = _resolve_path(
            "RAG_KNOWLEDGE_BASE_DIR", os.path.join("rag", "knowledge_base"),
        )
        self.VECTOR_STORE_DIR: str = _resolve_path(
            "RAG_VECTOR_STORE_DIR", os.path.join("rag", "vector_store"),
        )


class LogConfig:
    """日志配置"""

    def __init__(self):
        self._reload()

    def _reload(self):
        self.LEVEL: str = _getenv("LOG_LEVEL", "INFO")
        self.FILE_LEVEL: str = _getenv("LOG_FILE_LEVEL", "DEBUG")
        self.LOG_DIR: str = _resolve_path("LOG_DIR", "logs")
        self.ROTATION: str = _getenv("LOG_ROTATION", "50 MB")
        self.RETENTION: str = _getenv("LOG_RETENTION", "7 days")


class ReplayConfig:
    """回放记录配置"""

    def __init__(self):
        self._reload()

    def _reload(self):
        self.REPLAY_DIR: str = _resolve_path("REPLAY_DIR", "replays")


# ── 全局配置实例 ──────────────────────────────────────────

sim_engine = SimEngineConfig()
llm = LLMConfig()
agent = AgentConfig()
rag = RAGConfig()
log = LogConfig()
replay = ReplayConfig()
