"""
飞行控制技能（使用新的平台直接控制接口）
包含：航路飞行、巡逻、返航、编队、规避
"""
import math
from loguru import logger

from .base import Skill, SkillResult
from mcp.tools import (
    get_unit_state, platform_move_to_pos, platform_move_to_direction,
    platform_patrol, platform_return_land, platform_formation,
    control_equipment,
)


class FlightSkills(Skill):
    """飞行控制技能集"""

    @staticmethod
    def fly_to_position(unit_name: str, latitude: float, longitude: float,
                        altitude: float = 5000.0, speed: float = 200.0) -> SkillResult:
        """飞往指定经纬高位置

        Args:
            unit_name: 单元名称
            latitude: 目标纬度
            longitude: 目标经度
            altitude: 目标高度（米）
            speed: 飞行速度（m/s）
        """
        try:
            result = platform_move_to_pos.invoke({
                "unit_name": unit_name,
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude,
                "speed": speed,
            })
            return SkillResult(
                success=True,
                message=f"{unit_name} 飞往 ({latitude:.4f}, {longitude:.4f}) 高度{altitude}m 速度{speed}m/s",
                data=result,
            )
        except Exception as e:
            return SkillResult(success=False, message=f"飞行控制失败: {str(e)}")

    @staticmethod
    def fly_heading(unit_name: str, heading: float, altitude: float = 5000.0, speed: float = 200.0) -> SkillResult:
        """按指定航向飞行

        Args:
            unit_name: 单元名称
            heading: 航向（度，0=北）
            altitude: 飞行高度
            speed: 飞行速度
        """
        try:
            result = platform_move_to_direction.invoke({
                "unit_name": unit_name,
                "heading": heading,
                "altitude": altitude,
                "speed": speed,
            })
            return SkillResult(
                success=True,
                message=f"{unit_name} 按航向 {heading}° 飞行",
                data=result,
            )
        except Exception as e:
            return SkillResult(success=False, message=f"航向飞行失败: {str(e)}")

    @staticmethod
    def patrol_airspace(unit_name: str, airspace_name: str,
                        altitude: float = 5000.0, speed: float = 200.0) -> SkillResult:
        """在空域巡逻"""
        try:
            result = platform_patrol.invoke({
                "unit_name": unit_name,
                "airspace_name": airspace_name,
                "altitude": altitude,
                "speed": speed,
            })
            return SkillResult(
                success=True,
                message=f"{unit_name} 在空域 {airspace_name} 巡逻",
                data=result,
            )
        except Exception as e:
            return SkillResult(success=False, message=f"巡逻指令失败: {str(e)}")

    @staticmethod
    def return_to_base(unit_name: str, airport_name: str = None) -> SkillResult:
        """返航着陆"""
        try:
            result = platform_return_land.invoke({
                "unit_name": unit_name,
                "land_type": "直接返航",
                "airport_name": airport_name,
            })
            return SkillResult(
                success=True,
                message=f"{unit_name} 返航" + (f"至 {airport_name}" if airport_name else ""),
                data=result,
            )
        except Exception as e:
            return SkillResult(success=False, message=f"返航指令失败: {str(e)}")

    @staticmethod
    def join_formation(unit_name: str, leader_name: str, formation_name: str = None) -> SkillResult:
        """加入编队"""
        try:
            result = platform_formation.invoke({
                "unit_name": unit_name,
                "leader_name": leader_name,
                "formation_name": formation_name,
            })
            return SkillResult(
                success=True,
                message=f"{unit_name} 加入 {leader_name} 的编队",
                data=result,
            )
        except Exception as e:
            return SkillResult(success=False, message=f"编队指令失败: {str(e)}")

    @staticmethod
    def combat_spread(unit_name: str, threat_bearing: float, altitude: float = None,
                      speed: float = None) -> SkillResult:
        """战斗展开（面对威胁方向横向展开）

        Args:
            unit_name: 单元名称
            threat_bearing: 威胁来源方位角（度）
            altitude: 展开高度（可选，默认保持当前高度）
            speed: 展开速度（可选，默认保持当前速度）
        """
        try:
            state = get_unit_state.invoke({"unit_name": unit_name})
            if "error" in state:
                return SkillResult(success=False, message=f"获取状态失败: {state['error']}")

            current_alt = state.get("position", {}).get("altitude", 5000.0)
            current_spd = state.get("speed", 200.0)

            # 计算横向展开航向（垂直于威胁方向）
            spread_heading = (threat_bearing + 90.0) % 360.0

            result = platform_move_to_direction.invoke({
                "unit_name": unit_name,
                "heading": spread_heading,
                "altitude": altitude or current_alt,
                "speed": speed or current_spd,
                "turn_g": 4.0,
            })
            return SkillResult(
                success=True,
                message=f"{unit_name} 面对威胁方位 {threat_bearing}° 横向展开至 {spread_heading}°",
                data=result,
            )
        except Exception as e:
            return SkillResult(success=False, message=f"战斗展开失败: {str(e)}")


# 技能注册函数
def fly_to_position(unit_name: str, latitude: float, longitude: float,
                    altitude: float = 5000.0, speed: float = 200.0) -> SkillResult:
    """飞往指定经纬高坐标"""
    return FlightSkills.fly_to_position(unit_name, latitude, longitude, altitude, speed)


def fly_heading(unit_name: str, heading: float, altitude: float = 5000.0, speed: float = 200.0) -> SkillResult:
    """按指定航向飞行"""
    return FlightSkills.fly_heading(unit_name, heading, altitude, speed)


def patrol_airspace(unit_name: str, airspace_name: str,
                    altitude: float = 5000.0, speed: float = 200.0) -> SkillResult:
    """在空域巡逻"""
    return FlightSkills.patrol_airspace(unit_name, airspace_name, altitude, speed)


def return_to_base(unit_name: str, airport_name: str = None) -> SkillResult:
    """返航着陆"""
    return FlightSkills.return_to_base(unit_name, airport_name)


def join_formation(unit_name: str, leader_name: str, formation_name: str = None) -> SkillResult:
    """加入编队飞行"""
    return FlightSkills.join_formation(unit_name, leader_name, formation_name)


def combat_spread(unit_name: str, threat_bearing: float,
                  altitude: float = None, speed: float = None) -> SkillResult:
    """面对威胁方向战斗展开"""
    return FlightSkills.combat_spread(unit_name, threat_bearing, altitude, speed)
