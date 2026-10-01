from typing import List, Dict
import os
import sys

# 保证从任意目录运行都能找到项目根下的 sql_graph 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr
from PIL import Image, ImageDraw, ImageFont

from sql_graph.text2sql_graph import make_graph


# ============================================================
# 图只建一次（缓存复用）
# ============================================================
_graph = None


async def get_graph():
    global _graph
    if _graph is None:
        _graph = await make_graph()
    return _graph


# ============================================================
# 跑一次图，拿最终答案
# ============================================================
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


async def execute_graph_gradio(chat_bot: List[Dict]) -> List[Dict]:
    if not chat_bot:  # 空聊天记录（例如空输入就提交）→ 直接返回，不触发图
        return chat_bot
    user_input = chat_bot[-1].get("content", "")
    if isinstance(user_input, list):  # gradio 新版 content 可能是 list 格式，转回纯文本
        user_input = " ".join(p.get("text", "") for p in user_input if isinstance(p, dict))
    try:
        result = await run_graph_once(user_input)
        if not result:
            result = "我暂时没拿到有效结果，换个说法再试试？"
    except Exception as e:
        print(f"[Gradio] 执行出错: {e}")  # 详细错误进终端，供排查
        result = "服务暂时出了点问题，请稍后再试。"
    chat_bot.append({"role": "assistant", "content": result})
    return chat_bot


def do_graph(user_input, chat_bot):
    """输入框提交后，执行的函数"""
    if user_input:
        chat_bot.append({"role": "user", "content": user_input})
    return "", chat_bot


# ============================================================
# 生成对话头像（本地 PNG，不依赖外网）
# ============================================================
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(_ASSETS, exist_ok=True)
_user_avatar = os.path.join(_ASSETS, "user.png")
_bot_avatar = os.path.join(_ASSETS, "bot.png")


def _make_avatar(text: str, bg: tuple, fg: str, path: str, size: int = 120):
    if os.path.exists(path):
        return
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, size - 4, size - 4], fill=bg)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", int(size * 0.42))
    except Exception:
        font = ImageFont.load_default()
    bbox = d.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]), text, fill=fg, font=font)
    img.save(path)


_make_avatar("我", (96, 165, 250), "white", _user_avatar)   # 蓝色用户头像
_make_avatar("AI", (139, 92, 246), "white", _bot_avatar)   # 紫色 AI 头像


# ============================================================
# 主题与样式
# ============================================================
theme = gr.themes.Soft(
    primary_hue=gr.themes.colors.indigo,
    secondary_hue=gr.themes.colors.violet,
    neutral_hue=gr.themes.colors.slate,
)

CSS = """
.gradio-container {
    background: linear-gradient(160deg, #EEF2FF 0%, #F5F3FF 45%, #FDF4FF 100%) !important;
    max-width: 920px !important;
    margin: 24px auto !important;
    border-radius: 22px !important;
    border: 1px solid rgba(99, 102, 241, 0.12) !important;
    box-shadow: 0 12px 48px rgba(99, 102, 241, 0.14) !important;
    padding: 26px 34px !important;
}

#header {
    background: linear-gradient(135deg, #F5F3FF 0%, #EEF2FF 100%);
    border: 1px solid rgba(99, 102, 241, 0.16);
    border-radius: 18px;
    padding: 16px 22px;
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.08);
    margin-bottom: 18px;
}
.hwrap { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.hlogo {
    width: 46px; height: 46px; border-radius: 12px; flex-shrink: 0;
    background: linear-gradient(135deg, #6366F1, #8B5CF6);
    display: flex; align-items: center; justify-content: center;
    font-size: 22px; box-shadow: 0 4px 10px rgba(99, 102, 241, 0.30);
}
.htitle { font-size: 19px; font-weight: 700; color: #1F2937; letter-spacing: 0.5px; }
.hsub { font-size: 12.5px; color: #6B7280; margin-top: 3px; }
.hbadge {
    margin-left: auto; display: inline-flex; align-items: center; gap: 6px;
    background: rgba(74, 222, 128, 0.14); color: #16A34A;
    border: 1px solid rgba(74, 222, 128, 0.35); border-radius: 999px;
    padding: 4px 12px; font-size: 12px; font-weight: 600;
}
.dot { width: 8px; height: 8px; border-radius: 50%; background: #22C55E; display: inline-block; }

#chatbot {
    border-radius: 16px !important;
    border: 1px solid rgba(99, 102, 241, 0.14) !important;
    box-shadow: 0 4px 18px rgba(99, 102, 241, 0.08) !important;
    background: white !important;
    margin-bottom: 14px;
}

#inputbox textarea {
    border-radius: 14px !important;
    font-size: 15px !important;
    padding: 12px 16px !important;
}
#send-btn {
    background: linear-gradient(135deg, #6366F1, #8B5CF6) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 600;
    height: 48px;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
}
#send-btn:hover { filter: brightness(1.08); }
"""

# ============================================================
# 页面
# ============================================================
with gr.Blocks(title="Text2SQL AI 助手") as instance:
    with gr.Column(elem_id="page"):
        # 顶部头部卡片
        with gr.Column(elem_id="header"):
            gr.HTML(
                """
<div class="hwrap">
  <div class="hlogo">📊</div>
  <div class="htexts">
    <div class="htitle">Text2SQL AI 助手</div>
    <div class="hsub">查询贸易业务数据 —— 客户 · 产品 · 订单 · 供应商</div>
  </div>
  <div class="hbadge"><span class="dot"></span>服务在线</div>
</div>
""",
                elem_id="header_html",
            )

        # 聊天区
        chatbot = gr.Chatbot(
            elem_id="chatbot",
            height=480,
            avatar_images=(_user_avatar, _bot_avatar),
            render_markdown=True,
        )

        # 输入区
        with gr.Row():
            input_textbox = gr.Textbox(
                elem_id="inputbox",
                placeholder="试试问：总共有多少种产品？",
                scale=6,
                container=False,
            )
            send_btn = gr.Button("发送", elem_id="send-btn", scale=1)

    # 事件绑定：回车 / 点发送，两条路都走同一套逻辑
    input_textbox.submit(
        do_graph, [input_textbox, chatbot], [input_textbox, chatbot]
    ).then(execute_graph_gradio, chatbot, chatbot)
    send_btn.click(
        do_graph, [input_textbox, chatbot], [input_textbox, chatbot]
    ).then(execute_graph_gradio, chatbot, chatbot)

if __name__ == "__main__":
    instance.launch(debug=True, theme=theme, css=CSS)
