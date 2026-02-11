"""
技能模块 - 将高层战术意图转化为 MCP 工具调用序列

技能分类:
- maneuver: 基础飞行机动（爬升、下降、转向、规避、截击）
- flight: 平台飞行控制（航路飞行、巡逻、返航、编队、战斗展开）
- sensor: 雷达操作（开机、关机、搜索）
- electronic_warfare: 电子战（干扰机开关）
- communication: 通信管理
- weapon: 武器使用（BVR攻击、中止交战）
"""

from .maneuver import climb_and_accelerate, descend_and_decelerate, turn_to_heading, evade_missile, intercept_target
from .sensor import radar_power_on, radar_power_off, radar_search
from .electronic_warfare import activate_jammer, deactivate_jammer
from .communication import radio_power_on, radio_power_off
from .weapon import bvr_attack, abort_engagement
from .flight import fly_to_position, fly_heading, patrol_airspace, return_to_base, join_formation, combat_spread

# 全局技能注册表 - Tactical Agent 从这里选取技能
SKILL_REGISTRY = {
    # 基础机动
    "climb_and_accelerate": {
        "func": climb_and_accelerate,
        "description": "爬升并加速到指定高度和速度",
        "params": ["unit_name", "target_altitude", "target_speed"],
        "category": "maneuver",
    },
    "descend_and_decelerate": {
        "func": descend_and_decelerate,
        "description": "下降并减速到指定高度和速度",
        "params": ["unit_name", "target_altitude", "target_speed"],
        "category": "maneuver",
    },
    "turn_to_heading": {
        "func": turn_to_heading,
        "description": "转向到指定航向（度）",
        "params": ["unit_name", "target_heading"],
        "category": "maneuver",
    },
    "evade_missile": {
        "func": evade_missile,
        "description": "规避来袭导弹（急转下降+开启干扰）",
        "params": ["unit_name", "threat_bearing"],
        "category": "maneuver",
    },
    "intercept_target": {
        "func": intercept_target,
        "description": "截击目标（调整航向+加速趋近）",
        "params": ["unit_name", "target_name"],
        "category": "maneuver",
    },

    # 平台飞行
    "fly_to_position": {
        "func": fly_to_position,
        "description": "飞往指定经纬度坐标点（直接平台控制）",
        "params": ["unit_name", "latitude", "longitude", "altitude", "speed"],
        "category": "flight",
    },
    "fly_heading": {
        "func": fly_heading,
        "description": "按指定航向飞行（度，0=北）",
        "params": ["unit_name", "heading", "altitude", "speed"],
        "category": "flight",
    },
    "patrol_airspace": {
        "func": patrol_airspace,
        "description": "在指定空域巡逻飞行",
        "params": ["unit_name", "airspace_name", "altitude", "speed"],
        "category": "flight",
    },
    "return_to_base": {
        "func": return_to_base,
        "description": "返航着陆到基地",
        "params": ["unit_name", "airport_name"],
        "category": "flight",
    },
    "join_formation": {
        "func": join_formation,
        "description": "加入编队跟随长机飞行",
        "params": ["unit_name", "leader_name", "formation_name"],
        "category": "flight",
    },
    "combat_spread": {
        "func": combat_spread,
        "description": "面对威胁方向横向战斗展开",
        "params": ["unit_name", "threat_bearing", "altitude", "speed"],
        "category": "flight",
    },

    # 雷达
    "radar_power_on": {
        "func": radar_power_on,
        "description": "开启雷达",
        "params": ["unit_name"],
        "category": "sensor",
    },
    "radar_power_off": {
        "func": radar_power_off,
        "description": "关闭雷达（电磁静默）",
        "params": ["unit_name"],
        "category": "sensor",
    },
    "radar_search": {
        "func": radar_search,
        "description": "雷达搜索（开启雷达并获取探测结果）",
        "params": ["unit_name"],
        "category": "sensor",
    },

    # 电子战
    "activate_jammer": {
        "func": activate_jammer,
        "description": "开启干扰机",
        "params": ["unit_name"],
        "category": "ew",
    },
    "deactivate_jammer": {
        "func": deactivate_jammer,
        "description": "关闭干扰机",
        "params": ["unit_name"],
        "category": "ew",
    },

    # 通信
    "radio_power_on": {
        "func": radio_power_on,
        "description": "开启无线电通信",
        "params": ["unit_name"],
        "category": "comm",
    },
    "radio_power_off": {
        "func": radio_power_off,
        "description": "关闭无线电（通信静默）",
        "params": ["unit_name"],
        "category": "comm",
    },

    # 武器
    "bvr_attack": {
        "func": bvr_attack,
        "description": "BVR超视距攻击：雷达锁定+发射中距弹",
        "params": ["unit_name", "target_name", "weapon_name", "launch_num"],
        "category": "weapon",
    },
    "abort_engagement": {
        "func": abort_engagement,
        "description": "中止当前武器交战",
        "params": ["unit_name", "weapon_name"],
        "category": "weapon",
    },
}

__all__ = [
    "SKILL_REGISTRY",
    # maneuver
    "climb_and_accelerate", "descend_and_decelerate", "turn_to_heading", "evade_missile", "intercept_target",
    # flight
    "fly_to_position", "fly_heading", "patrol_airspace", "return_to_base", "join_formation", "combat_spread",
    # sensor
    "radar_power_on", "radar_power_off", "radar_search",
    # ew
    "activate_jammer", "deactivate_jammer",
    # comm
    "radio_power_on", "radio_power_off",
    # weapon
    "bvr_attack", "abort_engagement",
]
