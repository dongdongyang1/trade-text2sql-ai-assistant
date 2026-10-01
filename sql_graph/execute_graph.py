import asyncio

from sql_graph.draw_graph import draw_graph
from sql_graph.text2sql_graph import make_graph


async def execute_graph():
    """执行该 工作流"""
    # 拿到编译好的图
    graph = await make_graph()
    draw_graph(graph,"text2sql.png")
    while True:
        user_input = input("用户:")
        if user_input.lower() in ['q','quit','exit']:
            print("对话结束")
        else:
            #values 模式 = 每次吐当前完整的 State
            # 流式跑图：每个节点执行完吐一次完整状态
            async for event in graph.astream({"messages": [{"role": "user", "content": user_input}]},
                                             stream_mode="values"):
                event["messages"][-1].pretty_print()

if __name__ == "__main__":
    asyncio.run(execute_graph())