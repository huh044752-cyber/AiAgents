"""
智能对话页面 - 与 AI Agent 交互
所有文本、参数、快捷指令均从外部配置加载
"""
import streamlit as st
import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from styles import get_ui_text, get_ui_param, _quick_commands


def render():
    # ── 页面标题（从配置读取）──
    st.markdown(get_ui_text("chat", "page_title", "# 💬 智能对话"))
    st.markdown(get_ui_text("chat", "page_desc", "向 AI 飞行指挥官下达任务指令"))

    # ── 初始化会话状态 ──
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "agent_running" not in st.session_state:
        st.session_state.agent_running = False

    # ── 从配置读取参数 ──
    iter_default = get_ui_param("chat", "max_iter_default", 50)
    iter_min = get_ui_param("chat", "max_iter_min", 1)
    iter_max = get_ui_param("chat", "max_iter_max", 200)
    iter_step = get_ui_param("chat", "max_iter_step", 10)
    chat_height = get_ui_param("chat", "chat_height", 480)
    user_avatar = get_ui_text("chat", "user_avatar", "🧑‍✈️")
    ai_avatar = get_ui_text("chat", "ai_avatar", "🤖")
    input_placeholder = get_ui_text("chat", "input_placeholder", "输入任务指令...")

    # ── 顶部工具栏：四等分对齐 ──
    col_mode, col_iter, col_clear, col_export = st.columns(4)
    with col_mode:
        skip_check = st.checkbox("离线模式（跳过引擎连接）", value=True)
    with col_iter:
        max_iter = st.number_input(
            "最大迭代次数",
            min_value=iter_min, max_value=iter_max,
            value=iter_default, step=iter_step,
            label_visibility="visible",
        )
    with col_clear:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()
    with col_export:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("📋 导出对话", use_container_width=True):
            if st.session_state.chat_messages:
                export_text = _export_chat(st.session_state.chat_messages)
                st.session_state["_export_text"] = export_text
            else:
                st.toast("暂无对话记录")

    # 导出内容展示
    if st.session_state.get("_export_text"):
        with st.expander("📋 对话导出内容（可复制）", expanded=True):
            st.code(st.session_state["_export_text"], language="markdown")
            if st.button("关闭导出", key="close_export"):
                del st.session_state["_export_text"]
                st.rerun()

    st.markdown("---")

    # ── 对话历史展示 ──
    chat_container = st.container(height=chat_height)
    with chat_container:
        if not st.session_state.chat_messages:
            empty_title = get_ui_text("chat", "empty_title", "✈️ 准备就绪")
            empty_desc = get_ui_text("chat", "empty_desc", "输入任务指令开始对话")
            st.markdown(
                f"<div style='text-align:center; color:#8b949e; padding:4rem 0;'>"
                f"<h3>{empty_title}</h3>"
                f"<p>{empty_desc}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            for msg in st.session_state.chat_messages:
                if msg["role"] == "user":
                    with st.chat_message("user", avatar=user_avatar):
                        st.markdown(msg["content"])
                else:
                    with st.chat_message("assistant", avatar=ai_avatar):
                        st.markdown(msg["content"])

    # ── 输入框 ──
    user_input = st.chat_input(input_placeholder)

    if user_input and not st.session_state.agent_running:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with chat_container:
            with st.chat_message("user", avatar=user_avatar):
                st.markdown(user_input)

        st.session_state.agent_running = True
        with chat_container:
            with st.chat_message("assistant", avatar=ai_avatar):
                with st.spinner("🧠 Agent 正在分析和执行..."):
                    result_text = _run_agent_task(user_input, max_iter, skip_check)
                st.markdown(result_text)

        st.session_state.chat_messages.append({"role": "assistant", "content": result_text})
        st.session_state.agent_running = False
        st.rerun()

    # ── 快捷指令（热加载，修改 quick_commands.json 自动生效）──
    quick_cmds = _quick_commands()
    if quick_cmds:
        st.markdown("### 📋 快捷指令")
        cols = st.columns(len(quick_cmds))
        for i, cmd_cfg in enumerate(quick_cmds):
            icon = cmd_cfg.get("icon", f"指令{i+1}")
            command = cmd_cfg.get("command", "")
            with cols[i]:
                if st.button(icon, key=f"quick_{i}", use_container_width=True, help=command):
                    st.session_state.chat_messages.append({"role": "user", "content": command})
                    st.rerun()


def _run_agent_task(task: str, max_iterations: int, skip_check: bool) -> str:
    """执行 Agent 任务并返回结果文本"""
    try:
        import config

        if not skip_check:
            from mcp.client import get_client
            client = get_client()
            if not client.health_check():
                return "❌ **引擎未连接**，请先启动 C++ 仿真引擎或开启离线模式。"

        from agent.graph import run_agent
        final_state = run_agent(task, max_iterations=max_iterations)

        parts = ["### ✅ 任务执行完成\n"]
        if final_state:
            intent = final_state.get("tactical_intent", "")
            if intent:
                try:
                    intent_json = json.loads(intent)
                    parts.append("**📋 战术意图：**")
                    parts.append(f"- 任务理解：{intent_json.get('mission_understanding', 'N/A')}")
                    parts.append(f"- 态势评估：{intent_json.get('situation_assessment', 'N/A')}")
                    parts.append(f"- 战术方案：{intent_json.get('recommended_approach', 'N/A')}")
                except (json.JSONDecodeError, TypeError):
                    parts.append(f"**📋 战术意图：** {intent[:500]}")
            result = final_state.get("execution_result", "")
            if result:
                parts.append(f"\n**🎯 执行结果：** {str(result)[:800]}")
            skill = final_state.get("selected_skill", "")
            if skill:
                parts.append(f"\n**🔧 使用技能：** {str(skill)[:500]}")
        else:
            parts.append("Agent 未返回结果状态。")
        return "\n".join(parts)
    except Exception as e:
        return f"❌ **执行出错：** `{str(e)}`"


def _export_chat(messages: list) -> str:
    """导出对话为 Markdown 文本"""
    app_title = get_ui_text("app", "title", "AI Agent")
    lines = [f"# {app_title} 对话记录\n"]
    lines.append(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append("---\n")
    for msg in messages:
        role = "🧑‍✈️ 指挥官" if msg["role"] == "user" else "🤖 Agent"
        lines.append(f"### {role}\n")
        lines.append(msg["content"])
        lines.append("\n")
    return "\n".join(lines)
