"""
LangGraph 主图定义
编排 Commander -> Tactical -> Executor -> Observe 的循环流程
"""
import os
from functools import partial
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from loguru import logger

from .state import AgentState
from .commander import commander_node
from .tactical import tactical_node
from .executor import executor_node

import config


def _create_llm():
    """创建通义千问 LLM 实例"""
    from langchain_community.chat_models import ChatTongyi

    # 确保 API Key 设置
    if config.llm.DASHSCOPE_API_KEY:
        os.environ["DASHSCOPE_API_KEY"] = config.llm.DASHSCOPE_API_KEY

    llm = ChatTongyi(
        model=config.llm.MODEL_NAME,
        temperature=config.llm.TEMPERATURE,
        top_p=config.llm.TOP_P,
    )
    return llm


def _observe_node(state: AgentState, llm) -> dict:
    """
    Observe 节点 - 观察执行结果，决定是否继续
    """
    logger.info("[Observe] 评估执行结果...")

    execution_result = state.get("execution_result", "")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", config.agent.MAX_ITERATIONS)

    # 达到最大迭代次数，强制结束
    if iteration_count >= max_iterations:
        logger.warning(f"[Observe] 达到最大迭代次数 {max_iterations}，强制结束")
        return {
            "should_continue": False,
            "current_phase": "done",
            "messages": [HumanMessage(content=f"[Observe] 达到最大迭代次数，任务结束")],
        }

    # 让 LLM 判断是否需要继续
    observe_prompt = f"""你是任务观察者。根据以下执行结果，判断任务是否已完成。

## 原始任务
{state.get('task', '')}

## 战术意图
{state.get('tactical_intent', '')}

## 最近执行结果
{execution_result}

## 当前迭代次数
{iteration_count}/{max_iterations}

请判断:
1. 如果任务目标已达成或当前步骤执行成功且不需要后续操作，回复 JSON: {{"continue": false, "reason": "完成原因"}}
2. 如果需要继续执行（如需要调整参数、切换战术等），回复 JSON: {{"continue": true, "reason": "继续原因", "next_action": "建议的下一步"}}
"""

    messages = [HumanMessage(content=observe_prompt)]
    response = llm.invoke(messages)

    # 解析 LLM 响应
    from .executor import _extract_json
    decision = _extract_json(response.content)

    if decision and decision.get("continue", False):
        reason = decision.get("reason", "需要继续执行")
        logger.info(f"[Observe] 继续执行: {reason}")
        return {
            "should_continue": True,
            "current_phase": "tactical",  # 回到战术决策
            "messages": [HumanMessage(content=f"[Observe] 继续: {reason}")],
        }
    else:
        reason = decision.get("reason", "任务已完成") if decision else "任务已完成"
        logger.info(f"[Observe] 任务结束: {reason}")
        return {
            "should_continue": False,
            "current_phase": "done",
            "messages": [HumanMessage(content=f"[Observe] 完成: {reason}")],
        }


def _route_after_observe(state: AgentState) -> str:
    """Observe 之后的路由决策"""
    if state.get("should_continue", False):
        return "tactical"
    return END


def create_agent_graph():
    """创建 LangGraph Agent 图"""
    llm = _create_llm()

    # 创建状态图
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("commander", partial(commander_node, llm=llm))
    graph.add_node("tactical", partial(tactical_node, llm=llm))
    graph.add_node("executor", executor_node)
    graph.add_node("observe", partial(_observe_node, llm=llm))

    # 定义边（流程）
    graph.set_entry_point("commander")
    graph.add_edge("commander", "tactical")
    graph.add_edge("tactical", "executor")
    graph.add_edge("executor", "observe")

    # 条件边: observe 之后根据结果决定继续还是结束
    graph.add_conditional_edges("observe", _route_after_observe)

    # 编译图
    compiled = graph.compile()
    logger.info("[Graph] Agent 图编译完成")

    return compiled


def run_agent(task: str, max_iterations: int = None) -> dict:
    """
    运行 Agent 执行任务

    Args:
        task: 任务描述
        max_iterations: 最大迭代次数

    Returns:
        最终状态字典
    """
    if max_iterations is None:
        max_iterations = config.agent.MAX_ITERATIONS

    graph = create_agent_graph()

    # 初始状态
    initial_state = {
        "messages": [],
        "task": task,
        "tactical_intent": None,
        "world_state_summary": None,
        "selected_skill": None,
        "skill_params": None,
        "execution_result": None,
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "should_continue": True,
        "current_phase": "commander",
    }

    logger.info(f"[Agent] 开始执行任务: {task}")
    logger.info(f"[Agent] 最大迭代次数: {max_iterations}")

    # 运行图
    final_state = None
    for step in graph.stream(initial_state):
        for node_name, node_state in step.items():
            logger.debug(f"[Agent] 节点 {node_name} 执行完毕")
            final_state = node_state

    logger.info("[Agent] 任务执行完毕")

    # 保存回放记录
    from utils.replay import get_recorder
    get_recorder().save()

    return final_state
