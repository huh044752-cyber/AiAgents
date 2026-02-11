"""
AI Agent 主入口
负责初始化系统、连接仿真引擎、启动 Agent
"""
import sys
import time
import argparse
from loguru import logger

import config
from mcp.client import get_client
from utils.replay import new_session, get_recorder
from agent.graph import run_agent, create_agent_graph


def check_engine_connection() -> bool:
    """检查仿真引擎连接状态"""
    client = get_client()
    logger.info(f"正在连接仿真引擎: {config.sim_engine.base_url}")

    for attempt in range(3):
        if client.health_check():
            logger.info("仿真引擎连接成功!")
            return True
        logger.warning(f"连接失败，重试 ({attempt + 1}/3)...")
        time.sleep(2)

    logger.error("无法连接到仿真引擎，请确认:")
    logger.error(f"  1. C++ 仿真引擎已启动")
    logger.error(f"  2. AiHttpService 已加载")
    logger.error(f"  3. 地址正确: {config.sim_engine.base_url}")
    return False


def interactive_mode():
    """交互模式 - 通过命令行输入任务指令"""
    logger.info("========================================")
    logger.info("  AI 飞行仿真 Agent - 交互模式")
    logger.info("========================================")
    logger.info("输入任务指令，Agent 将自动执行")
    logger.info("输入 'quit' 退出, 'status' 查看仿真状态")
    logger.info("输入 'units' 查看所有单元")
    logger.info("========================================")

    client = get_client()

    while True:
        try:
            task = input("\n> 请输入任务指令: ").strip()

            if not task:
                continue

            if task.lower() == "quit":
                logger.info("退出 Agent")
                break

            if task.lower() == "status":
                status = client.get("/api/simulation/status")
                logger.info(f"仿真状态: {status}")
                continue

            if task.lower() == "units":
                units = client.get("/api/units")
                for u in units.get("units", []):
                    status_str = "激活" if u.get("active") else "未激活"
                    logger.info(f"  {u.get('unit_name')} [{u.get('forceside')}] - {status_str}")
                logger.info(f"共 {units.get('count', 0)} 个单元")
                continue

            if task.lower().startswith("state "):
                unit_name = task[6:].strip()
                state = client.get(f"/api/unit/{unit_name}/state")
                if "error" in state:
                    logger.error(f"错误: {state['error']}")
                else:
                    pos = state.get("position", {})
                    ori = state.get("orientation", {})
                    logger.info(f"单元: {state.get('unit_name')} [{state.get('forceside')}]")
                    logger.info(f"  位置: ({pos.get('latitude', 0):.6f}, {pos.get('longitude', 0):.6f}, {pos.get('altitude', 0):.1f}m)")
                    logger.info(f"  姿态: 航向={ori.get('heading', 0):.1f}, 俯仰={ori.get('pitch', 0):.1f}, 滚转={ori.get('roll', 0):.1f}")
                    logger.info(f"  速度: {state.get('speed', 0):.1f} m/s")
                    for eq in state.get("equipment", []):
                        logger.info(f"  装备: {eq.get('entity_name')} [{eq.get('type')}] - {eq.get('status')}")
                continue

            # 创建新的回放会话
            new_session()

            # 运行 Agent
            logger.info(f"开始执行任务: {task}")
            result = run_agent(task)

            if result:
                logger.info("任务执行完毕")
            else:
                logger.warning("任务执行异常")

        except KeyboardInterrupt:
            logger.info("\n收到中断信号，退出...")
            break
        except Exception as e:
            logger.error(f"执行异常: {e}")
            import traceback
            traceback.print_exc()


def single_task_mode(task: str):
    """单任务模式 - 执行一个任务后退出"""
    logger.info(f"单任务模式: {task}")

    new_session()
    result = run_agent(task)

    if result:
        logger.info("任务执行完毕")
    else:
        logger.warning("任务执行异常")

    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI 飞行仿真 Agent")
    parser.add_argument(
        "--task", "-t",
        type=str,
        help="直接执行的任务指令（不指定则进入交互模式）",
    )
    parser.add_argument(
        "--max-iterations", "-m",
        type=int,
        default=None,
        help=f"最大迭代次数（默认: {config.agent.MAX_ITERATIONS}）",
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="跳过引擎连接检查",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="仿真引擎地址",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="仿真引擎端口",
    )

    args = parser.parse_args()

    # 覆盖配置
    if args.host:
        config.sim_engine.HOST = args.host
    if args.port:
        config.sim_engine.PORT = args.port
    if args.max_iterations:
        config.agent.MAX_ITERATIONS = args.max_iterations

    logger.info("AI 飞行仿真 Agent 启动中...")
    logger.info(f"仿真引擎地址: {config.sim_engine.base_url}")
    logger.info(f"LLM 模型: {config.llm.MODEL_NAME}")

    # 检查引擎连接
    if not args.skip_check:
        if not check_engine_connection():
            logger.warning("跳过引擎连接检查，进入离线模式")
            logger.warning("（MCP 工具调用将返回连接错误）")

    # 执行模式
    if args.task:
        single_task_mode(args.task)
    else:
        interactive_mode()

    # 清理
    get_client().close()
    logger.info("Agent 已关闭")


if __name__ == "__main__":
    main()
