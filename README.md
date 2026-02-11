## AI 飞行仿真 Agent（Python 侧）

一个面向空战仿真场景的智能体项目，负责通过 HTTP 接口控制仿真引擎中的飞行平台、雷达、电子战设备、通信和武器系统，实现“像飞行员一样下达指令、自动选择战术并执行”的能力。

### 功能概览

- **智能决策 Agent**：基于 LangGraph/LangChain 构建的多节点决策流程（指挥、战术选择、执行）。
- **MCP 工具层**：将引擎暴露的 REST API 封装为可被 LLM 调用的工具。
- **技能层（Skills）**：在工具之上组合出常用战术动作，例如雷达开关、干扰机控制、飞行机动、武器发射等。
- **RAG 战术知识库**：支持从本地战术/装备文档中检索知识，辅助决策解释与方案选择。
- **Web 控制台（UI）**：使用 Streamlit 实现的对话式控制台，可下达任务、查看知识库与配置。

### 目录结构（Python 项目）

- `main.py`：命令行入口，可交互或单次执行任务。
- `config.py`：配置加载与环境变量封装。
- `agent/`：Agent 流程与状态定义。
- `mcp/`：HTTP 客户端与工具封装。
- `skills/`：各类战术技能实现。
- `rag/`：知识检索与本地文档。
- `ui/`：Web 控制台与界面配置。
- `utils/`：日志、回放等通用工具。
- `docs/`：项目相关文档与说明。

### 快速开始

1. 安装依赖：

   ```bash
   cd AiAgent
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. 配置环境变量：

   - 复制 `.env.example` 为 `.env`；
   - 填写大模型 API Key、仿真引擎地址等配置。

3. 启动 Web 控制台：

   ```bash
   streamlit run ui/app.py
   ```

4. 启动命令行 Agent（可选）：

   ```bash
   python main.py --task "控制某架战斗机在指定空域巡逻"
   ```

### 文档与二次开发

- 更深入的架构说明、接口清单和开发流程，请参见仓库中的 `docs` 目录。
- 所有 UI 文本、主题、快捷指令等均通过 `ui/ui_config/` 下的 JSON 配置热加载，适合根据自身场景定制。

