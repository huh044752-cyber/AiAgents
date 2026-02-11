"""
回放支持模块
记录和回放 Agent 的所有 MCP 调用序列，支持实验可复现性
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from loguru import logger


class ReplayRecorder:
    """记录 MCP 调用序列，用于回放"""

    def __init__(self, session_id: str = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.records: list[dict] = []
        self.start_time = time.time()

    def record(self, tool_name: str, params: dict, result: Any, sim_time: float = 0.0):
        """记录一次工具调用"""
        entry = {
            "seq": len(self.records),
            "timestamp": time.time() - self.start_time,
            "sim_time": sim_time,
            "tool": tool_name,
            "params": params,
            "result": result,
        }
        self.records.append(entry)

    def save(self, output_dir: str = None):
        """保存回放记录到文件"""
        import config
        if output_dir is None:
            output_dir = config.replay.REPLAY_DIR

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filepath = output_path / f"replay_{self.session_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "session_id": self.session_id,
                    "start_time": self.start_time,
                    "total_calls": len(self.records),
                    "records": self.records,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info(f"Replay saved to {filepath}")
        return str(filepath)

    @classmethod
    def load(cls, filepath: str) -> "ReplayRecorder":
        """从文件加载回放记录"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        recorder = cls(session_id=data["session_id"])
        recorder.start_time = data["start_time"]
        recorder.records = data["records"]
        return recorder


# 全局 recorder 实例
_recorder: ReplayRecorder | None = None


def get_recorder() -> ReplayRecorder:
    """获取全局 recorder"""
    global _recorder
    if _recorder is None:
        _recorder = ReplayRecorder()
    return _recorder


def new_session(session_id: str = None) -> ReplayRecorder:
    """创建新的回放会话"""
    global _recorder
    _recorder = ReplayRecorder(session_id)
    return _recorder
