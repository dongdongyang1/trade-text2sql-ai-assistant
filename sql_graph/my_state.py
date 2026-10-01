from typing import TypedDict, Annotated, List

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


class SQLState(TypedDict):
    #Annotated[类型, 合并函数] = "这个字段别覆盖，按这个函数合并"
    messages:Annotated[List[AnyMessage],add_messages]