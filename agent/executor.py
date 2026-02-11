"""
Executor Agent - 执行器节点
负责: 解析 Tactical 的技能选择，调用实际的 Skill 函数
"""
import json
import re
from langchain_core.messages import HumanMessage
from loguru import logger

from .state import AgentState
from skills import (
    climb_and_accelerate,
    descend_and_decelerate,
    turn_to_heading,
    evade_missile,
    intercept_target,
    radar_power_on,
    radar_power_off,
    radar_search,
    activate_jammer,
    deactivate_jammer,
    radio_power_on,
    radio_power_off,
)

# 技能名称到函数的映射
SKILL_REGISTRY = {
    "climb_and_accelerate": climb_and_accelerate,
    "descend_and_decelerate": descend_and_decelerate,
    "turn_to_heading": turn_to_heading,
    "evade_missile": evade_missile,
    "intercept_target": intercept_target,
    "radar_power_on": radar_power_on,
    "radar_power_off": radar_power_off,
    "radar_search": radar_search,
    "activate_jammer": activate_jammer,
    "deactivate_jammer": deactivate_jammer,
    "radio_power_on": radio_power_on,
    "radio_power_off": radio_power_off,
}


def _extract_json(text: str) -> dict | None:
    """从 LLM 输出文本中提取 JSON 对象"""
    # 尝试匹配 ```json ... ``` 代码块
    pattern = r'```json\s*\n?(.*?)\n?\s*```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试直接解析整个文本
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试匹配 { ... } 块
    brace_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(brace_pattern, text, re.DOTALL)
    for m in reversed(matches):  # 从后往前找（最后一个通常最完整）
        try:
            return json.loads(m)
        except json.JSONDecodeError:
            continue

    return None


def executor_node(state: AgentState) -> dict:
    """Executor 节点 - 执行技能"""
    logger.info("[Executor] 开始执行技能...")

    skill_decision = state.get("selected_skill", "")
    results = []

    # 解析技能决策 JSON
    decision_data = _extract_json(skill_decision)

    if decision_data is None:
        error_msg = f"无法解析技能决策: {skill_decision[:200]}"
        logger.error(f"[Executor] {error_msg}")
        return {
            "execution_result": error_msg,
            "current_phase": "observe",
            "iteration_count": state.get("iteration_count", 0) + 1,
            "messages": [HumanMessage(content=f"[Executor] 执行失败: {error_msg}")],
        }

    skills_to_execute = decision_data.get("skills", [])
    if not skills_to_execute:
        # 尝试单技能格式
        if "skill_name" in decision_data:
            skills_to_execute = [decision_data]

    for skill_info in skills_to_execute:
        skill_name = skill_info.get("skill_name", "")
        params = skill_info.get("params", {})
        reason = skill_info.get("reason", "")

        if skill_name not in SKILL_REGISTRY:
            error = f"未知技能: {skill_name}"
            logger.warning(f"[Executor] {error}")
            results.append({"skill": skill_name, "success": False, "error": error})
            continue

        skill_func = SKILL_REGISTRY[skill_name]
        logger.info(f"[Executor] 执行技能: {skill_name}({params}) - {reason}")

        try:
            result = skill_func(**params)
            results.append({
                "skill": skill_name,
                "success": result.success,
                "description": result.description,
                "actions_count": len(result.actions_taken),
            })
            logger.info(f"[Executor] {skill_name} -> {'成功' if result.success else '失败'}: {result.description}")
        except Exception as e:
            error = f"技能执行异常: {str(e)}"
            logger.error(f"[Executor] {skill_name} -> {error}")
            results.append({"skill": skill_name, "success": False, "error": error})

    # 汇总执行结果
    total = len(results)
    success_count = sum(1 for r in results if r.get("success"))
    execution_summary = f"执行了 {total} 个技能，成功 {success_count} 个"

    for r in results:
        if r.get("success"):
            execution_summary += f"\n  - {r['skill']}: {r.get('description', '成功')}"
        else:
            execution_summary += f"\n  - {r['skill']}: 失败 - {r.get('error', r.get('description', ''))}"

    logger.info(f"[Executor] {execution_summary}")

    return {
        "execution_result": execution_summary,
        "current_phase": "observe",
        "iteration_count": state.get("iteration_count", 0) + 1,
        "messages": [HumanMessage(content=f"[Executor] {execution_summary}")],
    }
