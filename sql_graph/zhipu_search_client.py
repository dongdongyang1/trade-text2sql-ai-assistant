# ========== 智谱搜索客户端：用openai包 ==========
from openai import OpenAI
from sql_graph.env_utils import ZHIPU_API_KEY

#OpenAI 兼容客户端，没有 .web_search 属性
zhipu_search_client = OpenAI(
    api_key=ZHIPU_API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)