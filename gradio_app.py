from typing import List, Dict

import gradio as gr

from sql_graph.text2sql_graph import make_graph


# ---- 图只建一次（缓存复用）----
_graph = None


async def get_graph():
    global _graph
    if _graph is None:
        _graph = await make_graph()
    return _graph


# ---- 跑一次图，拿最终答案（命令行版可共用）----
async def run_graph_once(user_input: str) -> str:
    graph = await get_graph()
    result = ""
    async for event in graph.astream(
        {"messages": [{"role": "user", "content": user_input}]},
        stream_mode="values",
    ):
        messages = event.get("messages") or []
        if not messages:
            continue
        last = messages[-1]  # 取最后一条消息
        if last.__class__.__name__ == "AIMessage" and last.content:
            result = last.content
    return result


# ---- 网页版执行器 ----
async def execute_graph_gradio(chat_bot: List[Dict]) -> List[Dict]:
    user_input = chat_bot[-1]["content"]
    try:
        result = await run_graph_once(user_input)
        if not result:
            result = "我暂时没拿到有效结果，换个说法再试试？"
    except Exception as e:
        print(f"[Gradio] 执行出错: {e}")  # 详细错误进终端，供排查
        result = "服务暂时出了点问题，请稍后再试。"
    chat_bot.append({"role": "assistant", "content": result})
    return chat_bot


# ---- 提交处理 ----
def do_graph(user_input, chat_bot):
    if user_input:
        chat_bot.append({"role": "user", "content": user_input})
    return "", chat_bot


with gr.Blocks(title='MCP服务的TEXT2SQL项目') as instance:
    gr.Label('调用MCP服务的TEXT2SQL项目', container=False)
    chatbot = gr.Chatbot(type='messages', height=450, label='AI客服')  # 聊天记录组件
    input_textbox = gr.Textbox(label='请输入你的问题📝', value='')  # 输入框组件
    input_textbox.submit(
        do_graph, [input_textbox, chatbot], [input_textbox, chatbot]
    ).then(execute_graph_gradio, chatbot, chatbot)

if __name__ == '__main__':
    instance.launch(debug=True)
