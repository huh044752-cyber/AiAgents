"""
机动技能模块
包含飞行器机动相关的战术技能
"""
import math
from loguru import logger

from .base import Skill, SkillResult
from mcp.client import get_client


def climb_and_accelerate(
    unit_name: str,
    target_altitude: float,
    target_speed: float,
    pitch_angle: float = 15.0,
) -> SkillResult:
    """爬升加速技能

    使飞行器以指定俯仰角爬升到目标高度并加速到目标速度。

    Args:
        unit_name: 单元名称
        target_altitude: 目标高度（米）
        target_speed: 目标速度（m/s）
        pitch_angle: 爬升俯仰角（度），默认15度

    Returns:
        SkillResult 执行结果
    """
    client = get_client()
    actions = []

    # 获取当前状态
    state = client.get(f"/api/unit/{unit_name}/state")
    if "error" in state:
        return SkillResult(success=False, description=f"无法获取单元状态: {state['error']}")

    current_alt = state.get("position", {}).get("altitude", 0)
    current_speed = state.get("speed", 0)

    # 限幅
    pitch_angle = Skill.clamp(pitch_angle, 0, 45)
    target_speed = Skill.clamp(target_speed, 0, 1000)  # 最大速度限制
    target_altitude = Skill.clamp(target_altitude, 0, 30000)  # 最大高度限制

    # 发送控制指令
    alter_data = {
        "altitude": target_altitude,
        "speed": target_speed,
        "pitch": pitch_angle,
    }
    result = client.post(f"/api/unit/{unit_name}/alter", alter_data)
    actions.append({"tool": "alter_unit", "params": alter_data, "result": result.get("result", "unknown")})

    description = (
        f"{unit_name} 执行爬升加速: "
        f"高度 {current_alt:.0f}m -> {target_altitude:.0f}m, "
        f"速度 {current_speed:.1f}m/s -> {target_speed:.1f}m/s, "
        f"俯仰角 {pitch_angle:.1f}°"
    )
    logger.info(f"[Skill] {description}")

    return SkillResult(
        success=result.get("result") == "success",
        description=description,
        actions_taken=actions,
        data={"target_altitude": target_altitude, "target_speed": target_speed},
    )


def descend_and_decelerate(
    unit_name: str,
    target_altitude: float,
    target_speed: float,
    pitch_angle: float = -10.0,
) -> SkillResult:
    """下降减速技能

    Args:
        unit_name: 单元名称
        target_altitude: 目标高度（米）
        target_speed: 目标速度（m/s）
        pitch_angle: 下降俯仰角（度），默认-10度
    """
    client = get_client()
    actions = []

    state = client.get(f"/api/unit/{unit_name}/state")
    if "error" in state:
        return SkillResult(success=False, description=f"无法获取单元状态: {state['error']}")

    pitch_angle = Skill.clamp(pitch_angle, -45, 0)
    target_speed = Skill.clamp(target_speed, 0, 1000)
    target_altitude = Skill.clamp(target_altitude, 0, 30000)

    alter_data = {
        "altitude": target_altitude,
        "speed": target_speed,
        "pitch": pitch_angle,
    }
    result = client.post(f"/api/unit/{unit_name}/alter", alter_data)
    actions.append({"tool": "alter_unit", "params": alter_data, "result": result.get("result", "unknown")})

    description = f"{unit_name} 执行下降减速: 目标高度 {target_altitude:.0f}m, 目标速度 {target_speed:.1f}m/s"
    logger.info(f"[Skill] {description}")

    return SkillResult(
        success=result.get("result") == "success",
        description=description,
        actions_taken=actions,
    )


def turn_to_heading(unit_name: str, target_heading: float) -> SkillResult:
    """转向技能

    使飞行器转向到指定航向。

    Args:
        unit_name: 单元名称
        target_heading: 目标航向（度，0=北，顺时针）
    """
    client = get_client()
    actions = []

    state = client.get(f"/api/unit/{unit_name}/state")
    if "error" in state:
        return SkillResult(success=False, description=f"无法获取单元状态: {state['error']}")

    current_heading = state.get("orientation", {}).get("heading", 0)
    target_heading = target_heading % 360

    alter_data = {"heading": target_heading}
    result = client.post(f"/api/unit/{unit_name}/alter", alter_data)
    actions.append({"tool": "alter_unit", "params": alter_data, "result": result.get("result", "unknown")})

    description = f"{unit_name} 转向: {current_heading:.1f}° -> {target_heading:.1f}°"
    logger.info(f"[Skill] {description}")

    return SkillResult(
        success=result.get("result") == "success",
        description=description,
        actions_taken=actions,
    )


def evade_missile(unit_name: str, threat_bearing: float = None) -> SkillResult:
    """导弹规避技能

    执行规避机动：急转 + 下降 + 释放干扰（如果有干扰机）。

    Args:
        unit_name: 单元名称
        threat_bearing: 威胁来袭方位角（度）。如果提供，将背向威胁方向转向。
    """
    client = get_client()
    actions = []

    # 获取当前状态
    state = client.get(f"/api/unit/{unit_name}/state")
    if "error" in state:
        return SkillResult(success=False, description=f"无法获取单元状态: {state['error']}")

    current_heading = state.get("orientation", {}).get("heading", 0)
    current_alt = state.get("position", {}).get("altitude", 5000)
    current_speed = state.get("speed", 200)

    # 计算规避航向（背向威胁 +/- 随机偏移以增加不可预测性）
    if threat_bearing is not None:
        evade_heading = (threat_bearing + 150) % 360  # 近似背向，略偏
    else:
        evade_heading = (current_heading + 90) % 360  # 无威胁信息则横转

    # 下降高度（紧急规避）
    evade_alt = max(current_alt - 1000, 500)  # 至少保持500米
    evade_speed = min(current_speed * 1.2, 800)  # 加速但不超限

    # 执行急转下降
    alter_data = {
        "heading": evade_heading,
        "altitude": evade_alt,
        "speed": evade_speed,
        "pitch": -20,  # 急降
        "roll": 60,  # 大角度滚转
    }
    result = client.post(f"/api/unit/{unit_name}/alter", alter_data)
    actions.append({"tool": "alter_unit", "params": alter_data, "result": result.get("result", "unknown")})

    # 开启干扰机（如果有的话）
    jammers = Skill.find_equipment_by_type(state, "jammer")
    for jammer in jammers:
        jammer_name = jammer.get("entity_name", "")
        if jammer.get("status") != "ON" and jammer_name:
            jammer_result = client.post(
                f"/api/unit/{unit_name}/equipment/{jammer_name}/control",
                {"power": True},
            )
            actions.append({
                "tool": "control_equipment",
                "params": {"equipment": jammer_name, "power": True},
                "result": jammer_result.get("result", "unknown"),
            })

    description = (
        f"{unit_name} 执行导弹规避: "
        f"航向 {current_heading:.1f}° -> {evade_heading:.1f}°, "
        f"高度 {current_alt:.0f}m -> {evade_alt:.0f}m, "
        f"速度 -> {evade_speed:.1f}m/s, "
        f"干扰机已激活 {len(jammers)} 部"
    )
    logger.info(f"[Skill] {description}")

    return SkillResult(
        success=True,
        description=description,
        actions_taken=actions,
        data={"evade_heading": evade_heading, "jammers_activated": len(jammers)},
    )


def intercept_target(
    unit_name: str,
    target_lat: float,
    target_lon: float,
    target_alt: float,
    intercept_speed: float = 400.0,
) -> SkillResult:
    """截击目标技能

    计算截击航向并加速飞向目标。

    Args:
        unit_name: 单元名称
        target_lat: 目标纬度
        target_lon: 目标经度
        target_alt: 目标高度
        intercept_speed: 截击速度（m/s）
    """
    client = get_client()
    actions = []

    state = client.get(f"/api/unit/{unit_name}/state")
    if "error" in state:
        return SkillResult(success=False, description=f"无法获取单元状态: {state['error']}")

    my_lat = state.get("position", {}).get("latitude", 0)
    my_lon = state.get("position", {}).get("longitude", 0)

    # 计算截击航向
    intercept_heading = Skill.calculate_bearing(my_lat, my_lon, target_lat, target_lon)
    distance = Skill.calculate_distance(my_lat, my_lon, target_lat, target_lon)

    # 限幅
    intercept_speed = Skill.clamp(intercept_speed, 100, 800)

    # 执行截击
    alter_data = {
        "heading": intercept_heading,
        "altitude": target_alt,
        "speed": intercept_speed,
    }
    result = client.post(f"/api/unit/{unit_name}/alter", alter_data)
    actions.append({"tool": "alter_unit", "params": alter_data, "result": result.get("result", "unknown")})

    # 开启雷达
    radars = Skill.find_equipment_by_type(state, "radar")
    for radar in radars:
        radar_name = radar.get("entity_name", "")
        if radar.get("status") != "ON" and radar_name:
            radar_result = client.post(
                f"/api/unit/{unit_name}/equipment/{radar_name}/control",
                {"power": True},
            )
            actions.append({
                "tool": "control_equipment",
                "params": {"equipment": radar_name, "power": True},
                "result": radar_result.get("result", "unknown"),
            })

    description = (
        f"{unit_name} 执行截击: "
        f"航向 {intercept_heading:.1f}°, "
        f"距离 {distance / 1000:.1f}km, "
        f"速度 {intercept_speed:.1f}m/s, "
        f"目标高度 {target_alt:.0f}m"
    )
    logger.info(f"[Skill] {description}")

    return SkillResult(
        success=True,
        description=description,
        actions_taken=actions,
        data={
            "intercept_heading": intercept_heading,
            "distance_m": distance,
            "radars_activated": len(radars),
        },
    )
