"""
MCP 服务监控页面 - 查看所有 MCP 工具、测试接口、监控状态
工具中文名、API 端点列表均从外部配置加载
"""
import streamlit as st
import json
import time
import sys
from pathlib import Path

import config

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from styles import (
    _api_endpoints, _colors,
    get_tool_cn_name, get_tool_cn_desc,
    get_ui_text, get_ui_param,
)


def render():
    st.markdown(get_ui_text("mcp_monitor", "page_title", "# 🔗 MCP 服务监控"))
    st.markdown(get_ui_text("mcp_monitor", "page_desc", "查看和测试 MCP 工具接口。"))

    # ── 连接信息 ──
    base_url = f"http://{config.sim_engine.HOST}:{config.sim_engine.PORT}"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="status-card">
            <h3>引擎地址</h3>
            <div class="metric">{config.sim_engine.HOST}</div>
            <div class="label">端口: {config.sim_engine.PORT}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="status-card">
            <h3>超时设置</h3>
            <div class="metric">{config.sim_engine.HTTP_TIMEOUT}s</div>
            <div class="label">HTTP 请求超时</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        connected = False
        latency = 0
        try:
            import httpx
            start = time.time()
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{base_url}/api/health")
                latency = (time.time() - start) * 1000
                connected = resp.status_code == 200
        except Exception:
            pass

        _clr = _colors()
        color = _clr.get("success", "#3fb950") if connected else _clr.get("error", "#f85149")
        status_text = "已连接" if connected else "未连接"
        latency_text = f"{latency:.0f}ms" if connected else "N/A"
        st.markdown(f"""
        <div class="status-card">
            <h3>连接状态</h3>
            <div class="metric" style="color:{color}">{status_text}</div>
            <div class="label">延迟: {latency_text}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── 标签页（从配置读取）──
    tab_labels = get_ui_param("mcp_monitor", "tabs", ["📦 MCP 工具列表", "🧪 接口测试", "📡 API 端点"])
    tab_tools, tab_test, tab_endpoints = st.tabs(tab_labels)

    # ━━━━ MCP 工具列表 ━━━━
    with tab_tools:
        st.markdown("### 已注册的 MCP 工具")

        from mcp.tools import ALL_TOOLS, QUERY_TOOLS, CONTROL_TOOLS

        col_q, col_c = st.columns(2)

        with col_q:
            st.markdown(f"#### 🔍 查询工具 ({len(QUERY_TOOLS)} 个)")
            for tool_obj in QUERY_TOOLS:
                _render_tool_card(tool_obj, "🔍")

        with col_c:
            st.markdown(f"#### ⚡ 控制工具 ({len(CONTROL_TOOLS)} 个)")
            for tool_obj in CONTROL_TOOLS:
                _render_tool_card(tool_obj, "⚡")

    # ━━━━ 接口测试 ━━━━
    with tab_test:
        st.markdown("### 手动测试 MCP 工具")

        from mcp.tools import ALL_TOOLS as _ALL

        tool_display = [f"{get_tool_cn_name(t.name)} ({t.name})" for t in _ALL]
        selected_idx = st.selectbox(
            "选择工具", range(len(_ALL)),
            format_func=lambda i: tool_display[i],
        )

        selected = _ALL[selected_idx]
        cn_name = get_tool_cn_name(selected.name)
        cn_desc = get_tool_cn_desc(selected.name)
        st.markdown(f"**{cn_name}** — {cn_desc if cn_desc else selected.description}")

        params = {}
        if hasattr(selected, "args_schema") and selected.args_schema:
            schema = selected.args_schema.model_json_schema()
            props = schema.get("properties", {})
            required = schema.get("required", [])

            if props:
                st.markdown("**参数输入：**")
                for pname, pinfo in props.items():
                    ptype = pinfo.get("type", "string")
                    default = pinfo.get("default", "")
                    desc = pinfo.get("description", pname)
                    is_required = pname in required
                    label = f"{pname}{'  *必填' if is_required else ''}"

                    if ptype in ("number", "integer"):
                        params[pname] = st.number_input(
                            label,
                            value=float(default) if default != "" and default is not None else 0.0,
                            help=desc, key=f"test_{selected.name}_{pname}",
                        )
                        if ptype == "integer":
                            params[pname] = int(params[pname])
                    elif ptype == "boolean":
                        params[pname] = st.checkbox(
                            label,
                            value=bool(default) if default != "" else False,
                            help=desc, key=f"test_{selected.name}_{pname}",
                        )
                    else:
                        params[pname] = st.text_input(
                            label,
                            value=str(default) if default != "" and default is not None else "",
                            help=desc, key=f"test_{selected.name}_{pname}",
                        )

        if st.button("▶️ 执行", type="primary", use_container_width=True):
            with st.spinner(f"执行 {cn_name}..."):
                try:
                    start = time.time()
                    result = selected.invoke(params)
                    elapsed = (time.time() - start) * 1000
                    st.success(f"✅ 执行完成 ({elapsed:.0f}ms)")
                    st.json(result)
                except Exception as e:
                    st.error(f"❌ 执行失败: {e}")

    # ━━━━ API 端点（从配置读取）━━━━
    with tab_endpoints:
        st.markdown("### REST API 端点列表 (C++ AiHttpService)")

        # 快捷测试
        st.markdown("#### 快捷测试")
        col_url, col_method = st.columns([4, 1])
        with col_url:
            test_url = st.text_input("请求 URL", value=f"{base_url}/api/health")
        with col_method:
            test_method = st.selectbox("方法", ["GET", "POST"], key="ep_method")

        test_body = ""
        if test_method == "POST":
            test_body = st.text_area("请求 Body (JSON)", value="{}", height=100)

        if st.button("🚀 发送请求", type="primary"):
            _send_raw_request(test_url, test_method, test_body)

        st.markdown("---")
        _endpoints = _api_endpoints()
        _clr2 = _colors()
        st.markdown(f"#### 全部端点 ({len(_endpoints)} 个)")

        for ep in _endpoints:
            method = ep.get("method", "GET")
            path = ep.get("path", "")
            name_cn = ep.get("name", "")
            desc_cn = ep.get("desc", "")
            method_color = _clr2.get("success", "#3fb950") if method == "GET" else _clr2.get("warning", "#d29922")
            st.markdown(
                f'<span style="display:inline-block;min-width:48px;color:{method_color};'
                f'font-weight:bold;font-family:monospace">{method}</span> '
                f'<code>{path}</code> — **{name_cn}** · '
                f'<span style="color:{_clr2.get("text_muted", "#8b949e")}">{desc_cn}</span>',
                unsafe_allow_html=True,
            )


def _render_tool_card(tool_obj, icon: str):
    """渲染单个工具卡片"""
    cn_name = get_tool_cn_name(tool_obj.name)
    cn_desc = get_tool_cn_desc(tool_obj.name)

    with st.expander(f"{icon} {cn_name}  `{tool_obj.name}`"):
        if cn_desc:
            st.markdown(f"**功能：** {cn_desc}")
        else:
            st.markdown(f"**功能：** {tool_obj.description}")

        if hasattr(tool_obj, "args_schema") and tool_obj.args_schema:
            schema = tool_obj.args_schema.model_json_schema()
            props = schema.get("properties", {})
            required = schema.get("required", [])
            if props:
                st.markdown("**参数：**")
                for pname, pinfo in props.items():
                    ptype = pinfo.get("type", "any")
                    desc = pinfo.get("description", "")
                    req_mark = " *必填*" if pname in required else ""
                    default_str = ""
                    if "default" in pinfo:
                        default_str = f"，默认: `{pinfo['default']}`"
                    st.markdown(f"- `{pname}` ({ptype}{req_mark}): {desc}{default_str}")
            else:
                st.caption("无参数")


def _send_raw_request(url: str, method: str, body: str = ""):
    """发送原始 HTTP 请求"""
    import httpx
    try:
        with httpx.Client(timeout=10.0) as client:
            start = time.time()
            if method == "GET":
                resp = client.get(url)
            else:
                try:
                    json_body = json.loads(body) if body.strip() else {}
                except json.JSONDecodeError:
                    st.error("Body JSON 格式错误")
                    return
                resp = client.post(url, json=json_body)

            elapsed = (time.time() - start) * 1000
            _c = _colors()
            status_color = _c.get("success", "#3fb950") if resp.status_code == 200 else _c.get("error", "#f85149")
            st.markdown(
                f'状态: <span style="color:{status_color};font-weight:bold">{resp.status_code}</span> · '
                f'耗时: {elapsed:.0f}ms',
                unsafe_allow_html=True,
            )
            try:
                st.json(resp.json())
            except Exception:
                st.code(resp.text[:2000])
    except httpx.ConnectError:
        st.error(f"❌ 无法连接: {url}")
    except Exception as e:
        st.error(f"❌ 请求异常: {e}")
