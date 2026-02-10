
import pymysql
import re
from datetime import timedelta,datetime
import sqlglot
from sqlglot import exp
from sqlglot.expressions import Create, Drop, Alter
from functools import lru_cache

def replace_alter_table(sql: str, old_table: str, new_table: str) -> str:
    """使用 sqlglot 安全替换 ALTER TABLE 中的表名"""
    try:
        parsed_statements = sqlglot.parse(sql)
        new_sql = []

        for stmt in parsed_statements:
            for node in stmt.walk():
                if isinstance(node, exp.Table) and node.name == old_table:
                    node.set("this", exp.to_identifier(new_table))
            new_sql.append(stmt.sql())

        return " ".join(new_sql)

    except Exception as e:
        print(f"替换失败: {e}")
        return sql  # fallback 原 SQL


def online_schema_change(
    host, user, password, database, table, by_type, alter_sql, condition
):
    """
    在线表结构变更的简化实现。
    :param host: MySQL 主机地址
    :param user: MySQL 用户名
    :param password: MySQL 密码
    :param database: 数据库名称
    :param table: 目标表名称
    :param by_type: 根据时间或者ID
    :param alter_sql: DDL 更改的 SQL 
    :param condition: 删除目标数据的条件
    """

    # 定义每隔多少行打印一次信息
    inserted_rows = 0
    print_interval = 100000
    counter = 0

    try:
        connection = pymysql.connect(host=host, user=user, password=password, database=database, cursorclass=pymysql.cursors.DictCursor)
        cursor = connection.cursor()

        # 1.确认条件字段
        TIME_COLUMN = ""
        PK_COLUMN = ""
        cursor.execute(f'SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA="{database}" AND TABLE_NAME="{table}";')
        columns_message = cursor.fetchall()
        for i in columns_message:
            print(i["DATA_TYPE"])
            if i["DATA_TYPE"].lower() in ["datetime", "timestamp"] and i["COLUMN_KEY"].lower() in ["mul"]:
                TIME_COLUMN = i["COLUMN_NAME"]
            if i["COLUMN_KEY"].lower() in ["pri"] and "int" in i["DATA_TYPE"].lower(): 
                PK_COLUMN = i["COLUMN_NAME"]
        if by_type == "TIME":
            if not TIME_COLUMN:
                print("表中没有具备索引的时间字段!")
                return False
        else:
            if not PK_COLUMN:
                print("表中没有主键")
                return False

        # 2.创建临时表并执行DDL语句
        target_tb = f"_{table}_temporary_"
        cursor.execute(f"create table {target_tb} like {table};")
        if alter_sql:
            final_sql = replace_alter_table(alter_sql, table, target_tb)
            cursor.execute(final_sql)
                
        # 3.创建触发器
        columns_list=[ i["COLUMN_NAME"] for i in columns_message ]
        ins_trigger_sql = f"CREATE TRIGGER `archive_{table}_ins` AFTER INSERT ON `{database}`.`{table}`  \
                                FOR EACH ROW REPLACE INTO `{database}`.`{target_tb}` ({'`'+'`, `'.join(columns_list)+'`'}) VALUES ({'NEW.`'+'`, NEW.`'.join(columns_list)+'`'});"
        del_trigger_sql = f"CREATE TRIGGER `archive_{table}_del` AFTER DELETE ON `{database}`.`{table}`  \
                                FOR EACH ROW DELETE IGNORE FROM `{database}`.`{target_tb}` WHERE `{database}`.`{target_tb}`.`{PK_COLUMN}` <=> OLD.`{PK_COLUMN}`;"
        upd_trigger_sql = f"CREATE TRIGGER `archive_{table}_upd` AFTER UPDATE ON `{database}`.`{table}`  \
                                FOR EACH ROW BEGIN DELETE IGNORE FROM `{database}`.`{target_tb}` WHERE !(OLD.`id` <=> NEW.`id`) AND `{database}`.`{target_tb}`.`{PK_COLUMN}` <=> OLD.`{PK_COLUMN}`; REPLACE INTO `{database}`.`{target_tb}` ({'`'+'`, `'.join(columns_list)+'`'}) VALUES ({'NEW.`'+'`, NEW.`'.join(columns_list)+'`'}); END"
        cursor.execute(ins_trigger_sql)
        cursor.execute(del_trigger_sql)
        cursor.execute(upd_trigger_sql)

        # 4.执行反向插入数据
        if by_type == "TIME":
            if TIME_COLUMN: 
                cursor.execute(f"SELECT MAX({TIME_COLUMN}) AS MAX_TIME, MIN({TIME_COLUMN}) AS MIN_TIME FROM {table} WHERE NOT ({condition});")
                res = cursor.fetchall()
                if res:
                    MIN_TIME = res[0]["MIN_TIME"]
                    MAX_TIME = res[0]["MAX_TIME"]
                    step_time = MIN_TIME
                    while step_time < MAX_TIME:
                        step_end_time = step_time + timedelta(minutes=180)
                        if step_end_time >= MAX_TIME:
                            connection.begin()
                            cursor.execute(f"/* PddSQL 1.0 EXEC */ INSERT IGNORE INTO {target_tb} SELECT * FROM {table} WHERE NOT ({condition}) AND {TIME_COLUMN} >= '{step_time}' AND {TIME_COLUMN} <= '{MAX_TIME}' LOCK IN SHARE MODE;")
                            counter += cursor.rowcount
                            inserted_rows += cursor.rowcount
                            connection.commit()
                            print(f"Insert rows: {inserted_rows}, now {TIME_COLUMN} in [{step_time} , {MAX_TIME}]")
                            break
                        else:
                            cursor.execute(f"/* PddSQL 1.0 EXEC */ INSERT IGNORE INTO {target_tb} SELECT * FROM {table} WHERE NOT ({condition}) AND {TIME_COLUMN} >= '{step_time}' AND {TIME_COLUMN} < '{step_end_time}' LOCK IN SHARE MODE;")
                            counter += cursor.rowcount
                            inserted_rows += cursor.rowcount
                            connection.commit()
                        step_time = step_end_time
                        if counter > print_interval:
                            print(f"Insert rows: {inserted_rows}, now {TIME_COLUMN} in [{step_time} , {step_end_time})", flush=True)
                            counter = 0
        
        if by_type == "PRI":
            pass
        # 4.交换表名
        now_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        rename_sql = f"RENAME TABLE {table} TO _{table}_fordbaremove_old_{now_timestamp}, {target_tb} TO {table};"
        cursor.execute(rename_sql)

        # 5.删除触发器
        cursor.execute(f"drop trigger if exists {database}.archive_{table}_ins")
        cursor.execute(f"drop trigger if exists {database}.archive_{table}_del")
        cursor.execute(f"drop trigger if exists {database}.archive_{table}_upd")
        print("触发器已清除")

    except Exception as e:
        print(e)
        if "connection" in locals():
            connection.close()

def extract_table_name_ddl(sql):
    """
    使用 sqlglot 解析 DDL 语句，提取第一个表名
    支持 CREATE / DROP / ALTER 等 DDL
    """
    try:
        parsed = sqlglot.parse_one(sql)
        if isinstance(parsed, (Create, Drop, Alter)):
            return parsed.this.name  # `this` 是 Table 节点
    except Exception as e:
        print(f"解析失败: {e}")
    return None

# 预编译正则，提升效率
RE_LINE_COMMENT = re.compile(r"--.*?(\n|$)")
RE_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
RE_MULTISPACE = re.compile(r"\s+")
RE_STRINGS = re.compile(r"'(?:\\'|[^'])*?'")
RE_NUMBERS = re.compile(r"\b\d+(\.\d+)?\b")
RE_IN_LIST = re.compile(r"\bIN\s*\((\s*\?[\s,]*)+\)", re.IGNORECASE)
RE_BETWEEN = re.compile(r"\bBETWEEN\s+\?\s+AND\s+\?", re.IGNORECASE)
RE_COMMAND = re.compile(
    r"^\s*(SHOW|SET|USE|DESC|DESCRIBE|EXPLAIN|HELP)\b",
    re.IGNORECASE
)

@lru_cache(maxsize=5000)
def normalize_sql(sql: str) -> str:
    if not sql:
        return ""

    # 轻量规范化（提高缓存命中率）
    sql = RE_LINE_COMMENT.sub(" ", sql)
    sql = RE_BLOCK_COMMENT.sub(" ", sql)
    sql = sql.strip()
    sql = RE_MULTISPACE.sub(" ", sql)

    # 命令类 SQL 不进 AST
    if RE_COMMAND.match(sql):
        return sql.upper()

    try:
        parsed = sqlglot.parse_one(sql, read="mysql")

        # AST 级参数抽象（安全）
        for lit in parsed.find_all(exp.Literal):
            lit.replace(exp.Placeholder())

        return parsed.sql(dialect="mysql", pretty=False)

    except Exception:
        return sql