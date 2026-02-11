"""
Pydantic 数据模型定义
映射 C++ 仿真引擎的数据结构到 Python 类型
"""
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================================
# 基础数据模型
# ============================================================================

class Position(BaseModel):
    """地理位置（经纬高）"""
    latitude: float = Field(description="纬度（度）")
    longitude: float = Field(description="经度（度）")
    altitude: float = Field(description="高度（米）")


class Orientation(BaseModel):
    """姿态角"""
    pitch: float = Field(description="俯仰角（度）")
    heading: float = Field(description="航向角（度）")
    roll: float = Field(description="滚转角（度）")


# ============================================================================
# 装备数据模型
# ============================================================================

class EquipmentInfo(BaseModel):
    """装备信息"""
    entity_id: int = Field(description="装备实体 ID")
    entity_name: str = Field(description="装备名称")
    class_name: str = Field(default="", description="装备类名")
    type: str = Field(description="装备类型: radar/jammer/communication/sensor/weapon_system/platform")
    status: str = Field(description="装备状态: ON/OFF/FAULT")


# ============================================================================
# 单元数据模型
# ============================================================================

class UnitSummary(BaseModel):
    """单元摘要信息"""
    unit_id: int = Field(description="单元 ID")
    unit_name: str = Field(description="单元名称")
    unit_type: str = Field(default="", description="单元类型")
    forceside: str = Field(default="", description="所属方")
    alive: bool = Field(default=True, description="是否存活")
    active: bool = Field(default=True, description="是否激活")


class UnitState(BaseModel):
    """单元完整状态"""
    unit_id: int = Field(description="单元 ID")
    unit_name: str = Field(description="单元名称")
    unit_type: str = Field(default="", description="单元类型")
    dictionary_name: str = Field(default="", description="字典名称")
    forceside: str = Field(default="", description="所属方")
    position: Position = Field(description="地理位置")
    orientation: Orientation = Field(description="姿态角")
    speed: float = Field(description="速度（m/s）")
    alive: bool = Field(default=True, description="是否存活")
    active: bool = Field(default=True, description="是否激活")
    commander_id: int = Field(default=-1, description="指挥官单元 ID")
    commander_name: str = Field(default="", description="指挥官名称")
    equipment: list[EquipmentInfo] = Field(default_factory=list, description="装备列表")


# ============================================================================
# 世界状态
# ============================================================================

class WorldState(BaseModel):
    """全局世界状态"""
    sim_time: float = Field(description="仿真时间")
    units: list[UnitState] = Field(default_factory=list, description="所有单元状态")


class UnitsListResponse(BaseModel):
    """单元列表响应"""
    count: int = Field(description="单元数量")
    units: list[UnitSummary] = Field(default_factory=list, description="单元摘要列表")


class SimulationStatus(BaseModel):
    """仿真状态"""
    status: str = Field(description="状态")
    sim_time: float = Field(description="仿真时间")
    http_server_running: bool = Field(description="HTTP 服务运行状态")


# ============================================================================
# 控制请求模型
# ============================================================================

class EquipmentControlRequest(BaseModel):
    """装备控制请求"""
    power: Optional[bool] = Field(default=None, description="开关机控制: true=开机, false=关机")
    set_fault: Optional[bool] = Field(default=None, description="故障设置: true=设为故障")
    params: Optional[dict] = Field(default=None, description="其他控制参数键值对")


class UnitAlterRequest(BaseModel):
    """单元状态修改请求"""
    latitude: Optional[float] = Field(default=None, description="新纬度")
    longitude: Optional[float] = Field(default=None, description="新经度")
    altitude: Optional[float] = Field(default=None, description="新高度")
    pitch: Optional[float] = Field(default=None, description="新俯仰角")
    heading: Optional[float] = Field(default=None, description="新航向角")
    roll: Optional[float] = Field(default=None, description="新滚转角")
    speed: Optional[float] = Field(default=None, description="新速度")
    active: Optional[bool] = Field(default=None, description="激活状态")
    equipment: Optional[list[dict]] = Field(default=None, description="装备状态修改列表")


class MissionRequest(BaseModel):
    """任务请求"""
    action: str = Field(description="任务动作: add/terminate/postpone/adjust")
    mission_type: str = Field(description="任务类型: air/sea/adi/ballistic/sky_to_land/land_sea_to_sky")
    task_name: Optional[str] = Field(default=None, description="任务名称")
    task_old_name: Optional[str] = Field(default=None, description="原任务名称（新增时使用）")
    mission_time: Optional[float] = Field(default=None, description="任务时间参数")


# ============================================================================
# 通用响应
# ============================================================================

class ActionResult(BaseModel):
    """操作结果响应"""
    result: str = Field(description="操作结果: success/error")
    unit_name: Optional[str] = Field(default=None, description="目标单元名称")
    equipment_name: Optional[str] = Field(default=None, description="目标装备名称")
    error: Optional[str] = Field(default=None, description="错误信息")
    unit_state: Optional[UnitState] = Field(default=None, description="更新后的单元状态")
    equipment_state: Optional[EquipmentInfo] = Field(default=None, description="更新后的装备状态")
