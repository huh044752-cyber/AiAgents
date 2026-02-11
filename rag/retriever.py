"""
战术 RAG 检索系统
基于本地文档的检索增强生成，为 Agent 决策提供战术知识支持

知识来源:
- 战术条令与战法
- 装备使用手册（雷达/干扰机/武器/通信）
- 历史空战案例
- 电子战对抗策略
"""
import os
import json
from pathlib import Path
from typing import Optional
from loguru import logger

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config


class TacticalRAG:
    """战术知识 RAG 检索器"""

    def __init__(self, persist_dir: str = None, knowledge_dir: str = None):
        self.persist_dir = persist_dir or config.rag.VECTOR_STORE_DIR
        self.knowledge_dir = Path(knowledge_dir or config.rag.KNOWLEDGE_BASE_DIR)
        self.vectorstore: Optional[FAISS] = None
        self.embeddings = None
        self._initialized = False

    def initialize(self):
        """初始化 RAG 系统"""
        if self._initialized:
            return

        logger.info("[RAG] 初始化战术知识库...")

        # 创建 embeddings
        try:
            self.embeddings = DashScopeEmbeddings(
                model=config.rag.EMBEDDING_MODEL,
                dashscope_api_key=config.llm.DASHSCOPE_API_KEY,
            )
        except Exception as e:
            logger.warning(f"[RAG] DashScope Embeddings 初始化失败: {e}，使用降级搜索")
            self._initialized = True
            return

        # 尝试加载已有向量库
        if os.path.exists(self.persist_dir):
            try:
                self.vectorstore = FAISS.load_local(
                    self.persist_dir, self.embeddings, allow_dangerous_deserialization=True
                )
                logger.info("[RAG] 已加载现有向量库")
                self._initialized = True
                return
            except Exception as e:
                logger.warning(f"[RAG] 加载向量库失败: {e}，重新构建")

        # 构建新向量库
        documents = self._load_knowledge_documents()
        if documents:
            # 分块
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=config.rag.CHUNK_SIZE,
                chunk_overlap=config.rag.CHUNK_OVERLAP,
                separators=["\n## ", "\n### ", "\n\n", "\n", "。", "；"],
            )
            chunks = splitter.split_documents(documents)
            logger.info(f"[RAG] 分块完成: {len(chunks)} 个片段")

            # 构建向量库
            try:
                self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
                # 持久化
                os.makedirs(self.persist_dir, exist_ok=True)
                self.vectorstore.save_local(self.persist_dir)
                logger.info(f"[RAG] 向量库构建完成，保存到 {self.persist_dir}")
            except Exception as e:
                logger.error(f"[RAG] 向量库构建失败: {e}")
        else:
            logger.warning("[RAG] 没有找到知识文档")

        self._initialized = True

    def _load_knowledge_documents(self) -> list[Document]:
        """加载知识库文档"""
        documents = []

        if not self.knowledge_dir.exists():
            logger.warning(f"[RAG] 知识库目录不存在: {self.knowledge_dir}")
            return documents

        for filepath in self.knowledge_dir.glob("*.md"):
            try:
                content = filepath.read_text(encoding="utf-8")
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": filepath.name,
                        "category": self._categorize_doc(filepath.name),
                    },
                )
                documents.append(doc)
                logger.info(f"[RAG] 加载文档: {filepath.name}")
            except Exception as e:
                logger.error(f"[RAG] 加载文档失败 {filepath}: {e}")

        # 加载 JSON 格式的知识
        for filepath in self.knowledge_dir.glob("*.json"):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        content = item.get("content", json.dumps(item, ensure_ascii=False))
                        doc = Document(
                            page_content=content,
                            metadata={
                                "source": filepath.name,
                                "category": item.get("category", "general"),
                            },
                        )
                        documents.append(doc)
                logger.info(f"[RAG] 加载文档: {filepath.name}")
            except Exception as e:
                logger.error(f"[RAG] 加载文档失败 {filepath}: {e}")

        return documents

    @staticmethod
    def _categorize_doc(filename: str) -> str:
        """根据文件名推断文档类别
        分类定义统一在 ui/ui_config/doc_categories.json 中维护
        优先从 JSON 配置加载，回退到内置规则
        """
        name_lower = filename.lower()
        # 尝试从 JSON 配置文件直接加载
        try:
            import json as _json
            _cfg_path = Path(__file__).resolve().parent.parent / "ui" / "ui_config" / "doc_categories.json"
            if _cfg_path.exists():
                _data = _json.loads(_cfg_path.read_text(encoding="utf-8"))
                categories = _data.get("categories", {})
                for cat_key, cat_info in categories.items():
                    if cat_key == "general":
                        continue
                    for kw in cat_info.get("keywords", []):
                        if kw in name_lower:
                            return cat_key
                return "general"
        except Exception:
            pass

        # 回退: 使用内置规则
        rules = [
            ("tactics",         ["tactic", "战术", "条令", "战法"]),
            ("radar_manual",    ["radar", "雷达"]),
            ("ew_manual",       ["jam", "干扰", "电子战", "ecm"]),
            ("weapon_manual",   ["weapon", "武器", "弹药", "导弹"]),
            ("comm_manual",     ["comm", "通信", "数据链"]),
            ("historical_case", ["case", "案例", "历史"]),
            ("flight_manual",   ["flight", "飞行", "航路", "空域"]),
        ]
        for cat_key, keywords in rules:
            for kw in keywords:
                if kw in name_lower:
                    return cat_key
        return "general"

    def retrieve(self, query: str, k: int = None, category: str = None) -> list[Document]:
        """检索相关知识

        Args:
            query: 查询文本
            k: 返回结果数量（默认读取配置 RAG_RETRIEVE_TOP_K）
            category: 可选的类别过滤

        Returns:
            相关文档列表
        """
        if k is None:
            k = config.rag.RETRIEVE_TOP_K

        if not self._initialized:
            self.initialize()

        if self.vectorstore is None:
            return self._fallback_search(query, category)

        try:
            if category:
                results = self.vectorstore.similarity_search(
                    query, k=k * 2,
                    filter={"category": category},
                )
                return results[:k]
            else:
                return self.vectorstore.similarity_search(query, k=k)
        except Exception as e:
            logger.error(f"[RAG] 检索失败: {e}")
            return self._fallback_search(query, category)

    def retrieve_with_scores(self, query: str, k: int = None) -> list[tuple[Document, float]]:
        """检索并返回相关性分数"""
        if k is None:
            k = config.rag.RETRIEVE_TOP_K

        if not self._initialized:
            self.initialize()

        if self.vectorstore is None:
            return [(doc, 0.5) for doc in self._fallback_search(query)]

        try:
            return self.vectorstore.similarity_search_with_score(query, k=k)
        except Exception as e:
            logger.error(f"[RAG] 检索失败: {e}")
            return [(doc, 0.5) for doc in self._fallback_search(query)]

    def get_context_for_agent(self, query: str, k: int = None) -> str:
        """获取格式化的上下文文本，供 Agent 使用"""
        if k is None:
            k = config.rag.RETRIEVE_TOP_K

        docs = self.retrieve(query, k=k)
        if not docs:
            return "（无相关战术知识）"

        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "未知")
            category = doc.metadata.get("category", "general")
            context_parts.append(f"[知识{i}] ({category} - {source})\n{doc.page_content}")

        return "\n\n".join(context_parts)

    def _fallback_search(self, query: str, category: str = None) -> list[Document]:
        """降级搜索（当向量库不可用时，直接读取文档文件做关键词匹配）"""
        all_docs = self._load_knowledge_documents()
        if not all_docs:
            logger.warning("[RAG] 降级搜索: knowledge_base 目录无文档可用")
            return []

        results = []
        query_lower = query.lower()
        keywords = [kw.strip() for kw in query_lower.replace("，", " ").replace("、", " ").split() if len(kw.strip()) > 0]

        for doc in all_docs:
            doc_cat = doc.metadata.get("category", "")
            if category and doc_cat != category:
                continue
            content_lower = doc.page_content.lower()
            if any(kw in content_lower for kw in keywords):
                results.append(doc)

        if results:
            return results[:5]
        return all_docs[:3]

    def rebuild(self):
        """重建向量库"""
        self._initialized = False
        if os.path.exists(self.persist_dir):
            import shutil
            shutil.rmtree(self.persist_dir)
        self.vectorstore = None
        self.initialize()


# 全局 RAG 实例
_rag: Optional[TacticalRAG] = None


def get_rag() -> TacticalRAG:
    """获取全局 RAG 实例"""
    global _rag
    if _rag is None:
        _rag = TacticalRAG()
    return _rag
