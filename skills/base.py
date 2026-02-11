"""
Skill 基础定义
Skill = 可复用、可解释、可组合的战术动作
输入: WorldState / UnitState
输出: 一组 MCP Tool 调用序列（确定性）
"""
import math
from dataclasses import dataclass, field
from typing import Any
from loguru import logger


@dataclass
class SkillResult:
    """Skill 执行结果"""
    success: bool
    description: str
    actions_taken: list[dict] = field(default_factory=list)
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "description": self.description,
            "actions_taken": self.actions_taken,
            "data": self.data,
        }


class Skill:
    """Skill 基类 - 所有战术技能继承此类"""

    name: str = "base_skill"
    description: str = "Base skill"

    @staticmethod
    def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点之间的方位角（度）"""
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        dlon = math.radians(lon2 - lon1)

        x = math.sin(dlon) * math.cos(lat2_r)
        y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon)

        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点之间的距离（米），使用 Haversine 公式"""
        R = 6371000  # 地球半径（米）
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """限幅函数"""
        return max(min_val, min(max_val, value))

    @staticmethod
    def find_equipment_by_type(unit_state: dict, equip_type: str) -> list[dict]:
        """在单元状态中查找指定类型的装备"""
        equipment_list = unit_state.get("equipment", [])
        return [e for e in equipment_list if e.get("type") == equip_type]

    @staticmethod
    def find_equipment_by_name(unit_state: dict, equip_name: str) -> dict | None:
        """在单元状态中按名称查找装备"""
        equipment_list = unit_state.get("equipment", [])
        for e in equipment_list:
            if e.get("entity_name") == equip_name:
                return e
        return None
