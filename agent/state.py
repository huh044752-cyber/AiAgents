"""
Agent 状态定义
LangGraph 中所有节点共享的状态结构
"""
from typing import Annotated, TypedDict, Optional
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph Agent 全局状态"""

    # 消息历史（自动累积）
    messages: Annotated[list, add_messages]

    # 原始任务指令
    task: str

    # Commander 输出 - 战术意图
    tactical_intent: Optional[str]

    # 当前世界态势摘要
    world_state_summary: Optional[str]

    # Tactical 选择的 Skill 名称及参数
    selected_skill: Optional[str]
    skill_params: Optional[dict]

    # Executor 执行结果
    execution_result: Optional[str]

    # 控制流
    iteration_count: int
    max_iterations: int
    should_continue: bool
    current_phase: str  # "commander" / "tactical" / "executor" / "observe" / "done"
