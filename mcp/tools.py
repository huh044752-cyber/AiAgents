"""
MCP Tools 定义
每个函数是一个可被 LangGraph Agent 调用的工具
映射到 C++ AiHttpService 的 HTTP 端点
"""
from typing import Optional
from langchain_core.tools import tool
from loguru import logger

from .client import get_client
from .schemas import (
    WorldState,
    UnitState,
    UnitsListResponse,
    EquipmentInfo,
    SimulationStatus,
    ActionResult,
)
from utils.replay import get_recorder


def _record_call(tool_name: str, params: dict, result: dict):
    """记录工具调用到回放系统"""
    try:
        sim_time = result.get("sim_time", 0.0)
        get_recorder().record(tool_name, params, result, sim_time)
    except Exception:
        pass


# ============================================================================
# 查询类工具
# ============================================================================

@tool
def get_world_state() -> dict:
    """获取当前全局世界态势，包含所有作战单元的位置、姿态、速度、装备状态等信息。
    返回完整的战场态势数据，是 AI 决策的基础信息来源。"""
    client = get_client()
    result = client.get("/api/world_state")
    _record_call("get_world_state", {}, result)
    logger.info(f"[MCP] get_world_state -> {len(result.get('units', []))} units")
    return result


@tool
def get_unit_state(unit_name: str) -> dict:
    """获取指定作战单元的完整状态信息。

    Args:
        unit_name: 单元名称

    Returns:
        包含位置、姿态、速度、装备列表等完整信息
    """
    client = get_client()
    result = client.get(f"/api/unit/{unit_name}/state")
    _record_call("get_unit_state", {"unit_name": unit_name}, result)
    logger.info(f"[MCP] get_unit_state({unit_name})")
    return result


@tool
def get_units_list() -> dict:
    """获取所有作战单元的摘要列表（ID、名称、类型、阵营、存活状态）。
    适合快速了解战场全局兵力部署。"""
    client = get_client()
    result = client.get("/api/units")
    _record_call("get_units_list", {}, result)
    logger.info(f"[MCP] get_units_list -> {result.get('count', 0)} units")
    return result


@tool
def query_equipment(unit_name: str, equipment_name: str) -> dict:
    """查询指定单元上指定装备的详细状态信息。

    Args:
        unit_name: 单元名称
        equipment_name: 装备名称

    Returns:
        装备的类型、状态（ON/OFF/FAULT）等信息
    """
    client = get_client()
    result = client.get(f"/api/unit/{unit_name}/equipment/{equipment_name}/query")
    _record_call("query_equipment", {"unit_name": unit_name, "equipment_name": equipment_name}, result)
    logger.info(f"[MCP] query_equipment({unit_name}, {equipment_name})")
    return result


@tool
def get_simulation_status() -> dict:
    """获取仿真引擎的运行状态和当前仿真时间。"""
    client = get_client()
    result = client.get("/api/simulation/status")
    _record_call("get_simulation_status", {}, result)
    return result


# ============================================================================
# 控制类工具
# ============================================================================

@tool
def control_equipment(
    unit_name: str,
    equipment_name: str,
    power: Optional[bool] = None,
    set_fault: Optional[bool] = None,
    params: Optional[dict] = None,
) -> dict:
    """控制指定单元上的装备（开关机、故障设置、参数调整）。

    Args:
        unit_name: 单元名称
        equipment_name: 装备名称
        power: 开关机控制，True=开机，False=关机
        set_fault: 故障设置，True=设为故障
        params: 其他控制参数键值对

    Returns:
        操作结果和更新后的装备状态

    安全约束: 所有控制均通过引擎接口执行，不直接修改物理状态。
    """
    client = get_client()
    body = {}
    if power is not None:
        body["power"] = power
    if set_fault is not None:
        body["set_fault"] = set_fault
    if params is not None:
        body["params"] = params

    result = client.post(f"/api/unit/{unit_name}/equipment/{equipment_name}/control", body)
    _record_call("control_equipment", {"unit_name": unit_name, "equipment_name": equipment_name, **body}, result)
    logger.info(f"[MCP] control_equipment({unit_name}, {equipment_name}, {body})")
    return result


@tool
def alter_unit(
    unit_name: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    altitude: Optional[float] = None,
    heading: Optional[float] = None,
    pitch: Optional[float] = None,
    roll: Optional[float] = None,
    speed: Optional[float] = None,
    active: Optional[bool] = None,
) -> dict:
    """修改指定单元的状态（位置、姿态、速度、激活状态）。

    Args:
        unit_name: 单元名称
        latitude: 新纬度（度）
        longitude: 新经度（度）
        altitude: 新高度（米）
        heading: 新航向角（度）
        pitch: 新俯仰角（度）
        roll: 新滚转角（度）
        speed: 新速度（m/s）
        active: 激活状态

    Returns:
        操作结果和更新后的单元状态

    安全约束: 通过 ManualInterventionServices 执行，遵守引擎限幅规则。
    """
    client = get_client()
    body = {}
    if latitude is not None:
        body["latitude"] = latitude
    if longitude is not None:
        body["longitude"] = longitude
    if altitude is not None:
        body["altitude"] = altitude
    if heading is not None:
        body["heading"] = heading
    if pitch is not None:
        body["pitch"] = pitch
    if roll is not None:
        body["roll"] = roll
    if speed is not None:
        body["speed"] = speed
    if active is not None:
        body["active"] = active

    result = client.post(f"/api/unit/{unit_name}/alter", body)
    _record_call("alter_unit", {"unit_name": unit_name, **body}, result)
    logger.info(f"[MCP] alter_unit({unit_name}, {body})")
    return result


@tool
def assign_mission(
    unit_name: str,
    action: str,
    mission_type: str,
    task_name: Optional[str] = None,
    task_old_name: Optional[str] = None,
    mission_time: Optional[float] = None,
) -> dict:
    """为指定单元下达或调整任务。

    Args:
        unit_name: 单元名称
        action: 任务操作类型 - "add"(新增), "terminate"(终止), "postpone"(推迟), "adjust"(调整)
        mission_type: 任务类型 - "air"(航空兵), "sea"(海域), "adi"(防空拦截),
                      "ballistic"(弹道弹), "sky_to_land"(天对地), "land_sea_to_sky"(地海对空天)
        task_name: 任务名称
        task_old_name: 原任务名称（新增任务时需要指定基于哪个任务新增）
        mission_time: 任务时间参数（新增时为开始时间，推迟时为推迟时间）

    Returns:
        操作结果
    """
    client = get_client()
    body = {
        "action": action,
        "mission_type": mission_type,
    }
    if task_name is not None:
        body["task_name"] = task_name
    if task_old_name is not None:
        body["task_old_name"] = task_old_name
    if mission_time is not None:
        body["mission_time"] = mission_time

    result = client.post(f"/api/unit/{unit_name}/mission", body)
    _record_call("assign_mission", {"unit_name": unit_name, **body}, result)
    logger.info(f"[MCP] assign_mission({unit_name}, {action}, {mission_type})")
    return result


# ============================================================================
# 扩展工具 - 平台飞行控制
# ============================================================================

@tool
def platform_move_to_pos(
    unit_name: str,
    latitude: float,
    longitude: float,
    altitude: float = 5000.0,
    speed: float = 200.0,
    turn_g: float = 3.0,
) -> dict:
    """命令平台飞往指定经纬高坐标点。

    Args:
        unit_name: 单元名称
        latitude: 目标纬度
        longitude: 目标经度
        altitude: 目标高度（米），默认5000
        speed: 飞行速度（m/s），默认200
        turn_g: 转弯过载（G），默认3
    """
    client = get_client()
    body = {"latitude": latitude, "longitude": longitude, "altitude": altitude,
            "speed": speed, "turn_g": turn_g}
    result = client.post(f"/api/unit/{unit_name}/platform/move_to_pos", body)
    _record_call("platform_move_to_pos", {"unit_name": unit_name, **body}, result)
    logger.info(f"[MCP] platform_move_to_pos({unit_name}, lat={latitude}, lon={longitude})")
    return result


@tool
def platform_move_to_direction(
    unit_name: str,
    heading: float,
    altitude: float = 5000.0,
    speed: float = 200.0,
    turn_g: float = 3.0,
) -> dict:
    """命令平台朝指定航向飞行。

    Args:
        unit_name: 单元名称
        heading: 目标航向（度，0=北，顺时针）
        altitude: 飞行高度（米）
        speed: 飞行速度（m/s）
        turn_g: 转弯过载（G）
    """
    client = get_client()
    body = {"heading": heading, "altitude": altitude, "speed": speed, "turn_g": turn_g}
    result = client.post(f"/api/unit/{unit_name}/platform/move_to_dir", body)
    _record_call("platform_move_to_direction", {"unit_name": unit_name, **body}, result)
    return result


@tool
def platform_patrol(unit_name: str, airspace_name: str, altitude: float = 5000.0, speed: float = 200.0) -> dict:
    """命令平台在指定空域巡逻。

    Args:
        unit_name: 单元名称
        airspace_name: 空域名称
        altitude: 巡逻高度（米）
        speed: 巡逻速度（m/s）
    """
    client = get_client()
    body = {"airspace_name": airspace_name, "altitude": altitude, "speed": speed}
    result = client.post(f"/api/unit/{unit_name}/platform/patrol", body)
    _record_call("platform_patrol", {"unit_name": unit_name, **body}, result)
    return result


@tool
def platform_return_land(unit_name: str, land_type: str = "直接返航", airport_name: str = None) -> dict:
    """命令平台返航着陆。

    Args:
        unit_name: 单元名称
        land_type: 返航方式 - "直接返航" 或 "原路返航"
        airport_name: 目标机场名称（可选）
    """
    client = get_client()
    body = {"land_type": land_type}
    if airport_name:
        body["airport_name"] = airport_name
    result = client.post(f"/api/unit/{unit_name}/platform/return_land", body)
    _record_call("platform_return_land", {"unit_name": unit_name, **body}, result)
    return result


@tool
def platform_formation(unit_name: str, leader_name: str, formation_name: str = None) -> dict:
    """命令平台编队飞行。

    Args:
        unit_name: 单元名称（跟随者）
        leader_name: 长机名称
        formation_name: 编队队形名称（可选）
    """
    client = get_client()
    body = {"leader_name": leader_name}
    if formation_name:
        body["formation_name"] = formation_name
    result = client.post(f"/api/unit/{unit_name}/platform/formation", body)
    _record_call("platform_formation", {"unit_name": unit_name, **body}, result)
    return result


# ============================================================================
# 扩展工具 - 雷达/干扰机详情
# ============================================================================

@tool
def get_radar_detail(unit_name: str, radar_name: str) -> dict:
    """获取雷达的详细参数（频率、功率、波束宽度、增益等）。

    Args:
        unit_name: 单元名称
        radar_name: 雷达装备名称
    """
    client = get_client()
    result = client.get(f"/api/unit/{unit_name}/radar/{radar_name}/detail")
    _record_call("get_radar_detail", {"unit_name": unit_name, "radar_name": radar_name}, result)
    return result


@tool
def get_jammer_detail(unit_name: str, jammer_name: str) -> dict:
    """获取干扰机的详细参数（干扰功率、频率、波束宽度等）。

    Args:
        unit_name: 单元名称
        jammer_name: 干扰机装备名称
    """
    client = get_client()
    result = client.get(f"/api/unit/{unit_name}/jammer/{jammer_name}/detail")
    _record_call("get_jammer_detail", {"unit_name": unit_name, "jammer_name": jammer_name}, result)
    return result


@tool
def jammer_command(
    unit_name: str,
    jammer_name: str,
    command: str = "SAECMCmd",
    jam_type: int = 1,
    center_az: float = 0.0,
    center_el: float = 0.0,
    az_range: float = 30.0,
    el_range: float = 15.0,
    duration: float = 60.0,
    target_name: str = None,
) -> dict:
    """向干扰机发送干扰指令（指定干扰方向、类型、时长）。

    Args:
        unit_name: 单元名称
        jammer_name: 干扰机装备名称
        command: 干扰指令类型 - "SAECMCmd"(空对空) 或 "AGECMCmd"(空对地)
        jam_type: 干扰类型编号
        center_az: 干扰中心方位角（度）
        center_el: 干扰中心仰角（度）
        az_range: 方位覆盖范围（度）
        el_range: 仰角覆盖范围（度）
        duration: 干扰持续时间（秒）
        target_name: 干扰目标名称（AGECMCmd时使用）
    """
    client = get_client()
    body = {"command": command, "jam_type": jam_type,
            "center_az": center_az, "center_el": center_el,
            "az_range": az_range, "el_range": el_range, "duration": duration}
    if target_name:
        body["target_name"] = target_name
    result = client.post(f"/api/unit/{unit_name}/jammer/{jammer_name}/command", body)
    _record_call("jammer_command", {"unit_name": unit_name, "jammer_name": jammer_name, **body}, result)
    return result


# ============================================================================
# 扩展工具 - 武器系统
# ============================================================================

@tool
def get_weapon_status(unit_name: str, weapon_name: str) -> dict:
    """查询武器系统状态（弹药可用性、交战状态）。

    Args:
        unit_name: 单元名称
        weapon_name: 武器系统名称
    """
    client = get_client()
    result = client.get(f"/api/unit/{unit_name}/weapon/{weapon_name}/status")
    _record_call("get_weapon_status", {"unit_name": unit_name, "weapon_name": weapon_name}, result)
    return result


@tool
def weapon_lock_target(unit_name: str, weapon_name: str, target_id: int) -> dict:
    """武器系统锁定目标。

    Args:
        unit_name: 单元名称
        weapon_name: 武器系统名称
        target_id: 目标单元 ID

    安全约束: 锁定不等于发射，锁定后需确认才能发射。
    """
    client = get_client()
    body = {"target_id": target_id}
    result = client.post(f"/api/unit/{unit_name}/weapon/{weapon_name}/lock", body)
    _record_call("weapon_lock_target", {"unit_name": unit_name, "weapon_name": weapon_name, **body}, result)
    return result


@tool
def weapon_launch(unit_name: str, weapon_name: str, target_id: int, launch_num: int = 1) -> dict:
    """发射武器攻击目标。

    Args:
        unit_name: 单元名称
        weapon_name: 武器系统名称
        target_id: 目标单元 ID
        launch_num: 发射弹药数量，默认1

    安全约束: 仅在确认目标在发射包线内且已锁定后才能发射。
    """
    client = get_client()
    body = {"target_id": target_id, "launch_num": launch_num}
    result = client.post(f"/api/unit/{unit_name}/weapon/{weapon_name}/launch", body)
    _record_call("weapon_launch", {"unit_name": unit_name, "weapon_name": weapon_name, **body}, result)
    logger.warning(f"[MCP] WEAPON LAUNCH: {unit_name}/{weapon_name} -> target {target_id} x{launch_num}")
    return result


@tool
def weapon_abort(unit_name: str, weapon_name: str) -> dict:
    """中止武器交战。

    Args:
        unit_name: 单元名称
        weapon_name: 武器系统名称
    """
    client = get_client()
    result = client.post(f"/api/unit/{unit_name}/weapon/{weapon_name}/abort", {})
    _record_call("weapon_abort", {"unit_name": unit_name, "weapon_name": weapon_name}, result)
    return result


# ============================================================================
# 扩展工具 - 通信详情
# ============================================================================

@tool
def get_comm_detail(unit_name: str, comm_name: str) -> dict:
    """获取通信设备的详细参数（频率、功率等）。

    Args:
        unit_name: 单元名称
        comm_name: 通信设备名称
    """
    client = get_client()
    result = client.get(f"/api/unit/{unit_name}/comm/{comm_name}/detail")
    _record_call("get_comm_detail", {"unit_name": unit_name, "comm_name": comm_name}, result)
    return result


# ============================================================================
# 工具列表（供 Agent 使用）
# ============================================================================

# 所有可用 MCP 工具
ALL_TOOLS = [
    # 基础查询
    get_world_state, get_unit_state, get_units_list, query_equipment, get_simulation_status,
    # 基础控制
    control_equipment, alter_unit, assign_mission,
    # 平台飞行控制
    platform_move_to_pos, platform_move_to_direction, platform_patrol,
    platform_return_land, platform_formation,
    # 雷达/干扰机
    get_radar_detail, get_jammer_detail, jammer_command,
    # 武器系统
    get_weapon_status, weapon_lock_target, weapon_launch, weapon_abort,
    # 通信
    get_comm_detail,
]

# 只读工具（查询类）
QUERY_TOOLS = [
    get_world_state, get_unit_state, get_units_list, query_equipment, get_simulation_status,
    get_radar_detail, get_jammer_detail, get_weapon_status, get_comm_detail,
]

# 控制工具（写入类）
CONTROL_TOOLS = [
    control_equipment, alter_unit, assign_mission,
    platform_move_to_pos, platform_move_to_direction, platform_patrol,
    platform_return_land, platform_formation,
    jammer_command,
    weapon_lock_target, weapon_launch, weapon_abort,
]
