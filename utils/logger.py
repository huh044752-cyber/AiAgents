"""
日志记录模块
支持控制台输出和文件记录，用于 Agent 决策审计和回放
"""
import sys
import json
from datetime import datetime
from pathlib import Path
from loguru import logger

import config


def setup_logger():
    """初始化日志系统"""
    # 移除默认 handler
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stderr,
        level=config.log.LEVEL,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )

    # 文件日志
    log_dir = Path(config.log.LOG_DIR)
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.add(
        log_dir / f"agent_{timestamp}.log",
        level=config.log.FILE_LEVEL,
        rotation=config.log.ROTATION,
        retention=config.log.RETENTION,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    return logger


def log_decision(agent_name: str, decision: dict):
    """记录 Agent 决策，用于审计"""
    logger.info(f"[{agent_name}] Decision: {json.dumps(decision, ensure_ascii=False, indent=2)}")


def log_mcp_call(tool_name: str, params: dict, result: dict):
    """记录 MCP 工具调用"""
    logger.info(f"[MCP] {tool_name}({json.dumps(params, ensure_ascii=False)}) -> {json.dumps(result, ensure_ascii=False)[:500]}")


# 初始化
setup_logger()
