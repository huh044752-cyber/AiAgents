"""
Tactical Agent - 战术决策节点
负责: 根据战术意图选择合适的 Skill 并确定参数
技能列表从 SKILL_REGISTRY 动态生成，不在此处写死
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from .state import AgentState


TACTICAL_SYSTEM_PROMPT_TEMPLATE = """你是一名战术AI参谋。你的职责是根据指挥官的战术意图，选择最合适的战术技能（Skill）并确定参数。

## 可用技能列表

{skill_list}

## 输出格式
你必须以如下JSON格式输出（可以选择多个技能顺序执行）：
```json
{{
    "analysis": "对当前态势的战术分析",
    "skills": [
        {{
            "skill_name": "技能名称",
            "params": {{"参数名": "参数值"}},
            "reason": "选择此技能的理由"
        }}
    ]
}}
```

## 约束
- 只选择上述列表中的技能
- 参数必须基于当前态势中的实际数据（单元名称、位置等）
- 考虑执行顺序的合理性（如先开雷达再截击）
"""


def _build_skill_list_prompt() -> str:
    """从 SKILL_REGISTRY 动态生成技能列表文本，保持与注册表同步"""
    from skills import SKILL_REGISTRY

    # 按 category 分组
    categories: dict[str, list] = {}
    for name, info in SKILL_REGISTRY.items():
        cat = info.get("category", "other")
        categories.setdefault(cat, []).append((name, info))

    category_labels = {
        "maneuver": "机动技能",
        "flight": "飞行控制",
        "sensor": "传感器",
        "ew": "电子战",
        "comm": "通信",
        "weapon": "武器",
    }

    parts = []
    idx = 1
    for cat, items in categories.items():
        label = category_labels.get(cat, cat)
        parts.append(f"### {label}")
        for name, info in items:
            params_str = ", ".join(info.get("params", []))
            parts.append(f"{idx}. **{name}** - {info['description']}")
            parts.append(f"   参数: {params_str}")
            idx += 1
        parts.append("")

    return "\n".join(parts)


def tactical_node(state: AgentState, llm) -> dict:
    """Tactical 节点 - 技能选择和参数确定"""
    logger.info("[Tactical] 开始战术决策...")

    tactical_intent = state.get("tactical_intent", "")
    world_state_summary = state.get("world_state_summary", "")

    # 动态生成技能列表
    skill_list_text = _build_skill_list_prompt()
    system_prompt = TACTICAL_SYSTEM_PROMPT_TEMPLATE.format(skill_list=skill_list_text)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""## 指挥官战术意图
{tactical_intent}

## 当前战场态势
{world_state_summary}

请选择合适的技能并确定参数。"""),
    ]

    response = llm.invoke(messages)
    skill_decision = response.content

    logger.info("[Tactical] 技能选择完成")

    return {
        "selected_skill": skill_decision,
        "current_phase": "executor",
        "messages": [HumanMessage(content=f"[Tactical] {skill_decision}")],
    }
