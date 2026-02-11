"""
统一样式与配置加载模块（热加载版）
所有可配置数据从 ui_config/ 目录下的 JSON 文件加载
修改 JSON 文件后无需重启 UI，自动检测文件变化并重新加载

配置文件清单:
  ui_config/theme.json          - 主题颜色
  ui_config/doc_categories.json - 知识库文档分类
  ui_config/tool_names.json     - MCP 工具中文映射
  ui_config/quick_commands.json - 对话快捷指令
  ui_config/api_endpoints.json  - REST API 端点列表
  ui_config/env_meta.json       - 环境变量元信息
  ui_config/ui_text.json        - UI 界面文本/参数
  ui_config/doc_templates/      - 各分类文档模板
"""
import json
from pathlib import Path

# ============================================================================
# 配置文件目录
# ============================================================================
_CONFIG_DIR = Path(__file__).resolve().parent / "ui_config"
_TEMPLATE_DIR = _CONFIG_DIR / "doc_templates"


# ============================================================================
# 热加载配置管理器
# ============================================================================
class _ConfigManager:
    """
    配置管理器 - 自动热加载
    每个 JSON 文件记录最后修改时间 (mtime)，
    访问配置时检测文件是否变化，变化则自动重新加载。
    """

    def __init__(self, config_dir: Path):
        self._dir = config_dir
        self._cache: dict[str, dict] = {}      # filename -> parsed data
        self._mtimes: dict[str, float] = {}     # filename -> last mtime

    def get(self, filename: str) -> dict:
        """获取指定配置文件内容，自动检测变化并热加载"""
        filepath = self._dir / filename
        if not filepath.exists():
            return {}

        current_mtime = filepath.stat().st_mtime
        cached_mtime = self._mtimes.get(filename, 0)

        if filename not in self._cache or current_mtime != cached_mtime:
            # 文件新增或已修改 -> 重新加载
            self._cache[filename] = json.loads(
                filepath.read_text(encoding="utf-8")
            )
            self._mtimes[filename] = current_mtime

        return self._cache[filename]

    def reload_all(self):
        """强制重新加载所有已缓存的配置"""
        self._cache.clear()
        self._mtimes.clear()


# 全局配置管理器实例
_cfg = _ConfigManager(_CONFIG_DIR)


# ============================================================================
# 便捷访问函数（每次调用时自动检测文件变化）
# ============================================================================

def _colors() -> dict:
    data = _cfg.get("theme.json")
    return data.get("colors", {
        "primary": "#58a6ff", "primary_hover": "rgba(88,166,255,0.15)",
        "primary_active": "rgba(88,166,255,0.25)", "bg_dark": "#0e1117",
        "bg_card": "#161b22", "bg_card_alt": "#1c2333", "border": "#30363d",
        "text_primary": "#f0f6fc", "text_secondary": "#c9d1d9", "text_muted": "#8b949e",
        "success": "#3fb950", "warning": "#d29922", "error": "#f85149",
        "chat_user_bg": "linear-gradient(135deg, #1f6feb, #388bfd)", "chat_ai_bg": "#161b22",
    })


def _doc_categories() -> dict:
    data = _cfg.get("doc_categories.json")
    return data.get("categories", {
        "general": {"label": "通用文档", "icon": "📄", "prefix": "通用文档", "keywords": [], "template": "general.md"}
    })


def _tool_cn_names() -> dict:
    data = _cfg.get("tool_names.json")
    return data.get("tools", {})


def _quick_commands() -> list:
    data = _cfg.get("quick_commands.json")
    return data.get("commands", [])


def _api_endpoints() -> list:
    data = _cfg.get("api_endpoints.json")
    return data.get("endpoints", [])


def _env_meta() -> list:
    data = _cfg.get("env_meta.json")
    return data.get("variables", [])


def _ui_text() -> dict:
    return _cfg.get("ui_text.json")


# ============================================================================
# 兼容属性访问（通过 property-like 模块级变量）
# 外部代码用 COLORS / DOC_CATEGORIES 等时，每次访问都走热加载
# ============================================================================

class _LiveConfig:
    """动态配置代理，属性访问时实时读取最新配置"""

    @property
    def COLORS(self) -> dict:
        return _colors()

    @property
    def DOC_CATEGORIES(self) -> dict:
        return _doc_categories()

    @property
    def TOOL_CN_NAMES(self) -> dict:
        return _tool_cn_names()

    @property
    def QUICK_COMMANDS(self) -> list:
        return _quick_commands()

    @property
    def API_ENDPOINTS(self) -> list:
        return _api_endpoints()

    @property
    def ENV_META(self) -> list:
        return _env_meta()

    @property
    def UI_TEXT(self) -> dict:
        return _ui_text()

    @property
    def GLOBAL_CSS(self) -> str:
        return _build_css(_colors())

    def reload(self):
        """手动强制重新加载所有配置"""
        _cfg.reload_all()


# 模块级单例
_live = _LiveConfig()


# ============================================================================
# 模块级兼容变量（向后兼容：from styles import COLORS 等）
# 注意: 这些是首次加载的快照。推荐使用函数或 _live 访问以获得热加载
# ============================================================================

def _build_css(colors: dict) -> str:
    """根据颜色生成 CSS"""
    return """
<style>
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, %(bg_dark)s 0%%, %(bg_card)s 100%%);
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: %(primary)s;
}
.status-card {
    background: linear-gradient(135deg, %(bg_card)s, %(bg_card_alt)s);
    border: 1px solid %(border)s;
    border-radius: 12px; padding: 1.2rem; margin: 0.5rem 0;
}
.status-card h3 { color: %(primary)s; margin: 0 0 0.5rem 0; font-size: 1rem; }
.status-card .metric { font-size: 1.8rem; font-weight: bold; color: %(text_primary)s; }
.status-card .label { color: %(text_muted)s; font-size: 0.85rem; }
.chat-user {
    background: %(chat_user_bg)s; color: white;
    padding: 0.8rem 1.2rem; border-radius: 16px 16px 4px 16px;
    max-width: 80%%; margin-left: auto; margin-bottom: 0.5rem;
}
.chat-ai {
    background: %(chat_ai_bg)s; border: 1px solid %(border)s;
    color: %(text_secondary)s; padding: 0.8rem 1.2rem;
    border-radius: 16px 16px 16px 4px; max-width: 80%%; margin-bottom: 0.5rem;
}
.stButton > button { border-radius: 8px; font-weight: 600; transition: all 0.3s; }
.stButton > button:hover {
    transform: translateY(-1px); box-shadow: 0 4px 12px rgba(88,166,255,0.3);
}
.editor-container { border: 1px solid %(border)s; border-radius: 8px; overflow: hidden; }
.tag { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.78rem; font-weight: 600; margin-right: 4px; }
.tag-query { background: rgba(56,139,253,0.15); color: #58a6ff; }
.tag-control { background: rgba(210,153,34,0.15); color: #d29922; }
.tag-category { background: rgba(63,185,80,0.15); color: #3fb950; }
.category-header {
    background: linear-gradient(135deg, %(bg_card)s, %(bg_card_alt)s);
    border: 1px solid %(border)s; border-radius: 10px;
    padding: 0.8rem 1rem; margin: 1rem 0 0.5rem 0;
}
.category-header h4 { margin: 0; color: %(primary)s; }
.category-header .count { color: %(text_muted)s; font-size: 0.85rem; }
.tool-card {
    background: %(bg_card)s; border: 1px solid %(border)s;
    border-radius: 10px; padding: 0.8rem 1rem; margin-bottom: 0.5rem; transition: border-color 0.3s;
}
.tool-card:hover { border-color: %(primary)s; }
.tool-card .tool-name { font-weight: 700; color: %(text_primary)s; }
.tool-card .tool-cn-name { color: %(primary)s; font-size: 0.9rem; }
.tool-card .tool-desc { color: %(text_muted)s; font-size: 0.85rem; margin-top: 4px; }
</style>
""" % colors


# ============================================================================
# 公开 API 函数（全部走热加载，修改 JSON 后无需重启）
# ============================================================================

def get_colors() -> dict:
    """获取当前颜色配置（热加载）"""
    return _colors()


def get_global_css() -> str:
    """获取全局 CSS（热加载，颜色变化自动生效）"""
    return _build_css(_colors())


def get_category_label(cat_key: str) -> str:
    """获取分类中文标签"""
    cats = _doc_categories()
    info = cats.get(cat_key, cats.get("general", {}))
    return f"{info.get('icon', '📄')} {info.get('label', cat_key)}"


def categorize_doc(filename: str) -> str:
    """根据文件名推断文档类别"""
    cats = _doc_categories()
    name_lower = filename.lower()
    for cat_key, cat_info in cats.items():
        if cat_key == "general":
            continue
        for kw in cat_info.get("keywords", []):
            if kw in name_lower:
                return cat_key
    return "general"


def get_tool_cn_name(tool_name: str) -> str:
    """获取工具中文名称"""
    info = _tool_cn_names().get(tool_name, {})
    return info.get("cn_name", tool_name)


def get_tool_cn_desc(tool_name: str) -> str:
    """获取工具中文简述"""
    info = _tool_cn_names().get(tool_name, {})
    return info.get("cn_desc", "")


def get_ui_text(section: str, key: str, default: str = "") -> str:
    """获取 UI 文本配置"""
    text = _ui_text()
    val = text.get(section, {})
    if isinstance(val, dict):
        return val.get(key, default)
    return default


def get_ui_param(section: str, key=None, default=None):
    """获取 UI 参数配置（可返回任意类型）
    当 key 为 None 时直接返回整个 section 的值
    """
    text = _ui_text()
    value = text.get(section, default)
    if key is None:
        return value
    if isinstance(value, dict):
        return value.get(key, default)
    return default


def load_doc_template(cat_key: str, title: str = "") -> str:
    """加载指定分类的文档模板，替换 {{title}} 占位符"""
    cats = _doc_categories()
    cat_info = cats.get(cat_key, cats.get("general", {}))
    template_file = cat_info.get("template", "general.md")
    template_path = _TEMPLATE_DIR / template_file

    if template_path.exists():
        content = template_path.read_text(encoding="utf-8")
        heading = title if title else cat_info.get("label", "文档")
        return content.replace("{{title}}", heading)

    heading = title if title else "文档"
    return f"# {heading}\n\n## 概述\n\n## 内容\n\n## 备注\n"


def load_json_template(cat_key: str, title: str = "") -> str:
    """生成 JSON 格式的文档模板"""
    import json as _json
    data = [{
        "category": cat_key,
        "title": title if title else "知识条目标题",
        "content": "知识条目内容，将被分块后索引到向量库中。",
        "tags": ["标签1", "标签2"],
    }]
    return _json.dumps(data, ensure_ascii=False, indent=2)


def reload_config():
    """手动强制重新加载所有配置（供 UI 刷新按钮调用）"""
    _cfg.reload_all()
