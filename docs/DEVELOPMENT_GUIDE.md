# AI 飞行仿真 Agent 开发指南

## 目录

1. [环境搭建](#1-环境搭建)
2. [项目结构](#2-项目结构)
3. [C++ 侧开发](#3-c-侧开发)
4. [Python 侧开发](#4-python-侧开发)
5. [RAG 知识库](#5-rag-知识库)
6. [API 参考](#6-api-参考)
7. [技能开发](#7-技能开发)
8. [调试与测试](#8-调试与测试)

---

## 1. 环境搭建

### 1.1 Python 环境

```bash
cd AiAgent
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 1.2 配置文件

复制 `.env.example` 为 `.env` 并填写:

```dotenv
DASHSCOPE_API_KEY=your_api_key_here
SIM_ENGINE_HOST=127.0.0.1
SIM_ENGINE_PORT=8080
LOG_LEVEL=DEBUG
```

### 1.3 C++ 编译

`AiHttpService` 需要加入到 FZFOSimModel 的编译项目中：
- 将 `Services/AiHttpService/` 目录加入 CMakeLists 或 VS 项目
- 头文件依赖: `httplib.h`, `json.hpp`（已放在服务目录下）
- 链接依赖: 无额外链接库（header-only）

---

## 2. 项目结构

```
ai_project/
├── FOSimEngine/                    # C++ 仿真引擎（只读）
├── FZFOSimModel/                   # C++ 仿真模型
│   └── ModelSource/FZBasicModel/
│       ├── Equipment/              # 装备模型
│       │   ├── Sensors/            #   雷达
│       │   ├── Jammers/            #   干扰机
│       │   ├── ComDevices/         #   通信设备
│       │   ├── Platforms/          #   平台(飞机)
│       │   └── WeaponSystems/      #   武器系统
│       └── Services/
│           ├── AiHttpService/      # ★ AI HTTP 服务（新增）
│           │   ├── aihttpservice.h
│           │   ├── aihttpservice.cpp
│           │   ├── aihttpservice_attr.cpp
│           │   ├── aihttpservice_exec.cpp
│           │   ├── aihttpservice_process.cpp
│           │   ├── aihttpservice_routes.cpp      # 基础路由
│           │   ├── aihttpservice_routes_ext.cpp   # 扩展路由
│           │   ├── AiHttpServiceData.hpp
│           │   ├── httplib.h                      # cpp-httplib
│           │   └── json.hpp                       # nlohmann/json
│           ├── ManualInterventionServices/
│           └── MQService/
│
└── AiAgent/                        # ★ Python AI Agent
    ├── main.py                     # 入口
    ├── config.py                   # 配置
    ├── requirements.txt
    ├── .env.example
    ├── mcp/                        # MCP 工具层
    │   ├── __init__.py
    │   ├── client.py               # HTTP 客户端
    │   ├── schemas.py              # Pydantic 数据模型
    │   └── tools.py                # 22个 MCP 工具函数
    ├── skills/                     # 技能层
    │   ├── __init__.py             # 技能注册表
    │   ├── base.py                 # 基类和工具函数
    │   ├── maneuver.py             # 飞行机动
    │   ├── flight.py               # 平台飞行控制
    │   ├── sensor.py               # 雷达操作
    │   ├── electronic_warfare.py   # 电子战
    │   ├── communication.py        # 通信管理
    │   └── weapon.py               # 武器使用
    ├── agent/                      # Agent 层
    │   ├── __init__.py
    │   ├── state.py                # LangGraph 状态定义
    │   ├── commander.py            # 指挥官节点 (+ RAG)
    │   ├── tactical.py             # 战术选择节点
    │   ├── executor.py             # 执行器节点
    │   └── graph.py                # LangGraph 图定义
    ├── rag/                        # RAG 知识检索
    │   ├── __init__.py
    │   ├── retriever.py            # RAG 检索器
    │   ├── knowledge_base/         # 知识库文档
    │   │   ├── 01_空战战术条令.md
    │   │   ├── 02_装备使用手册_雷达.md
    │   │   ├── 03_装备使用手册_电子战.md
    │   │   ├── 04_装备使用手册_武器系统.md
    │   │   └── 05_历史案例_空战对抗.md
    │   └── vector_store/           # FAISS 向量索引(自动生成)
    ├── utils/                      # 工具
    │   ├── logger.py
    │   └── replay.py
    └── docs/                       # 项目文档
        ├── PROJECT_PLAN.md
        └── DEVELOPMENT_GUIDE.md    # 本文档
```

---

## 3. C++ 侧开发

### 3.1 AiHttpService 架构

`AiHttpService` 继承 `CyberServiceImpl`，作为引擎的标准服务插件运行。使用 `CYMODEL_REGIST(AiHttpService)` 宏注册到引擎。

**核心组件:**
- `httplib::Server` - HTTP 服务器（独立线程）
- `nlohmann::json` - JSON 序列化
- `CyberMalImpl` - 引擎内部消息传递

### 3.2 添加新 HTTP 接口

步骤:
1. 在 `aihttpservice.h` 中声明新的 Handle 函数
2. 在 `aihttpservice_routes.cpp` 或 `_routes_ext.cpp` 中注册路由
3. 实现 Handle 函数

示例 - 添加新的查询接口:

```cpp
// aihttpservice.h 中声明
void HandleGetNewFeature(const void *req, void *res);

// SetupRoutes() 中注册
server_->Get(R"(/api/unit/([^/]+)/new_feature)", [this](const httplib::Request &req, httplib::Response &res)
{ HandleGetNewFeature(&req, &res); });

// 实现
void AiHttpService::HandleGetNewFeature(const void *req_ptr, void *res_ptr)
{
    auto &req = *(const httplib::Request *)req_ptr;
    auto &res = *(httplib::Response *)res_ptr;
    try {
        std::string unit_name = req.matches[1].str();
        ICyberUnit *unit = GetUnitByName(unit_name.c_str());
        // ... 查询逻辑
        json response;
        response["result"] = "ok";
        res.set_content(response.dump(2), "application/json");
    } catch (const std::exception &e) {
        json err; err["error"] = e.what();
        res.status = 500;
        res.set_content(err.dump(), "application/json");
    }
}
```

### 3.3 与装备交互模式

所有装备交互通过 `CyberMalImpl` (MAL = Message Argument List):

```cpp
// 查询 Query
CyberMalImpl *mal = CyberMalImpl::CreateMAL();
mal->AddName("IS_TURN_ON", "IS_TURN_ON");
CyberBOOL value = CYBER_FALSE;
mal->AddBoolean("IS_TURN_ON", value);
equipment->Query(mal);
mal->GetBoolean("IS_TURN_ON", value);
mal->MalDestroy();

// 修改 Alter
CyberMalImpl mal;
mal.AddBoolean("TURN_ON_OFF", CYBER_TRUE);
equipment->Alter(&mal);

// 控制 Control
CyberMalImpl mal;
mal.AddName("MoveToPos_LLA", "MoveToPos_LLA");
mal.AddReal("Lat", 39.0);
mal.AddReal("Lon", 116.0);
mal.AddReal("Height", 5000.0);
equipment->Control(&mal);
```

---

## 4. Python 侧开发

### 4.1 MCP 工具开发

每个 MCP 工具是一个 `@tool` 装饰的函数，内部调用 HTTP 客户端:

```python
from langchain_core.tools import tool
from mcp.client import get_client

@tool
def my_new_tool(unit_name: str, param1: float) -> dict:
    """工具描述（会被 LLM 读取来理解工具用途）

    Args:
        unit_name: 单元名称
        param1: 参数说明
    """
    client = get_client()
    result = client.post(f"/api/unit/{unit_name}/new_endpoint", {"param1": param1})
    return result
```

### 4.2 技能开发

技能是将多个 MCP 工具调用编排为战术动作:

```python
from skills.base import Skill, SkillResult
from mcp.tools import get_unit_state, control_equipment

def my_tactical_skill(unit_name: str, **kwargs) -> SkillResult:
    """技能描述"""
    try:
        # 1. 获取状态
        state = get_unit_state.invoke({"unit_name": unit_name})
        
        # 2. 计算参数
        # ...
        
        # 3. 执行控制
        result = control_equipment.invoke({...})
        
        return SkillResult(success=True, message="执行成功", data=result)
    except Exception as e:
        return SkillResult(success=False, message=str(e))
```

注册到 `skills/__init__.py`:
```python
SKILL_REGISTRY["my_skill"] = {
    "func": my_tactical_skill,
    "description": "技能描述",
    "params": ["unit_name", "param1"],
    "category": "custom",
}
```

### 4.3 Agent 流程

```
用户任务 → Commander(理解+态势+RAG) → Tactical(选技能) → Executor(执行)
                                                              ↓
                                                         Observe(观察结果)
                                                              ↓
                                                    是否需要继续？ → Commander
```

---

## 5. RAG 知识库

### 5.1 添加新知识

在 `rag/knowledge_base/` 中添加 `.md` 或 `.json` 文件:

**Markdown 格式** (推荐):
```markdown
# 文档标题

## 章节1
知识内容...

## 章节2
知识内容...
```

**JSON 格式**:
```json
[
  {"content": "知识内容1", "category": "tactics"},
  {"content": "知识内容2", "category": "weapon_manual"}
]
```

### 5.2 文件命名规范

文件名中包含关键词会自动分类:
- `tactic`/`战术`/`条令` → tactics
- `radar`/`雷达` → radar_manual
- `jam`/`干扰`/`电子战` → ew_manual
- `weapon`/`武器` → weapon_manual
- `case`/`案例` → historical_case
- `comm`/`通信` → comm_manual

### 5.3 重建向量库

修改知识库后需重建:
```python
from rag import get_rag
rag = get_rag()
rag.rebuild()
```

---

## 6. API 参考

### 6.1 平台飞行控制

**飞往坐标点**
```
POST /api/unit/{name}/platform/move_to_pos
{
    "latitude": 39.0,       // 纬度
    "longitude": 116.0,     // 经度
    "altitude": 5000.0,     // 高度(m)
    "speed": 200.0,         // 速度(m/s)
    "turn_g": 3.0           // 转弯过载(G)
}
```

**按航向飞行**
```
POST /api/unit/{name}/platform/move_to_dir
{
    "heading": 90.0,        // 航向(度, 0=北)
    "altitude": 5000.0,
    "speed": 200.0,
    "turn_g": 3.0
}
```

**空域巡逻**
```
POST /api/unit/{name}/platform/patrol
{
    "airspace_name": "巡逻空域A",
    "altitude": 5000.0,
    "speed": 200.0
}
```

**返航着陆**
```
POST /api/unit/{name}/platform/return_land
{
    "land_type": "直接返航",     // 或 "原路返航"
    "airport_name": "A机场"      // 可选
}
```

**编队飞行**
```
POST /api/unit/{name}/platform/formation
{
    "leader_name": "长机",
    "formation_name": "战斗队形"  // 可选
}
```

### 6.2 雷达操作

**雷达详情查询**
```
GET /api/unit/{name}/radar/{entity}/detail
→ {
    "entity_name": "...",
    "is_on": true,
    "radar_params": {
        "frequency_mhz": 9500.0,
        "transmit_power_dbw": 70.0,
        "az_beam_width_deg": 3.5,
        "el_beam_width_deg": 3.5,
        "max_antenna_gain_db": 35.0
    }
}
```

### 6.3 干扰机操作

**干扰指令**
```
POST /api/unit/{name}/jammer/{entity}/command
{
    "command": "SAECMCmd",    // 干扰类型
    "jam_type": 1,            // 干扰方式
    "center_az": 0.0,         // 干扰中心方位(度)
    "center_el": 0.0,         // 干扰中心仰角(度)
    "az_range": 30.0,         // 方位覆盖范围
    "el_range": 15.0,         // 仰角覆盖范围
    "duration": 60.0          // 干扰时长(秒)
}
```

### 6.4 武器系统

**武器状态查询**
```
GET /api/unit/{name}/weapon/{entity}/status
→ {
    "available": true,
    "engaged": false,
    "has_munition": true
}
```

**锁定目标**
```
POST /api/unit/{name}/weapon/{entity}/lock
{"target_id": 123}
```

**发射武器**
```
POST /api/unit/{name}/weapon/{entity}/launch
{
    "target_id": 123,
    "launch_num": 1
}
```

**中止交战**
```
POST /api/unit/{name}/weapon/{entity}/abort
{}
```

---

## 7. 技能开发

### 7.1 技能注册表

所有技能在 `skills/__init__.py` 的 `SKILL_REGISTRY` 中注册，格式:

```python
"skill_name": {
    "func": skill_function,          # 可调用对象
    "description": "人类可读描述",    # LLM 使用此描述选择技能
    "params": ["param1", "param2"],  # 参数列表
    "category": "类别",              # maneuver/flight/sensor/ew/comm/weapon
}
```

### 7.2 当前技能清单 (22个)

| 类别 | 技能 | 说明 |
|------|------|------|
| maneuver | climb_and_accelerate | 爬升加速 |
| maneuver | descend_and_decelerate | 下降减速 |
| maneuver | turn_to_heading | 转向 |
| maneuver | evade_missile | 导弹规避 |
| maneuver | intercept_target | 截击目标 |
| flight | fly_to_position | 飞往坐标 |
| flight | fly_heading | 按航向飞 |
| flight | patrol_airspace | 空域巡逻 |
| flight | return_to_base | 返航 |
| flight | join_formation | 编队 |
| flight | combat_spread | 战斗展开 |
| sensor | radar_power_on | 开启雷达 |
| sensor | radar_power_off | 关闭雷达 |
| sensor | radar_search | 雷达搜索 |
| ew | activate_jammer | 开启干扰机 |
| ew | deactivate_jammer | 关闭干扰机 |
| comm | radio_power_on | 开启通信 |
| comm | radio_power_off | 关闭通信 |
| weapon | bvr_attack | BVR超视距攻击 |
| weapon | abort_engagement | 中止交战 |

---

## 8. 调试与测试

### 8.1 启动 Agent

```bash
# 单任务模式
python main.py --task "控制战斗机A巡逻A空域"

# 交互模式
python main.py

# 跳过引擎连接检查
python main.py --skip-check --task "测试任务"
```

### 8.2 手动测试 API

```bash
# 健康检查
curl http://localhost:8080/api/health

# 获取世界态势
curl http://localhost:8080/api/world_state

# 控制平台飞行
curl -X POST http://localhost:8080/api/unit/战斗机A/platform/move_to_pos \
  -H "Content-Type: application/json" \
  -d '{"latitude": 39.0, "longitude": 116.0, "altitude": 8000}'
```

### 8.3 日志

日志文件保存在 `AiAgent/logs/` 目录:
- `ai_agent_YYYY-MM-DD.log` - 主日志
- 控制台同步输出

### 8.4 回放

所有 MCP 工具调用自动记录:
```python
from utils.replay import ReplayRecorder
recorder = ReplayRecorder()
# ... Agent 运行 ...
recorder.save("replay_session_001.json")
```

---

## 附录: 装备接口参数速查

### 雷达 (FzBaseRadar) Query 参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| IS_TURN_ON | Boolean | 开机状态 |
| IS_FAULT | Boolean | 故障状态 |
| RAD_TX_FEATURE | Struct | 发射特征（频率/功率/波束/增益） |

### 雷达 Alter 参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| TURN_ON_OFF | Boolean | 开关机 |
| TURN_ON | — | 开机 |
| TURN_OFF | — | 关机 |
| SET_FAULT | Boolean | 设置故障 |

### 干扰机 (FzComRadioJam) Control 参数
| 指令 | 参数 | 说明 |
|------|------|------|
| SAECMCmd | JAMTYPE, CENTERAZ, CENTEREL, AZRANGE, PHRANGE, TIME | 空对空干扰 |
| AGECMCmd | COUNTINE_TIME, JAM_TYPE, TARGET_TYPE, TARGET_NAME | 空对地干扰 |

### 平台 (FzFixedWing) Control 参数
| 指令 | 关键参数 | 说明 |
|------|----------|------|
| MoveToPos_LLA | Lat, Lon, Height, Speed, TurnG | 飞往经纬高 |
| MoveToDirection | Angle, Height, Speed, TurnG | 按航向飞行 |
| MoveInCruing | AirspaceName, Height, Speed | 空域巡逻 |
| ReturnLand | LAND_TYPE, AIRPORT_NAME | 返航 |
| MoveInFormation | LeaderID | 编队飞行 |
| LOCATE | LOCATION, ALTITUDE_AGL, HEADING, SPEED | 直接设置位置 |

### 武器系统 (FzAAMWeaponSys)
| 操作 | 参数 | 说明 |
|------|------|------|
| LOCK | EntityID | 锁定目标 |
| LAUNCH | EntityID | 发射 |
| ABORT | — | 中止交战 |
| LAUNCHNUM | Integer | 发射数量 |

### 通信 (FzComRadio) Query 参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| IS_TURN_ON | Boolean | 开机状态 |
| ComFreq | Real | 中心频率 |
| QueryComDevInfo | Struct | 设备完整参数 |
