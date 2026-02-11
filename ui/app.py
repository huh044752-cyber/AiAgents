"""
AI 飞行仿真 Agent - 控制台主界面
使用 Streamlit 构建，提供：对话、知识库、配置、MCP监控

启动方式: streamlit run ui/app.py

所有可配置数据均从 ui/ui_config/ 目录下的 JSON 文件加载:
  theme.json / doc_categories.json / tool_names.json
  quick_commands.json / api_endpoints.json / env_meta.json
  ui_text.json / doc_templates/*.md
二次开发时只需修改 JSON 文件，无需改动 Python 代码。
"""
import sys
from pathlib import Path

# 将项目根目录加入 sys.path（resolve 确保绝对路径，开发和部署通用）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 将 ui 目录也加入，供 components 中 import styles
UI_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(UI_DIR))

import streamlit as st
from styles import get_global_css, get_ui_text, get_ui_param

# ──────────── 从配置读取应用元信息 ────────────
app_title = get_ui_text("app", "title", "AI 飞行仿真 Agent")
app_icon = get_ui_text("app", "icon", "✈️")
app_version = get_ui_text("app", "version", "v1.0")
app_subtitle = get_ui_text("app", "subtitle", "Streamlit Dashboard")

# ──────────── 页面配置 ────────────
st.set_page_config(
    page_title=app_title,
    page_icon=app_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────── 注入全局 CSS（热加载，修改 theme.json 后自动生效） ────────────
st.markdown(get_global_css(), unsafe_allow_html=True)

# ──────────── 从配置读取导航项 ────────────
nav_config = get_ui_param("navigation", None, [
    {"label": "💬 智能对话", "page": "chat"},
    {"label": "📚 知识库管理", "page": "knowledge"},
    {"label": "⚙️ 系统配置", "page": "settings"},
    {"label": "🔗 MCP 服务", "page": "mcp_monitor"},
])

nav_labels = [item.get("label", "") for item in nav_config]
nav_pages = [item.get("page", "") for item in nav_config]

# ──────────── 侧边栏 ────────────
with st.sidebar:
    st.markdown(f"## {app_icon} {app_title}")
    st.markdown("---")

    page_label = st.radio(
        "导航",
        nav_labels,
        label_visibility="collapsed",
    )

    st.markdown("---")

    # 引擎连接状态指示
    st.markdown("### 引擎状态")
    try:
        from mcp.client import get_client
        client = get_client()
        ok = client.health_check()
        if ok:
            st.success("🟢 引擎已连接")
        else:
            st.warning("🟡 引擎响应异常")
    except Exception:
        st.error("🔴 引擎未连接")

    st.caption(f"{app_version} · {app_subtitle}")

# ──────────── 页面路由 ────────────
selected_page = ""
for i, label in enumerate(nav_labels):
    if page_label == label:
        selected_page = nav_pages[i]
        break

if selected_page == "chat":
    from components import chat
    chat.render()
elif selected_page == "knowledge":
    from components import knowledge
    knowledge.render()
elif selected_page == "settings":
    from components import settings
    settings.render()
elif selected_page == "mcp_monitor":
    from components import mcp_monitor
    mcp_monitor.render()
