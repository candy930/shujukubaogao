# -*- coding: utf-8 -*-
# 诊断 sp_login 的不同调用方式，定位 call_proc 返回空的原因
import db

md5 = 'e10adc3949ba59abbe56e057f20f883e'

# 方式1：直接 SELECT（基准，应该能查到）
sql = ("SELECT employee_id,name,role FROM employee "
       "WHERE login_name=? AND password=? AND status=N'在职'")
print("方式1 直接SELECT:", db.query(sql, ['admin', md5]))

# 方式2：ODBC 转义 {CALL}
conn = db.get_conn()
cur = conn.cursor()
cur.execute("{CALL sp_login (?,?)}", ['admin', md5])
print("方式2 CALL 描述:", [c[0] for c in cur.description] if cur.description else None)
print("方式2 CALL 结果:", cur.fetchall())
conn.close()

# 方式3：原生 EXEC
conn = db.get_conn()
cur = conn.cursor()
cur.execute("EXEC sp_login ?, ?", ['admin', md5])
print("方式3 EXEC 结果:", cur.fetchall())
conn.close()
