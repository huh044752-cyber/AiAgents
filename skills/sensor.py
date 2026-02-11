"""
传感器操作技能模块
包含雷达、光电等传感器的操作技能
"""
from loguru import logger

from .base import Skill, SkillResult
from mcp.client import get_client


def radar_power_on(unit_name: str, radar_name: str = None) -> SkillResult:
    """雷达开机技能

    开启指定单元的雷达。如果未指定雷达名称，则开启第一个找到的雷达。

    Args:
        unit_name: 单元名称
        radar_name: 雷达名称（可选，不指定则开启第一个雷达）
    """
    client = get_client()
    actions = []

    # 获取单元状态
    state = client.get(f"/api/unit/{unit_name}/state")
    if "error" in state:
        return SkillResult(success=False, description=f"无法获取单元状态: {state['error']}")

    # 查找雷达
    if radar_name:
        radar = Skill.find_equipment_by_name(state, radar_name)
        if radar is None:
            return SkillResult(success=False, description=f"未找到雷达: {radar_name}")
        radars = [radar]
    else:
        radars = Skill.find_equipment_by_type(state, "radar")
        if not radars:
            return SkillResult(success=False, description=f"{unit_name} 没有装备雷达")

    # 开启雷达
    activated = []
    for radar in radars:
        rname = radar.get("entity_name", "")
        if radar.get("status") == "ON":
            activated.append(rname)
            continue

        result = client.post(
            f"/api/unit/{unit_name}/equipment/{rname}/control",
            {"power": True},
        )
        actions.append({
            "tool": "control_equipment",
            "params": {"unit": unit_name, "equipment": rname, "power": True},
            "result": result.get("result", "unknown"),
        })
        if result.get("result") == "success":
            activated.append(rname)

    description = f"{unit_name} 雷达开机: {', '.join(activated)}"
    logger.info(f"[Skill] {description}")

    return SkillResult(
        success=len(activated) > 0,
        description=description,
        actions_taken=actions,
        data={"activated_radars": activated},
    )


def radar_power_off(unit_name: str, radar_name: str = None) -> SkillResult:
    """雷达关机技能（静默飞行，降低被发现概率）

    Args:
        unit_name: 单元名称
        radar_name: 雷达名称（可选）
    """
    client = get_client()
    actions = []

    state = client.get(f"/api/unit/{unit_name}/state")
    if "error" in state:
        return SkillResult(success=False, description=f"无法获取单元状态: {state['error']}")

    if radar_name:
        radar = Skill.find_equipment_by_name(state, radar_name)
        radars = [radar] if radar else []
    else:
        radars = Skill.find_equipment_by_type(state, "radar")

    if not radars:
        return SkillResult(success=False, description=f"{unit_name} 没有装备雷达")

    deactivated = []
    for radar in radars:
        rname = radar.get("entity_name", "")
        if radar.get("status") == "OFF":
            deactivated.append(rname)
            continue

        result = client.post(
            f"/api/unit/{unit_name}/equipment/{rname}/control",
            {"power": False},
        )
        actions.append({
            "tool": "control_equipment",
            "params": {"unit": unit_name, "equipment": rname, "power": False},
            "result": result.get("result", "unknown"),
        })
        if result.get("result") == "success":
            deactivated.append(rname)

    description = f"{unit_name} 雷达关机（静默模式）: {', '.join(deactivated)}"
    logger.info(f"[Skill] {description}")

    return SkillResult(
        success=len(deactivated) > 0,
        description=description,
        actions_taken=actions,
        data={"deactivated_radars": deactivated},
    )


def radar_search(unit_name: str, radar_name: str = None) -> SkillResult:
    """雷达搜索技能

    确保雷达开机并查询当前探测结果。

    Args:
        unit_name: 单元名称
        radar_name: 雷达名称（可选）
    """
    client = get_client()
    actions = []

    state = client.get(f"/api/unit/{unit_name}/state")
    if "error" in state:
        return SkillResult(success=False, description=f"无法获取单元状态: {state['error']}")

    # 查找雷达
    if radar_name:
        radar = Skill.find_equipment_by_name(state, radar_name)
        if radar is None:
            return SkillResult(success=False, description=f"未找到雷达: {radar_name}")
    else:
        radars = Skill.find_equipment_by_type(state, "radar")
        if not radars:
            return SkillResult(success=False, description=f"{unit_name} 没有装备雷达")
        radar = radars[0]

    rname = radar.get("entity_name", "")

    # 确保雷达开机
    if radar.get("status") != "ON":
        power_result = client.post(
            f"/api/unit/{unit_name}/equipment/{rname}/control",
            {"power": True},
        )
        actions.append({
            "tool": "control_equipment",
            "params": {"unit": unit_name, "equipment": rname, "power": True},
            "result": power_result.get("result", "unknown"),
        })

    # 查询雷达状态
    query_result = client.get(f"/api/unit/{unit_name}/equipment/{rname}/query")
    actions.append({
        "tool": "query_equipment",
        "params": {"unit": unit_name, "equipment": rname},
        "result": "queried",
    })

    description = f"{unit_name} 雷达 {rname} 执行搜索"
    logger.info(f"[Skill] {description}")

    return SkillResult(
        success=True,
        description=description,
        actions_taken=actions,
        data={"radar_name": rname, "radar_state": query_result},
    )
