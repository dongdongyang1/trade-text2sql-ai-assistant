import re
import uuid
from typing import Literal

from langchain_core.messages import AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from sql_graph.my_llm import llm
from sql_graph.my_state import SQLState
from sql_graph.tool_node import generate_query_system_prompt, query_check_system

# 连上你自己写的 MCP server，把它暴露的几个工具 "下载" 成本地能直接调用的函数对象
mcp_server_config = {
    "url":"http://localhost:8008/sse",
    "transport":"sse"
}


def fix_limit(sql: str, question: str) -> str:
    """根据用户问题意图，强制修正生成的 SQL 的 LIMIT 行数。
    提示词对 LLM 只是建议，遵守率不是 100%，这里做代码层兜底。
    """
    # C 类：分类汇总（每个/各/分布/分别）——保留模型自己的 LIMIT，绝不强制 LIMIT 1
    if re.search(r'每个|各|按.{0,4}统计|分别|分布', question):
        return sql
    # A 类：求唯一答案 —— 强制 LIMIT 1
    if re.search(r'哪个|哪一个|谁|哪一位|一共|总共|有多少|有没有|是否|是不是|最.{0,4}的是|最高|最多|最贵|最大|最便宜|最少', question):
        # 已有 LIMIT N（N>1）→ 替换成 LIMIT 1（兼容末尾分号）
        sql = re.sub(r'\s+LIMIT\s+\d+\s*;?\s*$', ' LIMIT 1', sql, flags=re.IGNORECASE)
        # 没有 LIMIT → 补一个 LIMIT 1（放在分号前）
        if 'LIMIT' not in sql.upper():
            sql = sql.rstrip().rstrip(';') + ' LIMIT 1'
    return sql


def should_continue(state:SQLState)->Literal[END,"check_query"]:
    """条件路由的动态边"""
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return END
    else:
        return "check_query"

async def make_graph():
    """定义，并且编译工作流"""
    # 新版 langchain-mcp-adapters（0.1.0+）不再支持 async with，直接创建 client
    client = MultiServerMCPClient({"yx_mcp":mcp_server_config})
    tools = await client.get_tools() #发一次网络请求,server 返回工具列表(工具对象本身)
    # 所有表名列表的工具
    list_tables_tool = next(tool for tool in tools if tool.name=="list_tables_tool")
    #获得表字段的工具
    get_schema_tool = next(tool for tool in tools if tool.name=="get_schema_tool")
    # 执行sql的工具
    db_query_tool = next(tool for tool in tools if tool.name=="db_query_tool")

    def call_list_tables(state:SQLState):
        """第一个节点 """
        tool_call = {
            "name":"list_tables_tool",
            "args":{},
            "id":str(uuid.uuid4()),
            "type":"tool_call"
        }
        tool_call_message = AIMessage(content="",tool_calls=[tool_call])
        return {"messages":[tool_call_message]}

    # 第二个节点：ToolNode 自动执行"列表名"
    list_tables_node = ToolNode([list_tables_tool],name="list_tables")

    def call_get_schema(state:SQLState):
        """第三个节点: 让 LLM 决定查哪几张表的字段"""
        llm_with_tools = llm.bind_tools([get_schema_tool], tool_choice="any")
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    # 第四个节点：ToolNode 自动执行"查表结构"
    get_schema_node = ToolNode([get_schema_tool], name="get_schema")

    def generate_query(state:SQLState):
        """第五个节点: 生成SQL语句"""
        system_message = {
            "role" : "system",
            "content" : generate_query_system_prompt
        }

        # 这里不强制工具调用，允许模型在获得解决方案时自然响应
        llm_with_tools = llm.bind_tools([db_query_tool])
        response = llm_with_tools.invoke([system_message]+state["messages"])

        # 代码层兜底：按用户问题意图修正 LIMIT（提示词遵守率不是 100%）
        if response.tool_calls:
            # 取出用户原始问题
            question = ""
            for m in state["messages"]:
                if m.type == "human":
                    question = m.content
                    if isinstance(question, list):  # 多模态 content 格式，转成纯文本
                        question = " ".join(
                            p.get("text", "") if isinstance(p, dict) else str(p)
                            for p in question
                        )
                    break
            args = response.tool_calls[0]["args"]
            if "query" in args and question:
                args["query"] = fix_limit(args["query"], question)

        return {"messages":[response]}

    def check_query(state:SQLState):
        """第六个节点: 检查SQL语句"""
        system_message = {
            "role" : "system",
            "content" : query_check_system
        }
        tool_call = state["messages"][-1].tool_calls[0]
        # 得到生成后的SQL
        user_message = {"role":"user","content":tool_call["args"]["query"]}
        llm_with_tool = llm.bind_tools([db_query_tool],tool_choice="any")
        resp = llm_with_tool.invoke([system_message,user_message])
        resp.id = state["messages"][-1].id
        return {"messages":[resp]}

    # 第七个节点：ToolNode 自动执行SQL
    run_query_node = ToolNode([db_query_tool],name="run_query")

    workflow = StateGraph(SQLState)
    workflow.add_node(call_list_tables)
    workflow.add_node(list_tables_node)
    workflow.add_node(call_get_schema)
    workflow.add_node(get_schema_node)
    workflow.add_node(generate_query)
    workflow.add_node(check_query)
    workflow.add_node(run_query_node)

    workflow.add_edge(START, "call_list_tables")
    workflow.add_edge("call_list_tables", "list_tables")
    workflow.add_edge("list_tables", "call_get_schema")
    workflow.add_edge("call_get_schema", "get_schema")
    workflow.add_edge("get_schema", "generate_query")
    workflow.add_conditional_edges('generate_query',should_continue)
    workflow.add_edge("check_query","run_query")
    workflow.add_edge("run_query","generate_query")

    graph = workflow.compile()
    return graph

