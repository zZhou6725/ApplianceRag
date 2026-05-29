# ApplianceRAG — 工程化 Agent 智能客服系统

基于 **LangGraph 状态编排 + Harness 驾驭层 + Skill 技能体系** 的智能客服系统，面向扫地机器人售后场景，支持多轮对话、知识库检索、长期记忆、报告导出。

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| CLI 入口 | Python argparse (单次查询 / 交互式 / 评测) |
| 编排层 | LangGraph StateGraph (意图分类 → 技能调度 → 记忆召回 → 结果生成) |
| 驾驭层 | Harness Engineering (Prompt 管理 / 上下文拼接 / 异常兜底 / 结果校验 / 重试 / 缓存) |
| 技能层 | Pluggable Skill (RAG / 天气 / 报告 / 用户数据，统一 BaseSkill 接口) |
| 记忆层 | ChromaDB 对话向量化 + LLM 摘要 (Long-term memory) |
| 缓存层 | 可插拔 CacheManager (Memory / Redis，自动降级) |
| AI 引擎 | 通义千问 Qwen3-Max (DashScope) |
| RAG | LangChain + ChromaDB (向量检索 + LLM 摘要) |
| Embedding | DashScope text-embedding-v4 |
| API 框架 | FastAPI + Uvicorn (异步) |
| 数据库 | SQLite (开发) / 可切换 PostgreSQL |
| 前端 | Vue 3 + TypeScript + Vite |
| 配置 | Pydantic-Settings + YAML + .env |

## 功能清单

- **CLI 命令行**: 单次查询、交互式 REPL、评测模式，一行命令启动完整 Agent
- **LangGraph 编排**: 状态机驱动的意图识别 → 技能调度 → 结果校验 → 输出生成，支持重试回路
- **Harness 驾驭层**: Prompt 模板管理 (lru_cache)、上下文拼接 (多轮历史限制)、异常捕获 (超时+兜底)、参数校验、结果校验+重试
- **Skill 技能体系**: RAG 检索、天气查询、报告生成、用户数据 — 四大技能统一 BaseSkill 接口，可插拔、可单独调试
- **长期记忆**: 对话自动摘要 → ChromaDB 向量化 → 语义召回 → 注入上下文，让 Agent 记住对话历史
- **可插拔缓存**: CacheManager 支持 Memory / Redis 后端，Redis 不可用时自动降级
- **智能对话**: 意图分类路由到对应 Skill，LLM 基于 Skill 结果生成自然语言回答
- **知识库 RAG**: 文档加载 → 切片 → 向量库 → 语义检索 → LLM 总结
- **流式响应**: CLI token-by-token 流式输出 + FastAPI SSE 流式接口
- **对话管理**: 创建/列表/详情/删除会话，消息持久化
- **报告导出**: 对话记录导出为 Markdown / PDF
- **评测体系**: CLI 内置评测 + RAG 检索质量评测 (Recall@K / Hit Rate / MRR)
- **安全基线**: 限流、安全响应头、日志脱敏、CORS 白名单

## 快速启动

### 环境要求

- Python 3.11+、Node.js 18+
- DashScope API Key ([阿里云百炼](https://bailian.console.aliyun.com/))
- 高德地图 API Key ([高德开放平台](https://lbs.amap.com/))

### 1. 克隆项目

```bash
git clone <repo-url>
cd ApplianceRAG
```

### 2. 后端服务

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 DASHSCOPE_API_KEY 和 AMAP_API_KEY

# 初始化知识库 (可选)
python scripts/ingest_knowledge.py

# 启动 FastAPI 服务
uvicorn app.api.main:app --reload --port 8000
```

服务启动后访问 http://localhost:8000/docs 查看 Swagger API 文档。

### 3. CLI 命令行（新增）

```bash
# 单次查询（流式输出）
python cli.py "扫地机器人滤网怎么清洗？"

# 交互式多轮对话
python cli.py -i

# 评测模式（内置 6 个测试用例）
python cli.py -e

# 自定义评测用例
python cli.py -e --cases my_cases.json

# Redis 缓存模式（需 Redis 服务）
python cli.py --cache redis "问题"

# 禁用长期记忆
python cli.py --no-memory "问题"

# 查看缓存/记忆统计
python cli.py "问题" --stats
```

交互模式下可用命令：`/quit` 退出、`/clear` 清空历史、`/stats` 查看统计、`/memory` 列出记忆。

### 4. 前端界面

```bash
cd frontend

npm install
npm run dev
```

访问 http://localhost:5173 进入聊天界面。

## 项目架构

```
backend/
├── cli.py                      # CLI 命令行入口 (3 模式)
│
├── graph/                      # LangGraph 状态编排层
│   ├── state.py                # AgentState TypedDict 定义
│   ├── nodes.py                # 图节点 (recall/classify/dispatch/assemble/generate/store)
│   └── agent_graph.py          # StateGraph 构建 + AgentGraph 外观类
│
├── harness/                    # Harness 驾驭层
│   ├── prompt_manager.py       # 提示词模板加载 (lru_cache) + 变量注入
│   ├── context_builder.py      # 多轮对话上下文拼接 + ConversationState
│   ├── error_handler.py        # 全局异常捕获 + 超时 + 兜底回复
│   ├── tool_router.py          # 关键词意图分类 + 技能路由
│   ├── result_validator.py     # 结果校验 + 重试决策
│   ├── cache_manager.py        # 可插拔缓存 (MemoryCache / RedisCache)
│   └── memory_manager.py       # 长期记忆 (对话摘要 → ChromaDB → 语义召回)
│
├── skills/                     # Skill 技能体系
│   ├── base.py                 # BaseSkill ABC + SkillResult + 注册表
│   ├── rag_skill.py            # RAG 知识库检索技能
│   ├── weather_skill.py        # 天气查询技能 (高德 API)
│   ├── user_skill.py           # 用户数据查询技能
│   └── report_skill.py         # 月度报告生成技能
│
├── app/                        # 原有 FastAPI 应用层 (零改动)
│   ├── api/                    # 接口层 (路由 + 中间件)
│   │   ├── main.py             # FastAPI 应用入口
│   │   └── routes/             # 路由模块 (chat/conversation/export/health)
│   ├── agent/                  # ReAct Agent 引擎
│   │   ├── react_agent.py      # Agent 主循环 (思考 → 工具调用 → 生成)
│   │   └── tools/              # 工具定义 (RAG/天气/用户数据)
│   ├── rag/                    # RAG 检索增强生成
│   │   ├── vector_store.py     # ChromaDB 向量库管理
│   │   ├── rag_service.py      # RAG 总结链
│   │   └── evaluation.py       # 评测指标 + LLM 缓存
│   ├── core/                   # 核心基础设施 (config/exceptions/response/security)
│   ├── db/                     # 数据库层 (SQLAlchemy)
│   ├── models/                 # 数据模型 (ORM + Pydantic)
│   ├── services/               # 业务服务层
│   ├── model/                  # 模型工厂 (LLM + Embedding)
│   └── utils/                  # 工具模块 (日志/文件/路径)
│
├── config/                     # YAML 配置文件
├── data/                       # 知识库文件 (txt/pdf/csv)
├── prompts/                    # 提示词模板
├── scripts/                    # 运维脚本
├── .env.example                # 环境变量模板
└── requirements.txt            # Python 依赖
```

### 调用链说明

```
CLI: python cli.py "问题"
  → AgentGraph.stream(query)
    → recall_memory_node        # 语义检索历史记忆
    → classify_intent_node      # 关键词意图分类 (consultation/weather/report/user_info)
    → dispatch_skill_node       # 路由到对应 Skill → skill.run()
    → assemble_result_node      # 结果校验 → 失败则重试 (最多 3 次)
    → generate_output_node      # LLM 生成最终回答 (流式 token)
    → store_memory_node         # 对话摘要 → ChromaDB 长期记忆
  → 终端流式输出

API: POST /chat/stream
  → chat_service.stream_chat() → ReactAgent.execute_stream() → SSE 流式返回
```

## 面试亮点

### 1. 工程化 Agent 架构（5 层分离）

```
CLI → Graph (LangGraph) → Harness (驾驭层) → Skills (技能层) → Tools (原有工具)
```

- **Graph 层**：LangGraph StateGraph 编排，意图分类、技能调度、重试回路、记忆召回 — 全部由状态机驱动
- **Harness 层**：把 Prompt 管理、上下文拼接、异常处理、参数校验、结果校验、缓存、记忆 — 这些"脏活"从业务代码中抽离
- **Skills 层**：4 大技能统一 `BaseSkill` 接口 (`validate_input → execute → validate_output`)，可插拔、可单独单元测试
- **Tools 层**：复用原有 LangChain tool 函数，不做改动

### 2. LangGraph 状态编排

不是简单的 `if-else`。完整的 StateGraph：条件分支（general 跳过工具 / 其他调度技能）、重试回路（`assemble → dispatch` 失败重试最多 3 次）、记忆注入（`recall_memory` 节点语义检索历史对话）。状态通过 `TypedDict` 严格定义，每个节点返回部分 state，LangGraph 自动合并。

### 3. Long-term Memory 实现

对话自动摘要 → ChromaDB 独立集合存储 → 每次新问题语义召回 top-3 相关历史 → 注入 system prompt。让 Agent 在多轮对话中拥有"记忆"，而不依赖简单的消息历史堆叠。

### 4. 可插拔缓存架构

`CacheBackend` 抽象基类 → `MemoryCache` / `RedisCache` 两个实现。Redis 连接失败自动降级到内存缓存（不抛异常、不影响主流程）。接口与原有 `llm_cache.get/set` 完全兼容，切换成本零。

### 5. RAG 全流程 + 质量评测

覆盖完整的 RAG pipeline：文档加载 (PDF/CSV/TXT) → 切片策略 (RecursiveCharacterTextSplitter + 中文标点) → ChromaDB 向量化 → 语义检索 → LLM 总结。内置 Recall@K、Hit Rate、MRR 三项评测指标。

### 6. 生产级可观测性

- 请求日志中间件：每个请求分配 Request ID，记录方法/路径/耗时/状态码
- 日志脱敏：自动过滤 API Key、手机号、邮箱等敏感字段
- 限流中间件：基于 IP 的滑动窗口限流（可配置开关）

### 7. SSE 流式响应 + 对话导出

对话接口使用 Server-Sent Events 流式返回，前端逐字渲染。支持将完整对话导出为 Markdown 和 PDF（中文字体排版）。

## 注意事项

### 安全

- `.env` 文件已加入 `.gitignore`，不要将 API Key 提交到版本控制
- `.env.example` 作为模板文件，不含真实密钥
- 生产环境请关闭 `RATE_LIMIT_ENABLED` 的调试模式，按实际 QPS 设置限流阈值
- 建议为生产环境启用 JWT 鉴权（`JWT_SECRET_KEY` 已预留）
- 前端 CORS 白名单可通过 `.env` 配置，不要使用 `*`

### 部署

- 当前使用 SQLite，生产环境建议切换到 PostgreSQL（修改 `DATABASE_URL` 即可）
- ChromaDB 持久化目录需在容器部署时挂载 Volume（知识库 `chroma_db/` + 记忆库 `chroma_db_memory/`）
- Redis 缓存通过 CLI `--cache redis` 启用，生产环境建议配合 `--redis-host` 指向独立 Redis 实例
- 推荐使用 `gunicorn` + `uvicorn` workers 部署（`gunicorn -w 4 -k uvicorn.workers.UvicornWorker`）

### 扩展方向

- JWT 用户鉴权（`JWT_SECRET_KEY` 配置已就绪）
- Docker 容器化部署
- Intent 分类升级为 LLM 分类器（替换 `tool_router.py` 中的关键词匹配）
- 新增 Skill 只需: 创建 `skills/xxx_skill.py` → 继承 `BaseSkill` → 注册到 `SKILL_REGISTRY` → 添加路由映射
