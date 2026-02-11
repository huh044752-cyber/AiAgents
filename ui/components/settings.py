"""
系统配置页面 - 编辑 .env 和所有配置项
环境变量元信息、选项列表均从外部 JSON 配置加载
"""
import streamlit as st
from pathlib import Path
from collections import OrderedDict
import sys
import importlib

import config

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from styles import _env_meta, get_ui_text, get_ui_param


ENV_FILE = Path(config.PROJECT_ROOT) / ".env"
ENV_EXAMPLE = Path(config.PROJECT_ROOT) / ".env.example"


def render():
    st.markdown(get_ui_text("settings", "page_title", "# ⚙️ 系统配置"))
    st.markdown(get_ui_text("settings", "page_desc", "管理 Agent 的所有配置参数。"))

    # ── 保存成功提示（跨 rerun 持久） ──
    if st.session_state.get("_config_saved"):
        st.success("✅ 配置已保存并立即生效！")
        del st.session_state["_config_saved"]
    if st.session_state.get("_config_reset"):
        st.success("✅ 已重置为默认配置并立即生效！")
        del st.session_state["_config_reset"]

    # ── 加载当前 .env ──
    env_data = _load_env()

    # ── 标签页分组（从配置读取）──
    tab_labels = get_ui_param("settings", "tabs", [
        "🤖 LLM 模型", "🖥️ 仿真引擎", "📚 RAG 检索",
        "🎮 Agent 行为", "📋 日志/回放", "📝 原始 .env"
    ])
    tabs = st.tabs(tab_labels)

    # ── 按 env_meta.json 中的分组自动渲染各标签页（热加载） ──
    _meta = _env_meta()
    groups = OrderedDict()
    for var_info in _meta:
        group = var_info.get("group", "其他")
        if group not in groups:
            groups[group] = []
        groups[group].append(var_info)

    # 分组映射到标签页索引（前 N-1 个标签给分组，最后一个给原始 .env）
    group_keys = list(groups.keys())
    tab_count = len(tabs)

    # ── 渲染各分组标签页（主要编辑界面）──
    for i, group_name in enumerate(group_keys):
        if i >= tab_count - 1:
            break  # 最后一个标签留给原始 .env
        with tabs[i]:
            st.markdown(f"### {group_name} 配置")
            vars_in_group = groups[group_name]
            _render_group_form(env_data, vars_in_group)

    # ━━━━ 原始 .env 标签页（只读预览 + 自定义变量管理）━━━━
    with tabs[tab_count - 1]:
        st.markdown("### 原始 .env 文件预览")
        st.caption("此处显示当前 .env 文件内容。请在左侧分组标签页中编辑配置项。")

        # 只读预览当前 .env 文件
        if ENV_FILE.exists():
            raw_content = ENV_FILE.read_text(encoding="utf-8")
        else:
            raw_content = "# .env 文件尚未创建"
        st.code(raw_content, language="bash")

        # ── 自定义新增项 ──
        st.markdown("---")
        st.markdown("#### ➕ 自定义配置项")
        st.caption("如果需要添加上面分组中未列出的环境变量，可以在此添加。")

        known_keys = {v.get("key") for v in _meta}
        extra_keys = [k for k in env_data if k not in known_keys]
        for ek in extra_keys:
            env_data[ek] = st.text_input(
                f"`{ek}`", value=env_data[ek], key=f"raw_extra_{ek}",
            )

        col_add1, col_add2 = st.columns([2, 3])
        with col_add1:
            new_key = st.text_input("新变量名", placeholder="MY_CUSTOM_VAR", key="raw_new_key")
        with col_add2:
            new_value = st.text_input("新变量值", placeholder="some_value", key="raw_new_val")
        if st.button("➕ 添加自定义变量", key="raw_add_btn"):
            if new_key and new_key.strip():
                env_data[new_key.strip()] = new_value.strip()
                st.success(f"已添加: {new_key.strip()}")
                st.rerun()

    # ── 保存 / 重置按钮 ──
    st.markdown("---")
    col_save, col_reset = st.columns([3, 1])
    with col_save:
        if st.button("💾 保存所有配置", use_container_width=True, type="primary"):
            _save_env(env_data)
            _reload_config()
            st.session_state["_config_saved"] = True
            st.rerun()
    with col_reset:
        if st.button("↩️ 重置为默认", use_container_width=True):
            if ENV_EXAMPLE.exists():
                env_data = _parse_env_text(ENV_EXAMPLE.read_text(encoding="utf-8"))
                _save_env(env_data)
                _reload_config()
                st.session_state["_config_reset"] = True
                st.rerun()


def _render_group_form(env_data: dict, vars_list: list):
    """根据 env_meta.json 中的类型定义动态渲染表单控件"""
    for var_info in vars_list:
        key = var_info.get("key", "")
        label = var_info.get("label", key)
        desc = var_info.get("desc", "")
        var_type = var_info.get("type", "text")
        default = var_info.get("default", "")
        options = var_info.get("options", [])

        current_val = env_data.get(key, default)

        if var_type == "password":
            env_data[key] = st.text_input(
                label, value=str(current_val), type="password",
                help=desc, key=f"cfg_{key}",
            )

        elif var_type == "select" and options:
            try:
                idx = options.index(str(current_val)) if str(current_val) in options else 0
            except ValueError:
                idx = 0
            env_data[key] = st.selectbox(
                label, options, index=idx,
                help=desc, key=f"cfg_{key}",
            )

        elif var_type == "slider":
            min_val = float(var_info.get("min", 0))
            max_val = float(var_info.get("max", 1))
            step_val = float(var_info.get("step", 0.05))
            try:
                cur_float = float(current_val)
            except (ValueError, TypeError):
                cur_float = float(default) if default else min_val
            env_data[key] = str(st.slider(
                label, min_value=min_val, max_value=max_val,
                value=cur_float, step=step_val,
                help=desc, key=f"cfg_{key}",
            ))

        elif var_type == "number":
            min_val = var_info.get("min", 0)
            max_val = var_info.get("max", 9999)
            step_val = var_info.get("step", 1)
            try:
                cur_num = float(current_val)
            except (ValueError, TypeError):
                cur_num = float(default) if default else float(min_val)
            # 判断整数/浮点
            if isinstance(min_val, int) and isinstance(step_val, int):
                env_data[key] = str(st.number_input(
                    label, min_value=int(min_val), max_value=int(max_val),
                    value=int(cur_num), step=int(step_val),
                    help=desc, key=f"cfg_{key}",
                ))
            else:
                env_data[key] = str(st.number_input(
                    label, min_value=float(min_val), max_value=float(max_val),
                    value=float(cur_num), step=float(step_val),
                    help=desc, key=f"cfg_{key}",
                ))

        else:
            # 默认文本输入
            placeholder = var_info.get("placeholder", "")
            env_data[key] = st.text_input(
                label, value=str(current_val),
                help=desc, key=f"cfg_{key}",
                placeholder=placeholder,
            )

    # 连接测试按钮（如果当前组包含引擎 host/port）
    keys_in_group = {v.get("key") for v in vars_list}
    if "SIM_ENGINE_HOST" in keys_in_group:
        st.markdown("---")
        if st.button("🔌 测试连接", type="primary", key="test_conn"):
            _test_connection(
                env_data.get("SIM_ENGINE_HOST", "localhost"),
                env_data.get("SIM_ENGINE_PORT", "8080"),
            )


def _load_env() -> dict:
    """加载 .env 文件为 dict"""
    data = OrderedDict()
    if ENV_EXAMPLE.exists():
        data.update(_parse_env_text(ENV_EXAMPLE.read_text(encoding="utf-8")))
    if ENV_FILE.exists():
        data.update(_parse_env_text(ENV_FILE.read_text(encoding="utf-8")))
    return data


def _parse_env_text(text: str) -> OrderedDict:
    """解析 .env 格式文本"""
    data = OrderedDict()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            data[key.strip()] = value.strip()
    return data


def _env_to_text(data: dict) -> str:
    """将 dict 转为 .env 格式文本
    路径类变量如果为空则注释掉，避免空值覆盖 config.py 的默认路径
    """
    # 路径类环境变量（值为空时不写入 .env，交给 config.py 使用默认路径）
    _path_keys = {
        "RAG_KNOWLEDGE_BASE_DIR", "RAG_VECTOR_STORE_DIR",
        "LOG_DIR", "REPLAY_DIR",
    }

    lines = ["# AI Agent 配置文件 (由 UI 生成)", ""]
    for key, value in data.items():
        val = str(value).strip()
        if key in _path_keys and not val:
            # 路径型变量为空 → 注释掉，使用默认路径
            lines.append(f"# {key}=")
        else:
            lines.append(f"{key}={val}")
    return "\n".join(lines)


def _save_env(data: dict):
    """保存 dict 到 .env 文件"""
    content = _env_to_text(data)
    ENV_FILE.write_text(content, encoding="utf-8")


def _reload_config():
    """热加载配置：保存 .env 后调用，立即刷新内存中的配置
    使用 importlib.reload 强制重新执行 config 模块，
    确保即使旧模块缓存中没有 reload() 函数也能正常工作
    """
    global config
    config = importlib.reload(config)
    # 如果新版 config 有 reload()，额外调用一次确保实例刷新
    if hasattr(config, "reload"):
        config.reload()


def _test_connection(host: str, port: str):
    """测试引擎连接"""
    import httpx
    url = f"http://{host}:{port}/api/health"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                st.success(f"✅ 连接成功！引擎状态: {data.get('status', 'ok')}")
                st.json(data)
            else:
                st.warning(f"⚠️ 引擎返回状态码: {resp.status_code}")
    except httpx.ConnectError:
        st.error(f"❌ 无法连接到 {url}")
    except Exception as e:
        st.error(f"❌ 连接异常: {e}")
