"""
武器使用技能
包含：BVR攻击、目标锁定与发射、多目标分配
"""
from loguru import logger

from .base import Skill, SkillResult
from mcp.tools import (
    get_unit_state, get_weapon_status, weapon_lock_target, weapon_launch,
    weapon_abort, control_equipment, get_world_state,
)


class WeaponSkills(Skill):
    """武器系统技能集"""

    @staticmethod
    def bvr_attack(unit_name: str, target_name: str, weapon_name: str = None, launch_num: int = 1) -> SkillResult:
        """BVR 超视距攻击流程

        完整流程: 确认目标 -> 确认武器 -> 锁定 -> 发射

        Args:
            unit_name: 攻击方单元名称
            target_name: 目标单元名称
            weapon_name: 武器系统名称（为空则自动查找）
            launch_num: 发射弹数
        """
        try:
            # 1. 获取己方状态
            my_state = get_unit_state.invoke({"unit_name": unit_name})
            if "error" in my_state:
                return SkillResult(success=False, message=f"获取己方状态失败: {my_state['error']}")

            # 2. 查找武器系统
            if not weapon_name:
                weapon_name = Skill.find_equipment_by_type(my_state, "WeaponSystem")
                if not weapon_name:
                    return SkillResult(success=False, message="未找到武器系统")

            # 3. 检查武器状态
            weapon_status = get_weapon_status.invoke({"unit_name": unit_name, "weapon_name": weapon_name})
            if not weapon_status.get("available", False):
                return SkillResult(success=False, message="武器系统不可用")
            if not weapon_status.get("has_munition", False):
                return SkillResult(success=False, message="弹药已耗尽")

            # 4. 获取目标信息 - 查找目标 ID
            world = get_world_state.invoke({})
            target_id = None
            for u in world.get("units", []):
                if u.get("unit_name") == target_name:
                    target_id = u.get("unit_id")
                    break
            if target_id is None:
                return SkillResult(success=False, message=f"未找到目标: {target_name}")

            # 5. 确认雷达开启
            radar_name = Skill.find_equipment_by_type(my_state, "Sensor")
            if radar_name:
                control_equipment.invoke({
                    "unit_name": unit_name,
                    "equipment_name": radar_name,
                    "action": "TURN_ON",
                })

            # 6. 锁定目标
            lock_result = weapon_lock_target.invoke({
                "unit_name": unit_name,
                "weapon_name": weapon_name,
                "target_id": target_id,
            })
            logger.info(f"[Weapon] 锁定目标: {target_name}(ID={target_id})")

            # 7. 发射
            launch_result = weapon_launch.invoke({
                "unit_name": unit_name,
                "weapon_name": weapon_name,
                "target_id": target_id,
                "launch_num": launch_num,
            })
            logger.warning(f"[Weapon] 发射武器: {unit_name} -> {target_name}, 弹数={launch_num}")

            return SkillResult(
                success=True,
                message=f"BVR攻击执行完成: {unit_name} 向 {target_name} 发射 {launch_num} 枚导弹",
                data={
                    "attacker": unit_name,
                    "target": target_name,
                    "target_id": target_id,
                    "weapon": weapon_name,
                    "launch_num": launch_num,
                    "lock_result": lock_result,
                    "launch_result": launch_result,
                },
            )
        except Exception as e:
            logger.error(f"[Weapon] BVR 攻击失败: {e}")
            return SkillResult(success=False, message=f"BVR攻击异常: {str(e)}")

    @staticmethod
    def abort_engagement(unit_name: str, weapon_name: str = None) -> SkillResult:
        """中止当前交战

        Args:
            unit_name: 单元名称
            weapon_name: 武器系统名称
        """
        try:
            if not weapon_name:
                state = get_unit_state.invoke({"unit_name": unit_name})
                weapon_name = Skill.find_equipment_by_type(state, "WeaponSystem")
                if not weapon_name:
                    return SkillResult(success=False, message="未找到武器系统")

            result = weapon_abort.invoke({"unit_name": unit_name, "weapon_name": weapon_name})
            return SkillResult(success=True, message=f"已中止交战: {unit_name}/{weapon_name}", data=result)
        except Exception as e:
            return SkillResult(success=False, message=f"中止交战失败: {str(e)}")


# 技能注册
def bvr_attack(unit_name: str, target_name: str, weapon_name: str = None, launch_num: int = 1) -> SkillResult:
    """BVR超视距攻击：锁定并发射中距弹攻击目标"""
    return WeaponSkills.bvr_attack(unit_name, target_name, weapon_name, launch_num)


def abort_engagement(unit_name: str, weapon_name: str = None) -> SkillResult:
    """中止交战：取消当前武器交战"""
    return WeaponSkills.abort_engagement(unit_name, weapon_name)
