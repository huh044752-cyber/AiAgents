"""
知识库管理页面 - 查看、编辑、新增知识文档
分类体系、模板均从外部配置加载
"""
import streamlit as st
import json
from pathlib import Path
from collections import OrderedDict
import sys

import config

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from styles import (
    _doc_categories, get_category_label, categorize_doc,
    load_doc_template, load_json_template,
    get_ui_text, get_ui_param,
)


def _knowledge_dir() -> Path:
    """动态获取知识库目录路径（跟随 config 热加载）

    兼容两种情况：
    - 新版 config: 已将路径解析为绝对路径
    - 旧进程 / 异常配置: env 里是空字符串或 '.'，这里再做一次兜底
    """
    raw = getattr(config.rag, "KNOWLEDGE_BASE_DIR", "") or ""
    raw = str(raw).strip()

    # 优先使用 config 提供的非空、非 '.' 路径
    if raw and raw not in {".", "./", ".\\"}:
        p = Path(raw)
        if p.is_absolute():
            return p
        # 相对路径视为相对于项目根目录
        project_root = getattr(config, "PROJECT_ROOT", Path(__file__).resolve().parent.parent)
        return (Path(project_root) / p).resolve()

    # 兜底：使用项目根目录下的默认 knowledge_base 目录
    project_root = getattr(config, "PROJECT_ROOT", Path(__file__).resolve().parent.parent)
    return (Path(project_root) / "rag" / "knowledge_base").resolve()


def render():
    st.markdown(get_ui_text("knowledge", "page_title", "# 📚 知识库管理"))
    st.markdown(get_ui_text("knowledge", "page_desc", "管理 RAG 战术知识库文档。"))

    KNOWLEDGE_DIR = _knowledge_dir()
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    # ── 顶部操作栏 ──
    col_path, col_rebuild, col_new = st.columns([3, 1, 1])
    with col_path:
        st.markdown(f"📁 知识库路径: `{KNOWLEDGE_DIR}`")
    with col_rebuild:
        if st.button("🔄 重建向量库", use_container_width=True, type="primary"):
            with st.spinner("正在重建向量库..."):
                try:
                    from rag import get_rag
                    rag = get_rag()
                    rag.rebuild()
                    st.success("✅ 向量库重建完成！")
                except Exception as e:
                    st.error(f"重建失败: {e}")
    with col_new:
        if st.button("➕ 新建文档", use_container_width=True):
            st.session_state.show_new_doc = True

    st.markdown("---")

    # ── 新建文档表单：先选类型 ──
    if st.session_state.get("show_new_doc", False):
        with st.expander("📝 新建知识文档", expanded=True):
            # 从配置热加载分类（general 放最后）
            _all_cats = _doc_categories()
            cat_options = OrderedDict()
            for k, v in _all_cats.items():
                if k != "general":
                    cat_options[k] = v
            cat_options["general"] = _all_cats.get("general", {"label": "通用文档", "icon": "📄"})

            cat_keys = list(cat_options.keys())
            cat_labels_list = [f"{v.get('icon', '📄')} {v.get('label', k)}" for k, v in cat_options.items()]

            col_cat, col_fmt = st.columns([3, 1])
            with col_cat:
                selected_idx = st.selectbox(
                    "选择文档分类",
                    range(len(cat_keys)),
                    format_func=lambda i: cat_labels_list[i],
                    help="文档将自动按所选分类命名并归组",
                )
            with col_fmt:
                doc_format = st.selectbox("文件格式", [".md", ".json"], index=0)

            selected_cat_key = cat_keys[selected_idx]
            selected_cat = cat_options[selected_cat_key]

            # 自动生成文件名前缀
            existing_files = list(KNOWLEDGE_DIR.glob("*"))
            next_num = len(existing_files) + 1
            auto_prefix = f"{next_num:02d}_{selected_cat.get('prefix', selected_cat_key)}"

            placeholder = get_ui_text("knowledge", "new_doc_title_placeholder", "例如: 超视距空战攻防原则")
            col_name, col_preview = st.columns([3, 2])
            with col_name:
                doc_title = st.text_input(
                    "文档标题（简要描述）",
                    placeholder=placeholder,
                    help="输入简短标题，系统自动生成完整文件名",
                )
            with col_preview:
                if doc_title:
                    final_name = f"{auto_prefix}_{doc_title}{doc_format}"
                else:
                    final_name = f"{auto_prefix}{doc_format}"
                st.markdown(f"**生成文件名:** `{final_name}`")

            # 文档模板（从外部模板文件加载）
            if doc_format == ".json":
                template = load_json_template(selected_cat_key, doc_title)
            else:
                template = load_doc_template(selected_cat_key, doc_title)

            new_content = st.text_area(
                "文档内容",
                value=template,
                height=300,
                help="支持 Markdown 格式，系统会自动分块索引",
            )

            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("💾 保存新文档", use_container_width=True, type="primary"):
                    if doc_title and new_content.strip():
                        filepath = KNOWLEDGE_DIR / final_name
                        filepath.write_text(new_content, encoding="utf-8")
                        st.success(f"✅ 已创建: {final_name}")
                        st.session_state.show_new_doc = False
                        st.rerun()
                    else:
                        st.warning("标题和内容不能为空")
            with col_cancel:
                if st.button("取消", use_container_width=True):
                    st.session_state.show_new_doc = False
                    st.rerun()

    # ── 加载并分类文档 ──
    md_files = sorted(KNOWLEDGE_DIR.glob("*.md"))
    json_files = sorted(KNOWLEDGE_DIR.glob("*.json"))
    all_files = md_files + json_files

    if not all_files:
        st.info("知识库为空，点击上方【新建文档】添加知识。")
        return

    # 按分类归组
    categorized = OrderedDict()
    for f in all_files:
        cat = categorize_doc(f.name)
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(f)

    # ── 统计卡片 ──
    stat_cols = st.columns(min(len(categorized), 6))
    for i, (cat, files) in enumerate(categorized.items()):
        col_idx = i % len(stat_cols)
        with stat_cols[col_idx]:
            label = get_category_label(cat)
            st.metric(label, f"{len(files)} 篇")

    st.markdown("---")

    # ── 按分类展示文档 ──
    editor_height = get_ui_param("knowledge", "editor_height", 400)

    _cats_display = _doc_categories()
    for cat_key, files in categorized.items():
        cat_info = _cats_display.get(cat_key, _cats_display.get("general", {}))
        icon = cat_info.get("icon", "📄")
        label = cat_info.get("label", cat_key)

        st.markdown(
            f'<div class="category-header">'
            f'<h4>{icon} {label} ({len(files)} 篇)</h4>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for filepath in files:
            with st.expander(f"{icon} {filepath.name}", expanded=False):
                content = filepath.read_text(encoding="utf-8")

                edited = st.text_area(
                    f"编辑 {filepath.name}",
                    value=content,
                    height=editor_height,
                    key=f"editor_{filepath.name}",
                    label_visibility="collapsed",
                )

                col_s, col_d, col_info = st.columns([1, 1, 3])
                with col_s:
                    if st.button("💾 保存", key=f"save_{filepath.name}", use_container_width=True, type="primary"):
                        filepath.write_text(edited, encoding="utf-8")
                        st.success(f"✅ 已保存 {filepath.name}")
                with col_d:
                    if st.button("🗑️ 删除", key=f"del_{filepath.name}", use_container_width=True):
                        filepath.unlink()
                        st.warning(f"已删除 {filepath.name}")
                        st.rerun()
                with col_info:
                    size_kb = filepath.stat().st_size / 1024
                    lines = content.count("\n") + 1
                    st.caption(f"分类: {label} · 大小: {size_kb:.1f}KB · {lines} 行")
