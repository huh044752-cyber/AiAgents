"""
Commander Agent - 指挥官节点
负责: 任务理解、态势分析、战术意图生成
集成 RAG 战术知识检索，辅助决策
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from .state import AgentState
from mcp.tools import get_world_state
from rag import get_rag
import config


COMMANDER_SYSTEM_PROMPT = """你是一名经验丰富的空战指挥官AI。你的职责是：

1. **理解任务**: 分析下达的任务指令，明确作战目标
2. **态势分析**: 基于当前世界态势数据，评估敌我态势
3. **知识参考**: 参考战术知识库中的条令、手册和历史案例
4. **生成战术意图**: 输出清晰的战术意图，指导后续战术决策

你只负责决策层面，不直接执行任何控制操作。

## 输出格式
你必须以如下JSON格式输出战术意图：
```json
{
    "mission_understanding": "对任务的理解",
    "situation_assessment": "态势评估",
    "knowledge_reference": "参考的战术知识要点",
    "tactical_intent": "战术意图描述",
    "priority_targets": ["优先目标列表"],
    "constraints": ["行动约束"],
    "recommended_approach": "建议采用的战术方案",
    "phase_plan": ["阶段1:...", "阶段2:...", "阶段3:..."]
}
```

## 约束
- 你不能直接修改任何物理状态
- 你只能通过MCP工具获取态势信息
- 所有决策必须基于可观察的态势数据
- 参考战术知识但灵活应用，不要生搬硬套
"""


def commander_node(state: AgentState, llm) -> dict:
    """Commander 节点 - 任务理解和战术意图生成"""
    logger.info("[Commander] 开始分析任务...")

    # 获取当前世界态势
    world_state = get_world_state.invoke({})
    
    # 构建态势摘要
    units = world_state.get("units", [])
    sim_time = world_state.get("sim_time", 0)
    
    state_summary_parts = [f"仿真时间: {sim_time}"]
    for unit in units:
        name = unit.get("unit_name", "unknown")
        side = unit.get("forceside", "unknown")
        pos = unit.get("position", {})
        speed = unit.get("speed", 0)
        alive = unit.get("alive", False)
        active = unit.get("active", False)
        equip_count = len(unit.get("equipment", []))

        status = "存活/激活" if alive and active else ("存活/未激活" if alive else "已摧毁")
        state_summary_parts.append(
            f"  - {name} [{side}] 状态:{status} "
            f"位置:({pos.get('latitude', 0):.4f}, {pos.get('longitude', 0):.4f}, {pos.get('altitude', 0):.0f}m) "
            f"速度:{speed:.1f}m/s 装备:{equip_count}件"
        )

    world_state_summary = "\n".join(state_summary_parts)

    # RAG 检索相关战术知识
    rag = get_rag()
    tactical_knowledge = rag.get_context_for_agent(state["task"])
    logger.info(f"[Commander] RAG 检索到 {len(tactical_knowledge)} 字符战术知识")

    # 构造 LLM 输入
    messages = [
        SystemMessage(content=COMMANDER_SYSTEM_PROMPT),
        HumanMessage(content=f"""## 当前任务
{state['task']}

## 当前战场态势
{world_state_summary}

## 相关战术知识（来自知识库）
{tactical_knowledge}

请分析态势，参考战术知识，输出战术意图。"""),
    ]

    # 调用 LLM
    response = llm.invoke(messages)
    tactical_intent = response.content

    logger.info(f"[Commander] 战术意图已生成")

    return {
        "tactical_intent": tactical_intent,
        "world_state_summary": world_state_summary,
        "current_phase": "tactical",
        "messages": [HumanMessage(content=f"[Commander] {tactical_intent}")],
    }
