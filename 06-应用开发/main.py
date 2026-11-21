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
            messagebox.showwarning("提示", "请输入登录名和密码", parent=self.win)
            return
        try:
            # 密码 MD5 后传给 sp_login（数据库存哈希，非明文），参数化防注入
            pwd_hash = hashlib.md5(pwd.encode("utf-8")).hexdigest()
            rows = db.call_proc("sp_login", [name, pwd_hash])
            if rows:
                self.win.destroy()
                MainWindow(rows[0])  # 传入 {employee_id, name, role}
            else:
                messagebox.showerror("失败", "登录名或密码错误，或账号已停用", parent=self.win)
        except Exception as e:
            messagebox.showerror("数据库错误", str(e), parent=self.win)

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
        messagebox.showinfo("提示", "该模块将在后续步骤实现（当前以会员管理为完整示例）", parent=self.win)

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
        self.win.geometry("720x420")

        # 当前生效的查询条件；第一级完整列表时这两个为空
        self.active_where = []
        self.active_params = []
        self.is_filtered = False   # 是否正处于筛选结果（第二级）

        # 筛选条件区（第一级，用于查询）
        filt = tk.Frame(self.win)
        filt.pack(pady=10)
        tk.Label(filt, text="姓名").grid(row=0, column=0, padx=4)
        self.e_name = tk.Entry(filt, width=10)
        self.e_name.grid(row=0, column=1, padx=4)
        tk.Label(filt, text="电话").grid(row=0, column=2, padx=4)
        self.e_phone = tk.Entry(filt, width=12)
        self.e_phone.grid(row=0, column=3, padx=4)
        tk.Label(filt, text="积分").grid(row=0, column=4, padx=4)
        self.e_points = tk.Entry(filt, width=8)
        self.e_points.grid(row=0, column=5, padx=4)
        tk.Label(filt, text="等级").grid(row=0, column=6, padx=4)
        self.e_level = ttk.Combobox(filt, values=["普通", "银卡", "金卡"], width=8)
        self.e_level.grid(row=0, column=7, padx=4)

        # 按钮区
        btn = tk.Frame(self.win)
        btn.pack(pady=6)
        tk.Button(btn, text="查询", width=8, command=self.query).pack(side="left", padx=5)
        tk.Button(btn, text="新增", width=8, command=self.add).pack(side="left", padx=5)
        tk.Button(btn, text="修改", width=8, command=self.update).pack(side="left", padx=5)
        tk.Button(btn, text="删除", width=8, command=self.delete).pack(side="left", padx=5)
        tk.Button(btn, text="返回", width=8, command=self.back).pack(side="left", padx=5)

        # 数据表格区（第一级）
        cols = ("member_id", "member_name", "phone", "points", "level", "reg_date")
        heads = ("会员号", "姓名", "电话", "积分", "等级", "注册日期")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=12)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=110, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)

        self._load()

    def query(self):
        """第一级查询：读取筛选框，保存生效条件，加载结果；有条件则进入筛选状态"""
        where = []
        params = []
        # 姓名：模糊
        name = self.e_name.get().strip()
        if name:
            where.append("member_name LIKE ?")
            params.append("%" + name + "%")
        # 电话：模糊
        phone = self.e_phone.get().strip()
        if phone:
            where.append("phone LIKE ?")
            params.append("%" + phone + "%")
        # 积分：精确，非整数则中止
        points = self.e_points.get().strip()
        if points:
            try:
                where.append("points = ?")
                params.append(int(points))
            except ValueError:
                messagebox.showwarning("提示", "积分必须是整数", parent=self.win)
                return
        # 等级：精确
        level = self.e_level.get().strip()
        if level:
            where.append("level = ?")
            params.append(level)
        # 保存当前生效条件，供后续刷新使用
        self.active_where = where
        self.active_params = params
        self.is_filtered = bool(where)
        self._load()

    def _load(self):
        """用当前生效条件加载表格（完整列表或筛选结果），不改变层级状态"""
        sql = "SELECT member_id, member_name, phone, points, level, reg_date FROM member"
        if self.active_where:
            sql += " WHERE " + " AND ".join(self.active_where)
        rows = db.query(sql, self.active_params)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["member_id"], r["member_name"],
                                                r["phone"], r["points"],
                                                r["level"], r["reg_date"]))

    def add(self):
        """打开第二级新增表单（空白）"""
        MemberFormDialog(self, None)

    def update(self):
        """打开第二级修改表单，预填选中行"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先在表格中选择一行", parent=self.win)
            return
        vals = self.tree.item(sel[0], "values")
        member = {
            "member_id": vals[0],
            "member_name": vals[1],
            "phone": vals[2],
            "points": vals[3],
            "level": vals[4],
        }
        MemberFormDialog(self, member)

    def delete(self):
        """删除选中行，确认后刷新当前列表（不进第二级）"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先在表格中选择一行", parent=self.win)
            return
        member_id = self.tree.item(sel[0], "values")[0]
        if messagebox.askyesno("确认", "确定删除该会员吗？", parent=self.win):
            try:
                db.execute("DELETE FROM member WHERE member_id=?", [int(member_id)])
                messagebox.showinfo("成功", "删除会员成功", parent=self.win)
                self._load()
            except Exception as e:
                messagebox.showerror("失败", str(e), parent=self.win)

    def back(self):
        """返回：筛选中则先清除筛选回完整列表；已在第一级则退出模块"""
        if self.is_filtered:
            # 第一次返回：清除生效条件、清空筛选框、显示全部
            self.active_where = []
            self.active_params = []
            self.is_filtered = False
            self.e_name.delete(0, "end")
            self.e_phone.delete(0, "end")
            self.e_points.delete(0, "end")
            self.e_level.set("")
            self._load()
        else:
            # 第二次返回：退出模块、回主窗口
            self.win.destroy()


class MemberFormDialog:
    """会员新增/修改表单（第二级）。保存或返回后关闭，回到第一级列表"""

    def __init__(self, parent_window, member):
        self.parent_window = parent_window   # 第一级 MemberWindow
        self.member = member                 # 非 None 表示修改，None 表示新增
        self.top = tk.Toplevel(parent_window.win)
        self.top.title("修改会员" if member else "新增会员")
        self.top.geometry("360x280")

        # 输入框
        frm = tk.Frame(self.top)
        frm.pack(pady=18)
        tk.Label(frm, text="姓名").grid(row=0, column=0, padx=6, pady=8)
        self.e_name = tk.Entry(frm, width=18)
        self.e_name.grid(row=0, column=1)
        tk.Label(frm, text="电话").grid(row=1, column=0, padx=6, pady=8)
        self.e_phone = tk.Entry(frm, width=18)
        self.e_phone.grid(row=1, column=1)
        tk.Label(frm, text="积分").grid(row=2, column=0, padx=6, pady=8)
        self.e_points = tk.Entry(frm, width=18)
        self.e_points.grid(row=2, column=1)
        tk.Label(frm, text="等级").grid(row=3, column=0, padx=6, pady=8)
        self.e_level = ttk.Combobox(frm, values=["普通", "银卡", "金卡"], width=16)
        self.e_level.grid(row=3, column=1)

        # 修改时预填，新增时给默认等级
        if member:
            self.e_name.insert(0, member["member_name"])
            self.e_phone.insert(0, member["phone"] or "")
            self.e_points.insert(0, member["points"])
            self.e_level.set(member["level"])
        else:
            self.e_level.set("普通")

        # 按钮
        btn = tk.Frame(self.top)
        btn.pack(pady=8)
        tk.Button(btn, text="保存", width=8, command=self.save).pack(side="left", padx=8)
        tk.Button(btn, text="返回", width=8, command=self.back).pack(side="left", padx=8)

        # 模态：表单打开时锁定第一级，焦点在表单
        self.top.grab_set()
        self.top.focus_force()

    def save(self):
        """保存：修改走 UPDATE，新增走 INSERT；成功后关闭表单、回第一级并刷新"""
        name = self.e_name.get().strip()
        phone = self.e_phone.get().strip()
        points = self.e_points.get().strip() or "0"
        level = self.e_level.get().strip() or "普通"
        if not name:
            messagebox.showwarning("提示", "姓名不能为空", parent=self.top)
            return
        try:
            if self.member:
                db.execute(
                    "UPDATE member SET member_name=?, phone=?, points=?, level=? WHERE member_id=?",
                    [name, phone, int(points), level, self.member["member_id"]])
                messagebox.showinfo("成功", "修改会员成功", parent=self.top)
            else:
                db.execute(
                    "INSERT INTO member(member_name, phone, points, level) VALUES (?, ?, ?, ?)",
                    [name, phone, int(points), level])
                messagebox.showinfo("成功", "新增会员成功", parent=self.top)
        except ValueError:
            # int(points) 失败
            messagebox.showwarning("提示", "积分必须是整数", parent=self.top)
            return
        except Exception as e:
            messagebox.showerror("失败", str(e), parent=self.top)
            return
        # 关闭表单，回第一级并刷新列表
        self.top.grab_release()
        self.top.destroy()
        self.parent_window._load()

    def back(self):
        """第二级返回：只关闭表单、回第一级，不退出模块"""
        self.top.grab_release()
        self.top.destroy()


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    LoginWindow().run()
