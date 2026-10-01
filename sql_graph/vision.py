import base64
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_VISION_MODEL = "deepseek-flash"

def _get_client()->OpenAI:
    return OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )

def recognize_product(image_path:str)->str:
    """识别图片中的产品，返回一句话描述（供后续查库）"""
    with open(image_path,"rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    #Data URI（数据内嵌格式）
    data_uri = f"data:image/jpeg;base64,{img_b64}"

    resp = _get_client().chat.completions.create(
        model=_VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_uri}},
                {"type": "text",
                 "text": "请识别图中产品，按以下格式输出（不要输出其他内容）：\n分类：<该产品所属类别，如饮料、海鲜、糖果、乳制品等，无法确定写未知>\n产品：<具体产品名称，无法确定写未知>\n特征：<一句话描述>"},
            ],
        }],
        max_tokens=1024
    )

    return resp.choices[0].message.content.strip()



