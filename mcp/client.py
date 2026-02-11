"""
HTTP 客户端封装
负责与 C++ AiHttpService 通信
"""
import httpx
from loguru import logger
from typing import Any, Optional

import config


class SimEngineClient:
    """C++ 仿真引擎 HTTP 客户端"""

    def __init__(self, base_url: str = None, timeout: float = None):
        self.base_url = base_url or config.sim_engine.base_url
        self.timeout = timeout if timeout is not None else config.sim_engine.HTTP_TIMEOUT
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.Client:
        """获取同步 HTTP 客户端（惰性创建）"""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    @property
    def async_client(self) -> httpx.AsyncClient:
        """获取异步 HTTP 客户端（惰性创建）"""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._async_client

    def get(self, path: str, params: dict = None) -> dict:
        """同步 GET 请求"""
        try:
            response = self.client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.error(f"无法连接到仿真引擎: {self.base_url}{path}")
            return {"error": f"Connection refused: {self.base_url}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 错误: {e.response.status_code} - {path}")
            try:
                return e.response.json()
            except Exception:
                return {"error": str(e)}
        except Exception as e:
            logger.error(f"请求异常: {e}")
            return {"error": str(e)}

    def post(self, path: str, data: dict = None) -> dict:
        """同步 POST 请求"""
        try:
            response = self.client.post(path, json=data or {})
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.error(f"无法连接到仿真引擎: {self.base_url}{path}")
            return {"error": f"Connection refused: {self.base_url}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 错误: {e.response.status_code} - {path}")
            try:
                return e.response.json()
            except Exception:
                return {"error": str(e)}
        except Exception as e:
            logger.error(f"请求异常: {e}")
            return {"error": str(e)}

    async def async_get(self, path: str, params: dict = None) -> dict:
        """异步 GET 请求"""
        try:
            response = await self.async_client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.error(f"无法连接到仿真引擎: {self.base_url}{path}")
            return {"error": f"Connection refused: {self.base_url}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 错误: {e.response.status_code} - {path}")
            try:
                return e.response.json()
            except Exception:
                return {"error": str(e)}
        except Exception as e:
            logger.error(f"请求异常: {e}")
            return {"error": str(e)}

    async def async_post(self, path: str, data: dict = None) -> dict:
        """异步 POST 请求"""
        try:
            response = await self.async_client.post(path, json=data or {})
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            logger.error(f"无法连接到仿真引擎: {self.base_url}{path}")
            return {"error": f"Connection refused: {self.base_url}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 错误: {e.response.status_code} - {path}")
            try:
                return e.response.json()
            except Exception:
                return {"error": str(e)}
        except Exception as e:
            logger.error(f"请求异常: {e}")
            return {"error": str(e)}

    def health_check(self) -> bool:
        """检查仿真引擎是否可连接"""
        result = self.get("/api/health")
        return result.get("status") == "ok"

    def close(self):
        """关闭客户端连接"""
        if self._client:
            self._client.close()
            self._client = None
        if self._async_client:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._async_client.aclose())
                else:
                    loop.run_until_complete(self._async_client.aclose())
            except Exception:
                pass
            self._async_client = None

    def __del__(self):
        self.close()


# 全局客户端实例
_client: Optional[SimEngineClient] = None


def get_client() -> SimEngineClient:
    """获取全局客户端实例"""
    global _client
    if _client is None:
        _client = SimEngineClient()
    return _client
