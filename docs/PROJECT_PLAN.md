# AI 飞行仿真 Agent 项目规划

## 项目概述

将 AI 决策能力集成到 C++ 飞行仿真引擎中，AI 以"飞行员"角色通过受控接口操纵仿真实体，不直接修改物理模型。

### 架构总览

```
┌──────────────────────────────────────────────────────┐
│  AI Agent (Python, LangGraph)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Commander    │→ │ Tactical     │→ │ Executor   │ │
│  │ (指挥决策)   │  │ (战术选择)   │  │ (技能执行) │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
│       ↑ RAG                              ↓           │
│  ┌──────────────┐              ┌──────────────────┐  │
│  │ 战术知识库   │              │ Skills 技能层    │  │
│  │ (条令/手册)  │              │ (武器/飞行/EW)   │  │
│  └──────────────┘              └──────────────────┘  │
│                                       ↓              │
│                          ┌──────────────────┐        │
│                          │ MCP Tools 工具层 │        │
│                          │ (HTTP API 封装)  │        │
│                          └──────────────────┘        │
└──────────────────────────┬───────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────┴───────────────────────────┐
│  C++ Simulation Engine                                │
│  ┌──────────────────────────────────────────────────┐│
│  │ AiHttpService (cpp-httplib + nlohmann/json)     ││
│  │ 24个 REST API 端点                               ││
│  └──────────────────────────────────────────────────┘│
│  ┌──────────────┐ ┌────────────┐ ┌────────────────┐ │
│  │ FOSimEngine  │ │ Equipment  │ │ Services       │ │
│  │ (引擎核心)   │ │ (装备模型) │ │ (服务模块)     │ │
│  └──────────────┘ └────────────┘ └────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 已完成工作

### Phase 1: 基础框架搭建 ✅

| 任务 | 状态 | 说明 |
|------|------|------|
| C++ AiHttpService 服务框架 | ✅ | 继承 CyberServiceImpl，注册到引擎 |
| HTTP 服务器 (cpp-httplib) | ✅ | 独立线程运行，支持 CORS |
| JSON 序列化 (nlohmann/json) | ✅ | 请求/响应 JSON 格式化 |
| 基础查询接口 (5个) | ✅ | 健康检查、仿真状态、世界态势、单元列表、装备查询 |
| 基础控制接口 (3个) | ✅ | 装备控制、单元修改、任务下达 |

### Phase 2: Python AI Agent 框架 ✅

| 任务 | 状态 | 说明 |
|------|------|------|
| MCP 工具层 (8个基础工具) | ✅ | HTTP 客户端 + Pydantic Schema |
| LangGraph Agent 框架 | ✅ | Commander → Tactical → Executor 流水线 |
| 基础 Skills (机动/雷达/干扰/通信) | ✅ | 5类共10个技能函数 |
| 日志与回放系统 | ✅ | loguru + ReplayRecorder |
| 配置管理 | ✅ | .env + config.py |

### Phase 3: 接口扩展与 RAG ✅ (当前阶段)

| 任务 | 状态 | 说明 |
|------|------|------|
| C++ 平台飞行控制接口 (6个) | ✅ | 航路/方向/巡逻/返航/编队/定位 |
| C++ 雷达详情接口 | ✅ | 发射特征参数查询 |
| C++ 干扰机控制接口 (2个) | ✅ | 详情查询 + 干扰指令 |
| C++ 武器系统接口 (4个) | ✅ | 状态/锁定/发射/中止 |
| C++ 通信详情接口 | ✅ | 频率参数查询 |
| Python MCP 新工具 (14个) | ✅ | 对应所有新 C++ 端点 |
| 武器技能 (weapon.py) | ✅ | BVR攻击 + 中止交战 |
| 飞行控制技能 (flight.py) | ✅ | 6个飞行控制技能 |
| RAG 战术知识检索 | ✅ | FAISS + DashScope Embeddings |
| 战术知识库文档 (5篇) | ✅ | 条令/雷达/电子战/武器/案例 |
| Commander 集成 RAG | ✅ | 决策前自动检索相关知识 |

---

## 未来规划

### Phase 4: 多 Agent 对抗

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 红蓝双方 Agent 实例 | 高 | 分别控制对抗双方 |
| Agent 间通信协议 | 高 | 编队内协同通信 |
| 对抗评估指标 | 中 | 胜负判定、效能评估 |
| 态势评估模型 | 中 | 威胁评估算法 |

### Phase 5: 高级决策

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 强化学习集成 | 中 | RL + LLM 混合决策 |
| 决策树可视化 | 低 | 决策过程可视化展示 |
| 在线学习 | 低 | 从对抗中自我进化 |
| 更多战术知识 | 中 | 扩展知识库覆盖范围 |

### Phase 6: 生产化

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 性能优化 | 高 | HTTP 连接池、批量请求 |
| 错误恢复 | 高 | 断连重试、状态恢复 |
| Web UI 监控面板 | 中 | 实时态势展示 |
| Docker 容器化 | 低 | 一键部署 |

---

## 接口清单 (24个 REST API)

### 查询接口 (10个)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/simulation/status` | 仿真状态 |
| GET | `/api/world_state` | 全局态势 |
| GET | `/api/units` | 所有单元列表 |
| GET | `/api/unit/{name}/state` | 单元详细状态 |
| GET | `/api/unit/{name}/equipment/{entity}/query` | 装备参数查询 |
| GET | `/api/unit/{name}/radar/{entity}/detail` | 雷达详细参数 |
| GET | `/api/unit/{name}/jammer/{entity}/detail` | 干扰机详细参数 |
| GET | `/api/unit/{name}/weapon/{entity}/status` | 武器系统状态 |
| GET | `/api/unit/{name}/comm/{entity}/detail` | 通信设备详情 |

### 控制接口 (14个)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/unit/{name}/equipment/{entity}/control` | 通用装备控制 |
| POST | `/api/unit/{name}/alter` | 单元状态修改 |
| POST | `/api/unit/{name}/mission` | 任务下达 |
| POST | `/api/unit/{name}/platform/move_to_pos` | 飞往坐标点 |
| POST | `/api/unit/{name}/platform/move_to_dir` | 按航向飞行 |
| POST | `/api/unit/{name}/platform/patrol` | 空域巡逻 |
| POST | `/api/unit/{name}/platform/return_land` | 返航着陆 |
| POST | `/api/unit/{name}/platform/formation` | 编队飞行 |
| POST | `/api/unit/{name}/platform/locate` | 直接设置位置 |
| POST | `/api/unit/{name}/jammer/{entity}/command` | 干扰指令 |
| POST | `/api/unit/{name}/weapon/{entity}/lock` | 武器锁定目标 |
| POST | `/api/unit/{name}/weapon/{entity}/launch` | 武器发射 |
| POST | `/api/unit/{name}/weapon/{entity}/abort` | 中止交战 |

---

## 技术栈

### C++ 侧
- **引擎**: FOSimEngine (CyberServiceImpl 插件架构)
- **HTTP**: cpp-httplib (header-only)
- **JSON**: nlohmann/json (header-only)
- **编译**: MSVC / CMake

### Python 侧
- **Agent**: LangGraph + LangChain
- **LLM**: 通义千问 (DashScope API)
- **RAG**: FAISS + DashScope Embeddings
- **HTTP**: httpx
- **Schema**: Pydantic v2
- **日志**: loguru
