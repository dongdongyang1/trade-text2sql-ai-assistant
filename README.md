# 贸易业务 Text2SQL AI 助手

基于 **MCP（本地模拟远程）+ LangGraph + DeepSeek** 的自然语言查询 SQLite 数据库项目。
输入一句中文问题（如"总共有多少种产品？"），自动生成 SQL、执行查询并返回答案。

内置数据集：**Northwind 贸易数据库**（客户、产品、订单、供应商等经典贸易业务数据）。

---

## 功能特性

- 🗣️ **自然语言查库**：直接问"单价最贵的 3 种产品是什么？"即可，无需写 SQL
- 🧠 **MCP 服务**：通过 MCP（SSE 传输）在本地模拟远程工具调用，工具与图解耦
- 🔀 **LangGraph 状态图**：7 节点工作流（列表 → 表结构 → 生成 SQL → 检查 SQL → 执行 → 回答）
- ✅ **SQL 智能检查**：自动修正常见 SQL 错误（NOT IN NULL、UNION/UNION ALL、类型不匹配等）
- 🎯 **LIMIT 智能控制**：问"哪个/最"自动限制返回 1 条，问"前 N 个"按 N 返回，其余最多 5 条
- 🖥️ **Gradio 网页界面**：现代风格聊天 UI，支持文字问答（图片识别功能开发中）
- 🛡️ **密钥安全**：`.env` 已被 `.gitignore` 保护，绝不提交真实密钥

## 架构

```
用户问题
   │
   ▼
Gradio 网页 (gradio_view/chat_gradio.py)
   │
   ▼
LangGraph 图 (sql_graph/text2sql_graph.py)
   │   ├─ call_list_tables ──► ToolNode(list_tables_tool)
   │   ├─ call_get_schema ──► ToolNode(get_schema_tool)
   │   ├─ generate_query（生成 SQL + LIMIT 兜底）
   │   ├─ check_query（SQL 专家检查）
   │   └─ run_query ──► ToolNode(db_query_tool)
   │
   ▼
MCP Server (mcp_server/mcp_tools.py, SSE @ 127.0.0.1:8008)
   │   ├─ list_tables_tool   列出所有表
   │   ├─ get_schema_tool    查看表结构（BLOB 字段会提示勿 SELECT *）
   │   └─ db_query_tool      执行 SQL（BLOB 值替换为占位符）
   │
   ▼
SQLite (northwind.db)
```

## 目录结构

```
text2sql/
├── sql_graph/                 # LangGraph 图
│   ├── text2sql_graph.py      # 主图（7 节点 + fix_limit + make_graph）
│   ├── my_llm.py              # LLM 配置（DeepSeek）
│   ├── my_state.py            # 状态定义（消息合并）
│   ├── tool_node.py           # 系统提示词（生成 SQL / 检查 SQL）
│   └── execute_graph.py       # 命令行入口（输入循环 + 图可视化）
├── mcp_server/                # MCP 服务（本地模拟远程）
│   ├── mcp_tools.py           # FastMCP server，注册 3 个工具，SSE 8008
│   └── simple_sql_db.py       # SimpleSQLDatabase 封装（SQLAlchemy）
├── gradio_view/
│   └── chat_gradio.py         # Gradio 网页聊天界面
├── test_images/categories/    # 从库中提取的分类图片（测试素材）
├── northwind.db               # SQLite 数据库（贸易数据）
├── requirements.txt
├── .env.example               # 环境变量模板（复制为 .env 后填真实密钥）
└── .gitignore
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置密钥

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY（识别/问答），如需图片识别另配 ZHIPU_API_KEY 或 OPENAI_API_KEY
```

### 3. 启动 MCP Server（终端 1）

> ⚠️ 必须从项目根目录以模块方式启动，否则会报 `ModuleNotFoundError: sql_graph`

```bash
python -m mcp_server.mcp_tools
```

看到 `Uvicorn running on http://127.0.0.1:8008` 即成功，**保持此窗口运行**。

### 4. 启动网页（终端 2）

```bash
python gradio_view/chat_gradio.py
```

浏览器打开 http://127.0.0.1:7860（若被占用则自动使用 7861）。

### 5. 命令行模式（可选）

```bash
python sql_graph/execute_graph.py
```

## 示例问题

| 问题 | 期望 |
| --- | --- |
| 总共有多少种产品？ | 返回 77 |
| 单价最贵的 3 种产品是什么？ | 返回前 3 种及价格 |
| 2009 年销售额最高的产品是哪款？ | 唯一答案（LIMIT 1） |
| 每个分类下有多少产品？ | 按分类分组统计 |
| 有多少订单还没发货？ | ShippedDate 为空的订单数 |

## 注意事项

- **MCP server 必须先启动**，网页/命令行才能查询；
- **`.env` 含真实 API 密钥，已被 git 忽略，请勿手动提交**；
- server 必须用 `python -m mcp_server.mcp_tools` 启动（不能直接 `python mcp_server/mcp_tools.py`）；
- northwind.db 中 Products 表无图片字段，仅有 Categories.Picture（分类图）与 Employees.Photo（员工照片）。

## License

MIT
