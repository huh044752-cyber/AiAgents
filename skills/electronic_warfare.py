"""
电子战技能模块
包含干扰机操作、电子对抗等技能
"""
from loguru import logger

from .base import Skill, SkillResult
from mcp.client import get_client


def activate_jammer(unit_name: str, jammer_name: str = None) -> SkillResult:
    """开启干扰机

    开启指定单元的干扰机进行电子干扰。

    Args:
        unit_name: 单元名称
        jammer_name: 干扰机名称（可选，不指定则开启所有干扰机）
    """
    client = get_client()
    actions = []

    state = client.get(f"/api/unit/{unit_name}/state")
    if "error" in state:
        return SkillResult(success=False, description=f"无法获取单元状态: {state['error']}")

    # 查找干扰机
    if jammer_name:
        jammer = Skill.find_equipment_by_name(state, jammer_name)
        jammers = [jammer] if jammer else []
    else:
        jammers = Skill.find_equipment_by_type(state, "jammer")

    if not jammers:
        return SkillResult(success=False, description=f"{unit_name} 没有装备干扰机")

    activated = []
    for jammer in jammers:
        jname = jammer.get("entity_name", "")
        if jammer.get("status") == "ON":
            activated.append(jname)
            continue

        result = client.post(
            f"/api/unit/{unit_name}/equipment/{jname}/control",
            {"power": True},
        )
        actions.append({
            "tool": "control_equipment",
            "params": {"unit": unit_name, "equipment": jname, "power": True},
            "result": result.get("result", "unknown"),
        })
        if result.get("result") == "success":
            activated.append(jname)

    description = f"{unit_name} 干扰机开启: {', '.join(activated)}"
    logger.info(f"[Skill] {description}")

    return SkillResult(
        success=len(activated) > 0,
        description=description,
        actions_taken=actions,
        data={"activated_jammers": activated},
    )


def deactivate_jammer(unit_name: str, jammer_name: str = None) -> SkillResult:
    """关闭干扰机（节约能源/降低暴露）

    Args:
        unit_name: 单元名称
        jammer_name: 干扰机名称（可选）
    """
    client = get_client()
    actions = []

    state = client.get(f"/api/unit/{unit_name}/state")
    if "error" in state:
        return SkillResult(success=False, description=f"无法获取单元状态: {state['error']}")

    if jammer_name:
        jammer = Skill.find_equipment_by_name(state, jammer_name)
        jammers = [jammer] if jammer else []
    else:
        jammers = Skill.find_equipment_by_type(state, "jammer")

    if not jammers:
        return SkillResult(success=False, description=f"{unit_name} 没有装备干扰机")

    deactivated = []
    for jammer in jammers:
        jname = jammer.get("entity_name", "")
        if jammer.get("status") == "OFF":
            deactivated.append(jname)
            continue

        result = client.post(
            f"/api/unit/{unit_name}/equipment/{jname}/control",
            {"power": False},
        )
        actions.append({
            "tool": "control_equipment",
            "params": {"unit": unit_name, "equipment": jname, "power": False},
            "result": result.get("result", "unknown"),
        })
        if result.get("result") == "success":
            deactivated.append(jname)

    description = f"{unit_name} 干扰机关闭: {', '.join(deactivated)}"
    logger.info(f"[Skill] {description}")

    return SkillResult(
        success=len(deactivated) > 0,
        description=description,
        actions_taken=actions,
        data={"deactivated_jammers": deactivated},
    )
