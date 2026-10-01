#启动服务端
# from langchain_community.utilities import SQLDatabase
#SQLDatabase本质就是SQLAlchemy 包装类，官方现在推荐：直接基于 SQLAlchemy 自己封装数据库查询逻辑
# if __name__ == "__main__":
#     db = SQLDatabase.from_uri("sqlite:///../northwind.db")
#     print(db.get_usable_table_names())
#     res = db.run('select CategoryID, CategoryName, Description from Categories limit 10;')
#     print(res)
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
# create_engine：创建数据库连接引擎
# text：把普通 SQL 字符串包装成 sqlalchemy 可执行对象
# inspect：数据库探查器，专门读表名、字段结构
# SQLAlchemyError：捕获 SQL 执行报错


class SimpleSQLDatabase:
    def __init__(self,engine):
        self.engine = engine #数据库连接引擎
        self.inspector = inspect(engine) #探查器，后面用来读表、字段信息

    #类的普通方法
    @classmethod
    def from_uri(cls,uri:str):
        """输入数据库连接字符串（uri），自动创建引擎，返回 SimpleSQLDatabase 实例"""
        engine = create_engine(uri)
        return cls(engine)

    def get_usable_table_names(self):
        """等价原 langchain SQLDatabase.get_usable_table_names()"""
        return self.inspector.get_table_names()

    def get_table_info(self, table_names: list[str] = None):
        """获取表结构信息，用于LLM构造SQL，跳过BLOB字段详情"""
        tables = table_names or self.get_usable_table_names()
        schema_info = [] #存放每张表的描述文本，最后一次性拼接返回给 LLM
        for tbl in tables:
            cols = self.inspector.get_columns(tbl) #探查器 inspector 读取这张表所有字段信息
            col_desc = [] #当前这一张表的所有字段描述
            for c in cols:
                col_type = str(c["type"])
                # 标记BLOB类型
                if "BLOB" in col_type.upper(): #upper()把类型字符串全部转大写
                    col_desc.append(f"{c['name']} ({col_type}) [Binary blob, do NOT select *]")
                else:
                    col_desc.append(f"{c['name']} ({col_type})")
            schema_info.append(f"Table {tbl}: {', '.join(col_desc)}")
        return "\n".join(schema_info) #用换行符\n拼接成一整个大字符串返回

    def run(self, query: str):
        """执行SQL，自动将bytes(BLOB)替换为简短描述，避免大量二进制污染上下文"""
        try:
            with self.engine.connect() as conn: #打开数据库连接，连接对象叫 conn
                result = conn.execute(text(query)) #text(query)把普通字符串 SQL 包装成 SQLAlchemy 识别的对象
                rows = result.fetchall() #fetchall()取出 SQL 查询返回的全部行数据
                output = []
                for row in rows:
                    row_data = []
                    for val in row:
                        if isinstance(val, bytes):
                            row_data.append(f"[BLOB IMAGE, length={len(val)} bytes]")
                        else:
                            row_data.append(val)
                    output.append(tuple(row_data))
                return output
        except SQLAlchemyError as e:
            return f"Error executing query: {str(e)}"

if __name__ == "__main__":
    db = SimpleSQLDatabase.from_uri("sqlite:///../northwind.db")
    print(db.get_usable_table_names())
    # 可选：查看表结构
    # print(db.get_table_info(["Categories"]))
    res = db.run('select * from Categories limit 10;')
    print(res)
