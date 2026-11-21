# -*- coding: utf-8 -*-
"""
sale.py —— 销售管理（组员2负责）
两级结构：
  第一级 SaleWindow：销售单列表 + 筛选 + 新增/出库/返回
  第二级 NewSaleDialog：新增销售单表单（会员 + 明细 + 折扣），保存或返回后回第一级
销售出库：调用存储过程 sp_sale_outbound（事务：校验库存→扣库存→写流水→加积分→改状态）
"""
import tkinter as tk
from tkinter import ttk, messagebox
import db


class SaleWindow:
    def __init__(self, parent, employee_id=1):
        self.win = tk.Toplevel(parent)
        self.win.title("销售管理")
        self.win.geometry("880x440")
        self.employee_id = employee_id

        # 当前生效的查询条件；第一级完整列表时这两个为空
        self.active_where = []
        self.active_params = []
        self.is_filtered = False   # 是否正处于筛选结果（第二级）

        # 筛选条件区（第一级，用于查询）
        filt = tk.Frame(self.win)
        filt.pack(pady=8)
        tk.Label(filt, text="会员").grid(row=0, column=0, padx=4)
        self.f_member = tk.Entry(filt, width=16)
        self.f_member.grid(row=0, column=1, padx=4)
        tk.Label(filt, text="状态").grid(row=0, column=2, padx=4)
        self.f_status = ttk.Combobox(filt, width=10, values=["草稿", "已出库"])
        self.f_status.grid(row=0, column=3, padx=4)

        # 按钮区
        btn = tk.Frame(self.win)
        btn.pack(pady=8)
        tk.Button(btn, text="查询", width=8, command=self.query).pack(side="left", padx=6)
        tk.Button(btn, text="新增销售单", width=12, command=self.new_order).pack(side="left", padx=6)
        tk.Button(btn, text="销售出库", width=12, command=self.outbound).pack(side="left", padx=6)
        tk.Button(btn, text="返回", width=8, command=self.back).pack(side="left", padx=6)

        # 数据表格区（第一级）
        cols = ("sale_order_id", "member_name", "op_date", "total_amount",
                "discount", "paid_amount", "status")
        heads = ("销售单号", "会员", "日期", "总金额", "折扣", "实收", "状态")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=14)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=115, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)

        self._load()

    def query(self):
        """第一级查询：读取筛选框，保存生效条件，加载结果；有条件则进入筛选状态"""
        where = []
        params = []
        # 会员名：模糊（匹配会员表姓名）
        mem = self.f_member.get().strip()
        if mem:
            where.append("m.member_name LIKE ?")
            params.append("%" + mem + "%")
        # 状态：精确
        status = self.f_status.get().strip()
        if status:
            where.append("o.status = ?")
            params.append(status)
        # 保存当前生效条件，供后续刷新使用
        self.active_where = where
        self.active_params = params
        self.is_filtered = bool(where)
        self._load()

    def _load(self):
        """用当前生效条件加载表格（完整列表或筛选结果），不改变层级状态"""
        sql = ("SELECT o.sale_order_id, COALESCE(m.member_name, N'散客') AS member_name, "
               "o.op_date, o.total_amount, o.discount, o.paid_amount, o.status "
               "FROM sale_order o LEFT JOIN member m ON o.member_id = m.member_id")
        if self.active_where:
            sql += " WHERE " + " AND ".join(self.active_where)
        sql += " ORDER BY o.sale_order_id DESC"
        rows = db.query(sql, self.active_params)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["sale_order_id"], r["member_name"],
                                                r["op_date"], r["total_amount"], r["discount"],
                                                r["paid_amount"], r["status"]))

    def new_order(self):
        """打开第二级新增销售单表单"""
        NewSaleDialog(self, self.employee_id)

    def outbound(self):
        """销售出库：调用存储过程 sp_sale_outbound（事务），确认后刷新当前列表"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一张「草稿」状态的销售单", parent=self.win)
            return
        oid = int(self.tree.item(sel[0], "values")[0])
        status = self.tree.item(sel[0], "values")[6]
        if status != "草稿":
            messagebox.showwarning("提示", "只有「草稿」状态的销售单才能出库", parent=self.win)
            return
        try:
            db.call_proc("sp_sale_outbound", [oid, self.employee_id])
            messagebox.showinfo("成功", "销售出库完成，库存/流水/积分已更新", parent=self.win)
            self._load()
        except Exception as e:
            # 存储过程 RAISERROR 的信息在 e.args[0]
            messagebox.showerror("失败", e.args[0] if e.args else str(e), parent=self.win)

    def back(self):
        """返回：筛选中则先清除筛选回完整列表；已在第一级则退出模块"""
        if self.is_filtered:
            # 第一次返回：清除生效条件、清空筛选框、显示全部
            self.active_where = []
            self.active_params = []
            self.is_filtered = False
            self.f_member.delete(0, "end")
            self.f_status.set("")
            self._load()
        else:
            # 第二次返回：退出模块、回主窗口
            self.win.destroy()


class NewSaleDialog:
    """新增销售单表单（第二级）：选会员(可选) + 录明细 + 折扣 + 保存；保存或返回后回第一级"""

    def __init__(self, parent_window, employee_id):
        self.parent_window = parent_window   # 第一级 SaleWindow
        self.win = tk.Toplevel(parent_window.win)
        self.win.title("新增销售单")
        self.win.geometry("600x460")
        self.employee_id = employee_id
        self.items = []   # 临时明细 [(sku_id, info, qty, price), ...]

        # 会员选择 + 折扣
        frm = tk.Frame(self.win)
        frm.pack(pady=8)
        tk.Label(frm, text="会员").grid(row=0, column=0, padx=4)
        self.members = db.query("SELECT member_id, member_name FROM member")
        self.cb_member = ttk.Combobox(frm, width=16)
        self.cb_member["values"] = ["散客"] + ["%s-%s" % (m["member_id"], m["member_name"])
                                               for m in self.members]
        self.cb_member.current(0)
        self.cb_member.grid(row=0, column=1, padx=4)
        tk.Label(frm, text="折扣(如0.9)").grid(row=0, column=2, padx=4)
        self.e_discount = tk.Entry(frm, width=8)
        self.e_discount.insert(0, "1.00")
        self.e_discount.grid(row=0, column=3, padx=4)

        # 明细录入
        frm2 = tk.Frame(self.win)
        frm2.pack(pady=6)
        self.skus = db.query(
            "SELECT s.sku_id, p.style_code, s.color, s.size, s.sale_price "
            "FROM product_sku s JOIN product p ON s.product_id = p.product_id")
        self.cb_sku = ttk.Combobox(frm2, width=20)
        self.cb_sku["values"] = ["%s-%s %s%s" % (s["sku_id"], s["style_code"],
                                                  s["color"], s["size"])
                                 for s in self.skus]
        self.cb_sku.grid(row=0, column=0, padx=4)
        self.e_qty = tk.Entry(frm2, width=8)
        self.e_qty.grid(row=0, column=1, padx=4)
        self.e_price = tk.Entry(frm2, width=10)
        self.e_price.grid(row=0, column=2, padx=4)
        tk.Button(frm2, text="添加明细", command=self.add_item).grid(row=0, column=3, padx=6)

        # 明细列表
        cols = ("sku_id", "info", "quantity", "unit_price", "subtotal")
        heads = ("SKU号", "商品规格", "数量", "单价", "小计")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=10)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=115, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)

        # 底部按钮：保存 + 返回
        foot = tk.Frame(self.win)
        foot.pack(pady=8)
        tk.Button(foot, text="保存销售单", width=14, command=self.save).pack(side="left", padx=8)
        tk.Button(foot, text="返回", width=8, command=self.back).pack(side="left", padx=8)

        # 模态：表单打开时锁定第一级，焦点在表单
        self.win.grab_set()
        self.win.focus_force()

    def add_item(self):
        """添加一行明细到临时列表并刷新明细表"""
        sku_str = self.cb_sku.get().strip()
        if not sku_str:
            messagebox.showwarning("提示", "请选择 SKU", parent=self.win)
            return
        sku_id = int(sku_str.split("-")[0])
        info = sku_str.split("-", 1)[1]
        # 数量：必须是整数
        try:
            qty = int(self.e_qty.get().strip())
        except ValueError:
            messagebox.showwarning("提示", "数量必须是整数，例如 10", parent=self.win)
            return
        # 数量必须大于 0，与数据库 CHECK(quantity>0) 一致
        if qty <= 0:
            messagebox.showwarning("提示", "数量必须大于 0，不能填 0 或负数", parent=self.win)
            return
        # 单价：必须是数字
        try:
            price = float(self.e_price.get().strip())
        except ValueError:
            messagebox.showwarning("提示", "单价必须是数字，例如 100.00", parent=self.win)
            return
        # 单价不能为负
        if price < 0:
            messagebox.showwarning("提示", "单价不能为负数", parent=self.win)
            return
        self.items.append((sku_id, info, qty, price))
        self.tree.insert("", "end", values=(sku_id, info, qty, price, qty * price))

    def save(self):
        """保存：写主单 + 循环写明细（参数化，事务）；成功后关闭表单、回第一级并刷新"""
        if not self.items:
            messagebox.showwarning("提示", "请至少添加一条明细", parent=self.win)
            return
        # 会员：散客或未选时 member_id 为 None
        member_id = None
        m = self.cb_member.get().strip()
        if m and m != "散客" and "-" in m:
            member_id = int(m.split("-")[0])
        # 折扣：必须是数字
        try:
            discount = float(self.e_discount.get().strip())
        except ValueError:
            messagebox.showwarning("提示", "折扣必须是数字，例如 0.9", parent=self.win)
            return
        # 折扣范围 0~1，与数据库 CHECK 一致：1 不打折，0.9 表示九折
        if discount < 0 or discount > 1:
            messagebox.showwarning("提示", "折扣必须在 0 到 1 之间，0.9 表示九折", parent=self.win)
            return
        total = sum(i[2] * i[3] for i in self.items)
        paid = round(total * discount, 2)
        try:
            with db.get_conn() as conn:
                cur = conn.cursor()
                # 用 OUTPUT 在同一条 INSERT 内直接返回新自增 id，避免 SCOPE_IDENTITY
                # 因参数化经 sp_executesql 执行、作用域不一致而取到 NULL
                cur.execute(
                    "INSERT INTO sale_order(member_id, employee_id, total_amount, discount, "
                    "paid_amount, status) OUTPUT INSERTED.sale_order_id "
                    "VALUES (?,?,?,?,?, N'草稿')",
                    [member_id, self.employee_id, total, discount, paid])
                order_id = cur.fetchone()[0]
                for sku_id, _info, qty, price in self.items:
                    cur.execute(
                        "INSERT INTO sale_item(sale_order_id, sku_id, quantity, unit_price, "
                        "subtotal) VALUES (?,?,?,?,?)",
                        [order_id, sku_id, qty, price, qty * price])
                conn.commit()
            messagebox.showinfo("成功", "销售单 %s 已保存（草稿），可点击「销售出库」" % order_id,
                                parent=self.win)
        except Exception as e:
            messagebox.showerror("失败", str(e), parent=self.win)
            return
        # 关闭表单，回第一级并刷新列表
        self.win.grab_release()
        self.win.destroy()
        self.parent_window._load()

    def back(self):
        """第二级返回：只关闭表单、回第一级，不退出模块"""
        self.win.grab_release()
        self.win.destroy()
