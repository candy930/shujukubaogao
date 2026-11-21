# -*- coding: utf-8 -*-
"""
main.py —— 服装销售管理系统 主程序（登录 + 主菜单 + 会员管理完整示例）

教学说明：
1. 本文件是「可运行的最小系统」：登录 + 会员管理增删改查。
2. 所有 SQL 均通过 db.py 的参数化查询执行（? 占位符），杜绝 SQL 注入。
3. 其余模块（商品/采购/销售/库存/报表）照「会员管理」模板复制改写即可，
   后续我会逐个给出。
运行方式：python main.py
"""
import tkinter as tk
from tkinter import ttk, messagebox
import hashlib
import db
import base_data
import stock_report
import purchase
import sale


# ============================================================
# 一、登录窗口
# ============================================================
class LoginWindow:
    def __init__(self):
        self.win = tk.Tk()
        self.win.title("服装销售管理系统 - 登录")
        self.win.geometry("360x220")
        self.win.resizable(False, False)

        tk.Label(self.win, text="服装销售管理系统", font=("微软雅黑", 16, "bold")).pack(pady=18)
        tk.Label(self.win, text="登录名").pack()
        self.entry_name = tk.Entry(self.win, width=26)
        self.entry_name.pack(pady=4)
        tk.Label(self.win, text="密码").pack()
        self.entry_pwd = tk.Entry(self.win, width=26, show="*")
        self.entry_pwd.pack(pady=4)

        tk.Button(self.win, text="登 录", width=20, command=self.do_login).pack(pady=14)

    def do_login(self):
        name = self.entry_name.get().strip()
        pwd = self.entry_pwd.get().strip()
        if not name or not pwd:
            messagebox.showwarning("提示", "请输入登录名和密码")
            return
        try:
            # 密码 MD5 后传给 sp_login（数据库存哈希，非明文），参数化防注入
            pwd_hash = hashlib.md5(pwd.encode("utf-8")).hexdigest()
            rows = db.call_proc("sp_login", [name, pwd_hash])
            if rows:
                self.win.destroy()
                MainWindow(rows[0])  # 传入 {employee_id, name, role}
            else:
                messagebox.showerror("失败", "登录名或密码错误，或账号已停用")
        except Exception as e:
            messagebox.showerror("数据库错误", str(e))

    def run(self):
        self.win.mainloop()


# ============================================================
# 二、主窗口（菜单导航）
# ============================================================
class MainWindow:
    def __init__(self, user):
        self.user = user
        self.employee_id = user.get("employee_id", 1)  # 当前登录员工号，用于写流水/盘点
        self.win = tk.Tk()
        self.win.title("服装销售管理系统")
        self.win.geometry("760x520")

        # 记录已打开的功能窗口，防止同一个窗口重复打开、任务栏堆积
        self.open_windows = {}

        # 菜单栏
        menubar = tk.Menu(self.win)
        m_base = tk.Menu(menubar, tearoff=0)
        m_base.add_command(label="会员管理", command=lambda: self.open_window(
            "member", lambda: MemberWindow(self.win)))
        m_base.add_command(label="商品管理", command=lambda: self.open_window(
            "product", lambda: base_data.ProductWindow(self.win)))
        m_base.add_command(label="供应商管理", command=lambda: self.open_window(
            "supplier", lambda: base_data.SupplierWindow(self.win)))
        menubar.add_cascade(label="基础数据", menu=m_base)

        m_biz = tk.Menu(menubar, tearoff=0)
        m_biz.add_command(label="采购管理", command=lambda: self.open_window(
            "purchase", lambda: purchase.PurchaseWindow(self.win, self.employee_id)))
        m_biz.add_command(label="销售管理", command=lambda: self.open_window(
            "sale", lambda: sale.SaleWindow(self.win, self.employee_id)))
        m_biz.add_command(label="库存管理", command=lambda: self.open_window(
            "stock", lambda: stock_report.StockWindow(self.win, self.employee_id)))
        menubar.add_cascade(label="进销存", menu=m_biz)

        m_rep = tk.Menu(menubar, tearoff=0)
        m_rep.add_command(label="销售统计", command=lambda: self.open_window(
            "report", lambda: stock_report.ReportWindow(self.win)))
        menubar.add_cascade(label="统计报表", menu=m_rep)

        self.win.config(menu=menubar)

        # 顶部信息
        info = f"当前用户：{user['name']}（{user['role']}）"
        tk.Label(self.win, text=info, font=("微软雅黑", 13)).pack(pady=12)
        tk.Label(self.win, text="请通过上方菜单进入各功能模块", fg="#666").pack()

    def open_window(self, key, factory):
        """打开功能窗口：已存在则提到最前并聚焦，不重复新建；不存在才创建并登记"""
        old = self.open_windows.get(key)
        if old is not None and old.win.winfo_exists():
            # 窗口还开着：只提到最前、夺回焦点，不再新建
            old.win.lift()
            old.win.focus_force()
            return
        # 窗口不存在或已被关闭：新建并登记
        self.open_windows[key] = factory()

    def todo(self):
        messagebox.showinfo("提示", "该模块将在后续步骤实现（当前以会员管理为完整示例）")

    def run(self):
        self.win.mainloop()


# ============================================================
# 三、会员管理窗口（完整 CRUD 示例模板）
#    其余模块照此复制改写：把表名/字段名替换即可
# ============================================================
class MemberWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("会员管理")
        self.win.geometry("720x440")

        # 顶部表单区
        frm = tk.Frame(self.win)
        frm.pack(pady=10)
        tk.Label(frm, text="姓名").grid(row=0, column=0, padx=4)
        self.e_name = tk.Entry(frm, width=12)
        self.e_name.grid(row=0, column=1, padx=4)
        tk.Label(frm, text="电话").grid(row=0, column=2, padx=4)
        self.e_phone = tk.Entry(frm, width=14)
        self.e_phone.grid(row=0, column=3, padx=4)
        tk.Label(frm, text="积分").grid(row=0, column=4, padx=4)
        self.e_points = tk.Entry(frm, width=8)
        self.e_points.grid(row=0, column=5, padx=4)
        tk.Label(frm, text="等级").grid(row=0, column=6, padx=4)
        self.e_level = ttk.Combobox(frm, values=["普通", "银卡", "金卡"], width=8)
        self.e_level.grid(row=0, column=7, padx=4)

        # 按钮区
        btn = tk.Frame(self.win)
        btn.pack(pady=6)
        tk.Button(btn, text="查询", width=8, command=self.query).pack(side="left", padx=5)
        tk.Button(btn, text="新增", width=8, command=self.add).pack(side="left", padx=5)
        tk.Button(btn, text="修改", width=8, command=self.update).pack(side="left", padx=5)
        tk.Button(btn, text="删除", width=8, command=self.delete).pack(side="left", padx=5)
        tk.Button(btn, text="返回", width=8, command=self.close).pack(side="left", padx=5)

        # 数据表格区（Treeview）
        cols = ("member_id", "member_name", "phone", "points", "level", "reg_date")
        heads = ("会员号", "姓名", "电话", "积分", "等级", "注册日期")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=12)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=110, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.tree.bind("<ButtonRelease-1>", self.on_select)

        self.query()

    def query(self):
        """多条件组合查询：姓名/电话模糊，积分精确，等级精确；填了才生效，条件之间是并且"""
        sql = "SELECT member_id, member_name, phone, points, level, reg_date FROM member"
        where = []
        params = []
        # 姓名：模糊匹配
        name = self.e_name.get().strip()
        if name:
            where.append("member_name LIKE ?")
            params.append("%" + name + "%")
        # 电话：模糊匹配（输几位号码就能查）
        phone = self.e_phone.get().strip()
        if phone:
            where.append("phone LIKE ?")
            params.append("%" + phone + "%")
        # 积分：精确匹配（必须是整数，否则提示并中止）
        points = self.e_points.get().strip()
        if points:
            try:
                where.append("points = ?")
                params.append(int(points))
            except ValueError:
                messagebox.showwarning("提示", "积分必须是整数")
                return
        # 等级：精确匹配
        level = self.e_level.get().strip()
        if level:
            where.append("level = ?")
            params.append(level)
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = db.query(sql, params)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["member_id"], r["member_name"],
                                                r["phone"], r["points"],
                                                r["level"], r["reg_date"]))

    def on_select(self, event):
        """点击表格行，回填表单（便于修改）"""
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.e_name.delete(0, "end");   self.e_name.insert(0, vals[1])
        self.e_phone.delete(0, "end");  self.e_phone.insert(0, vals[2])
        self.e_points.delete(0, "end"); self.e_points.insert(0, vals[3])
        self.e_level.set(vals[4])

    def add(self):
        """新增会员（参数化 INSERT）"""
        name, phone = self.e_name.get().strip(), self.e_phone.get().strip()
        points = self.e_points.get().strip() or "0"
        level = self.e_level.get().strip() or "普通"
        if not name:
            messagebox.showwarning("提示", "姓名不能为空")
            return
        try:
            db.execute(
                "INSERT INTO member(member_name, phone, points, level) VALUES (?, ?, ?, ?)",
                [name, phone, int(points), level])
            messagebox.showinfo("成功", "新增会员成功")
            self.query()
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def update(self):
        """修改选中会员（参数化 UPDATE，按主键定位）"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先在表格中选择一行")
            return
        member_id = self.tree.item(sel[0], "values")[0]
        name = self.e_name.get().strip()
        phone = self.e_phone.get().strip()
        points = self.e_points.get().strip() or "0"
        level = self.e_level.get().strip() or "普通"
        try:
            db.execute(
                "UPDATE member SET member_name=?, phone=?, points=?, level=? WHERE member_id=?",
                [name, phone, int(points), level, int(member_id)])
            messagebox.showinfo("成功", "修改会员成功")
            self.query()
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def delete(self):
        """删除选中会员（参数化 DELETE）"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先在表格中选择一行")
            return
        member_id = self.tree.item(sel[0], "values")[0]
        if messagebox.askyesno("确认", "确定删除该会员吗？", parent=self.win):
            try:
                db.execute("DELETE FROM member WHERE member_id=?", [int(member_id)])
                messagebox.showinfo("成功", "删除会员成功")
                self.query()
            except Exception as e:
                messagebox.showerror("失败", str(e))

    def close(self):
        """关闭当前模块窗口，回到主窗口（主窗口一直存在，关掉本窗口即可露出）"""
        self.win.destroy()


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    LoginWindow().run()
