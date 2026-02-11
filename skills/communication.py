"""
通信技能模块
包含通信设备的操作技能
"""
from loguru import logger

from .base import Skill, SkillResult
from mcp.client import get_client


def radio_power_on(unit_name: str, radio_name: str = None) -> SkillResult:
    """通信设备开机

    Args:
        unit_name: 单元名称
        radio_name: 通信设备名称（可选）
    """
    client = get_client()
    actions = []

    state = client.get(f"/api/unit/{unit_name}/state")
    if "error" in state:
        return SkillResult(success=False, description=f"无法获取单元状态: {state['error']}")

    if radio_name:
        radio = Skill.find_equipment_by_name(state, radio_name)
        radios = [radio] if radio else []
    else:
        radios = Skill.find_equipment_by_type(state, "communication")

    if not radios:
        return SkillResult(success=False, description=f"{unit_name} 没有装备通信设备")

    activated = []
    for radio in radios:
        rname = radio.get("entity_name", "")
        if radio.get("status") == "ON":
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

    description = f"{unit_name} 通信设备开机: {', '.join(activated)}"
    logger.info(f"[Skill] {description}")

    return SkillResult(
        success=len(activated) > 0,
        description=description,
        actions_taken=actions,
        data={"activated_radios": activated},
    )


def radio_power_off(unit_name: str, radio_name: str = None) -> SkillResult:
    """通信设备关机（通信静默）

    Args:
        unit_name: 单元名称
        radio_name: 通信设备名称（可选）
    """
    client = get_client()
    actions = []

    state = client.get(f"/api/unit/{unit_name}/state")
    if "error" in state:
        return SkillResult(success=False, description=f"无法获取单元状态: {state['error']}")

    if radio_name:
        radio = Skill.find_equipment_by_name(state, radio_name)
        radios = [radio] if radio else []
    else:
        radios = Skill.find_equipment_by_type(state, "communication")

    if not radios:
        return SkillResult(success=False, description=f"{unit_name} 没有装备通信设备")

    deactivated = []
    for radio in radios:
        rname = radio.get("entity_name", "")
        if radio.get("status") == "OFF":
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

    description = f"{unit_name} 通信设备关机（静默模式）: {', '.join(deactivated)}"
    logger.info(f"[Skill] {description}")

    return SkillResult(
        success=len(deactivated) > 0,
        description=description,
        actions_taken=actions,
        data={"deactivated_radios": deactivated},
    )
