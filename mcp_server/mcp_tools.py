import os

from mcp.server import FastMCP
from sql_graph.zhipu_search_client import zhipu_search_client
from mcp_server.simple_sql_db import SimpleSQLDatabase

mcp_server = FastMCP(name="yx-mcp",instructions="我自己的MCP服务",port=8008)
_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "northwind.db")
db = SimpleSQLDatabase.from_uri(f"sqlite:///{_DB_PATH}")

@mcp_server.tool("my_search_tool",description="专门搜索互联网中的内容")
def my_search(query:str)->str:
    """搜索互联网上的内容"""
    try:
        response = zhipu_search_client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role":"user","content":query}],
            tools=[
                {
                    "type":"web_search",
                    "web_search":{"search_query":query}
                }
            ]
        )
        content = response.choices[0].message.content
        return content
    except Exception as e:
        print(e)
        return '没有搜索到任何内容！'

#接口
@mcp_server.tool("list_tables_tool",description="输入是一个空字符串，返回数据库中的所有:以逗号分隔的表名字列表")
def list_tables_tool()->str:
    """输入是一个空字符串, 返回数据库中的所有：以逗号分隔的表名字列表"""
    return ",".join(db.get_usable_table_names()) #   ['emp': “这是一个员工表，”, '']

@mcp_server.tool("get_schema_tool",description="查询指定表的字段结构（列名+类型）。输入逗号分隔的表名，例如 'Categories,Orders'")
def get_schema_tool(table_names:str)->str:
    """获取表结构信息，table_names 为逗号分隔的表名。"""
    tables = [t.strip() for t in table_names.split(",") if t.strip()]
    return db.get_table_info(tables)

@mcp_server.tool()
def db_query_tool(query:str) -> str:
    """
    执行SQL查询并返回结果。
    如果查询不正确，将返回错误信息。
    如果返回错误，请重写查询语句，检查后重试。

    Args:
        query (str): 要执行的SQL查询语句

    Returns:
        str: 查询结果或错误信息
    """
    result = db.run(query)
    if isinstance(result,str):
        return result
    return str(result) if result else "查询成功，但结果为空。"

if __name__ == "__main__":
    mcp_server.run(transport="sse")

