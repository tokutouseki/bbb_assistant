# RAG系统技术文档

## 一、工作概述

### 1.1 完成的修复工作

| 问题 | 修复内容 | 文件 |
|-----|---------|------|
| 模块导出错误 | 更新 `__init__.py` 导出正确的类名 | `modules/rag/__init__.py` |
| 类型注释错误 | `QdrantVectorStore` → `ChromaDBVectorStore` | `rag_engine.py` |
| 配置路径错误 | 数据路径从 `./data` 改为 `../data` | `settings.py` |
| jieba兼容性 | `jieba.lcut` → `list(jieba.cut)` | `index_manager.py` |
| 缺少配置项 | 添加 `embedding_model_path` 和 `embedding_offline_mode` | `settings.py`, `rag_engine.py` |
| API配置不一致 | 更新RAG API使用正确的配置 | `api/rag.py` |

### 1.2 新增功能

1. **本地模型支持** - 支持离线加载本地嵌入模型
2. **多种嵌入服务** - 支持 SentenceTransformer、OpenAI、智谱AI、Mock模式
3. **混合检索** - 结合向量检索和精确检索的优势

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        RAG Engine                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    RAGConfig                         │    │
│  │  - data_path: 知识库数据路径                          │    │
│  │  - chroma_persist_directory: 向量数据库路径           │    │
│  │  - embedding_model_path: 本地模型路径                 │    │
│  │  - embedding_offline_mode: 离线模式                   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Embedding    │  │ VectorStore  │  │ IndexManager │       │
│  │ Service      │  │ (ChromaDB)   │  │ (精确索引)    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                 │                 │                │
│         └─────────────────┼─────────────────┘                │
│                           │                                  │
│                    ┌──────┴──────┐                           │
│                    │  Retriever  │                           │
│                    │  (检索器)    │                           │
│                    └─────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、核心组件说明

### 3.1 RAGConfig 配置类

```python
from src.modules.rag import RAGConfig, RAGEngine, SearchMode

config = RAGConfig(
    data_path="../data",                    # 知识库数据目录
    index_path="../data/rag_index",         # 精确索引存储路径
    chroma_persist_directory="../data/chroma_db",  # ChromaDB路径
    chroma_collection="bbb_knowledge",      # 集合名称
    embedding_model="paraphrase-multilingual-MiniLM-L12-v2",  # 模型名
    embedding_model_path="./paraphrase-multilingual-MiniLM-L12-v2",  # 本地路径
    embedding_device="cpu",                 # 运行设备: cpu/cuda
    embedding_offline_mode=True,            # 离线模式
    default_top_k=5,                        # 默认返回数量
    default_mode=SearchMode.HYBRID,         # 默认检索模式
    context_max_length=2000                 # 上下文最大长度
)
```

### 3.2 检索模式

| 模式 | 说明 | 适用场景 |
|-----|------|---------|
| `SearchMode.FAST` | 向量相似度检索 | 语义搜索、模糊查询 |
| `SearchMode.PRECISE` | 关键词精确匹配 | 名称查询、分类过滤 |
| `SearchMode.HYBRID` | 混合检索（推荐） | 综合查询、最佳效果 |

### 3.3 核心类说明

#### RAGEngine - 主引擎
```python
class RAGEngine:
    async def initialize() -> bool           # 初始化引擎
    async def search(query, mode, top_k)     # 检索
    async def retrieve(query, top_k)         # 获取上下文
    async def index_knowledge_base()        # 索引知识库
    async def get_stats()                    # 获取统计
    async def health_check()                 # 健康检查
```

#### EmbeddingService - 嵌入服务
```python
class EmbeddingService:
    async def initialize() -> bool           # 初始化模型
    async def embed_single(text) -> List[float]    # 单文本嵌入
    async def embed_batch(texts) -> List[List[float]]  # 批量嵌入
    @property dimension -> int               # 向量维度
```

#### ChromaDBVectorStore - 向量存储
```python
class ChromaDBVectorStore:
    async def initialize() -> bool
    async def add_vectors(docs)              # 添加向量
    async def search(query_vector, top_k)    # 向量搜索
    async def delete_by_ids(ids)             # 删除向量
    async def get_count() -> int             # 获取数量
```

#### IndexManager - 精确索引
```python
class IndexManager:
    async def initialize() -> bool
    async def add_document(doc)              # 添加文档
    async def search(query, top_k)           # 精确搜索
    async def search_by_category(category)   # 分类搜索
    async def save_index()                   # 保存索引
```

---

## 四、使用方法

### 4.1 基本使用

```python
import asyncio
from src.modules.rag import RAGEngine, RAGConfig, SearchMode

async def main():
    # 1. 创建配置
    config = RAGConfig(
        data_path="../data",
        embedding_model_path="./paraphrase-multilingual-MiniLM-L12-v2",
        embedding_offline_mode=True
    )
    
    # 2. 初始化引擎
    engine = RAGEngine(config)
    await engine.initialize()
    
    # 3. 检索
    results = await engine.search(
        query="炽翎的技能介绍",
        mode=SearchMode.HYBRID,
        top_k=5
    )
    
    # 4. 处理结果
    for r in results:
        print(f"名称: {r.name}")
        print(f"分类: {r.category}/{r.subcategory}")
        print(f"分数: {r.score}")
        print(f"内容: {r.content[:200]}...")

asyncio.run(main())
```

### 4.2 检索结果结构

```python
@dataclass
class UnifiedSearchResult:
    id: str                    # 文档ID
    name: str                  # 文档名称
    content: str               # 文档内容
    category: str              # 主分类
    subcategory: Optional[str] # 子分类
    score: float               # 相关性分数
    match_type: str            # 匹配类型
    metadata: Dict[str, Any]   # 元数据
```

### 4.3 命令行工具

```bash
# 索引知识库
python scripts/index_knowledge.py

# 强制重新索引
python scripts/index_knowledge.py --force

# 索引特定分类
python scripts/index_knowledge.py --category 图鉴

# 测试检索
python scripts/index_knowledge.py --test "炽翎" --mode hybrid

# 查看统计
python scripts/index_knowledge.py --stats

# 交互式测试
python scripts/index_knowledge.py --interactive
```

---

## 五、API接口

### 5.1 搜索接口

**POST** `/api/rag/search`

请求体:
```json
{
    "query": "炽翎的技能介绍",
    "mode": "hybrid",
    "category": null,
    "top_k": 5
}
```

响应:
```json
{
    "success": true,
    "results": [
        {
            "id": "abc123",
            "name": "炽翎",
            "content": "...",
            "category": "图鉴",
            "subcategory": "女武神",
            "score": 0.95,
            "match_type": "name_exact"
        }
    ],
    "total": 5,
    "query": "炽翎的技能介绍",
    "mode": "hybrid"
}
```

### 5.2 上下文检索接口

**POST** `/api/rag/retrieve`

请求体:
```json
{
    "query": "如何培养炽翎",
    "top_k": 5,
    "max_length": 2000
}
```

响应:
```json
{
    "success": true,
    "context": "【炽翎】(图鉴/女武神)\n...",
    "length": 1500,
    "sources": 5
}
```

### 5.3 统计接口

**GET** `/api/rag/stats`

响应:
```json
{
    "initialized": true,
    "vector_store": {
        "name": "bbb_knowledge",
        "vectors_count": 2152,
        "dimension": 384
    },
    "index": {
        "total_documents": 3334,
        "total_keywords": 5562,
        "categories": {
            "图鉴": 1983,
            "档案": 628,
            "第二部探索指南": 401
        }
    },
    "embedding": {
        "model_type": "sentence_transformer",
        "model_name": "paraphrase-multilingual-MiniLM-L12-v2",
        "dimension": 384
    }
}
```

### 5.4 健康检查接口

**GET** `/api/rag/health`

响应:
```json
{
    "healthy": true,
    "components": {
        "embedding": "ok",
        "vector_store": "ok",
        "index_manager": "ok"
    }
}
```

---

## 六、知识库数据结构

### 6.1 目录结构

```
data/
├── 图鉴/
│   ├── 女武神/
│   │   ├── 炽翎.json
│   │   ├── 炽翎.txt
│   │   └── ...
│   ├── 圣痕/
│   ├── 武器/
│   └── ...
├── 档案/
│   ├── 故事/
│   ├── 壁纸/
│   └── ...
├── 第二部探索指南/
│   ├── 成就/
│   ├── 收藏品/
│   └── ...
└── rag_index/
    └── precise_index.json
```

### 6.2 JSON文件格式

```json
{
    "name": "炽翎",
    "main_content": "角色评价技能介绍...",
    "html_content": "<div>...</div>",
    "media_resources": [
        {
            "url": "https://...",
            "type": "image",
            "local_path": "data/图鉴/女武神/media/炽翎.png"
        }
    ]
}
```

---

## 七、配置说明

### 7.1 settings.py 配置项

```python
# RAG配置
rag_enabled: bool = True                    # 启用RAG
rag_data_path: str = "../data"              # 知识库路径
rag_index_path: str = "../data/rag_index"   # 索引路径
rag_default_mode: str = "hybrid"            # 默认模式
rag_default_top_k: int = 5                  # 默认返回数
rag_context_max_length: int = 2000          # 上下文长度

# ChromaDB配置
chroma_persist_directory: str = "../data/chroma_db"
chroma_collection: str = "bbb_knowledge"

# 嵌入模型配置
embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
embedding_model_path: str = "./paraphrase-multilingual-MiniLM-L12-v2"
embedding_device: str = "cpu"               # cpu 或 cuda
embedding_offline_mode: bool = True         # 离线模式
```

### 7.2 环境变量 (.env)

```env
# 可选：覆盖默认配置
RAG_DATA_PATH=../data
EMBEDDING_DEVICE=cuda
EMBEDDING_OFFLINE_MODE=true
```

---

## 八、性能优化建议

1. **使用GPU** - 设置 `embedding_device="cuda"` 可显著提升嵌入速度
2. **批量处理** - 使用 `embed_batch()` 而非多次 `embed_single()`
3. **缓存利用** - 嵌入结果会自动缓存，重复查询更快
4. **索引优化** - 定期运行 `--force` 重建索引保持最佳性能

---

## 九、故障排除

### 9.1 常见问题

| 问题 | 解决方案 |
|-----|---------|
| 模型加载失败 | 检查 `embedding_model_path` 是否正确 |
| 向量数量为0 | 运行 `python scripts/index_knowledge.py` |
| 检索无结果 | 检查知识库数据是否正确加载 |
| 内存不足 | 减小 `batch_size` 或使用更小的模型 |

### 9.2 日志查看

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 十、版本信息

- **RAG模块版本**: 1.0.0
- **嵌入模型**: paraphrase-multilingual-MiniLM-L12-v2
- **向量维度**: 384
- **向量数据库**: ChromaDB
- **支持语言**: 中文、英文等多语言
