# -*- coding: utf-8 -*-
"""
db.py —— 数据库连接 + 参数化查询封装（防 SQL 注入）

依赖：pip install pyodbc
说明：SQL Server 需先启用对应 ODBC 驱动（ODBC Driver 17/18 for SQL Server）
      Windows 本地 SQL Server 默认可用 Windows 身份验证（Trusted_Connection=yes），无需密码
"""
import pyodbc

# 服务器名：本机实例为 SQLEXPRESS，故填 .\\SQLEXPRESS（等价于 localhost\\SQLEXPRESS）
SERVER = ".\\SQLEXPRESS"
DATABASE = "ClothingSalesDB"


def _get_driver():
    """自动选择可用的 SQL Server ODBC 驱动"""
    drivers = pyodbc.drivers()
    for pref in ["ODBC Driver 18 for SQL Server",
                 "ODBC Driver 17 for SQL Server",
                 "SQL Server"]:
        if pref in drivers:
            return pref
    raise RuntimeError(
        "未找到 SQL Server ODBC 驱动。请安装 'ODBC Driver 17/18 for SQL Server'。\n"
        "本机可用驱动：%s" % drivers
    )


def _conn_str():
    return (
        "DRIVER={%s};" % _get_driver()
        + "SERVER=%s;" % SERVER
        + "DATABASE=%s;" % DATABASE
        + "Trusted_Connection=yes;"   # Windows 身份验证（零基础最省事）
        + "TrustServerCertificate=yes;"  # 信任服务器证书，避免 ODBC 驱动 18 证书校验报错
        + "Encrypt=no;"  # 本机连接，关闭强制加密，进一步避免证书问题
    )


def get_conn():
    """获取数据库连接"""
    return pyodbc.connect(_conn_str())


def query(sql, params=None):
    """
    参数化查询（SELECT），返回字典列表。
    例：query('SELECT * FROM member WHERE member_id = ?', [1])
    ? 是占位符，参数通过列表传入 —— 杜绝 SQL 注入。
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def execute(sql, params=None):
    """
    参数化执行（INSERT/UPDATE/DELETE），返回受影响行数。
    例：execute('UPDATE member SET points = ? WHERE member_id = ?', [100, 1])
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        conn.commit()
        return cur.rowcount


def call_proc(proc_name, params=None):
    """调用存储过程（如采购入库/销售出库），返回结果"""
    with get_conn() as conn:
        cur = conn.cursor()
        if params:
            cur.execute("{CALL %s (%s)}" % (proc_name, ",".join("?" * len(params))), params)
        else:
            cur.execute("{CALL %s}" % proc_name)
        # 必须先取完结果集再 commit：commit 会关闭游标，之后 fetch 会报函数序列错误
        try:
            cols = [c[0] for c in cur.description]
            result = [dict(zip(cols, row)) for row in cur.fetchall()]
        except Exception:
            result = []
        conn.commit()
        return result
