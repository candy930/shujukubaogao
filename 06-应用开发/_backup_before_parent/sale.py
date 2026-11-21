# -*- coding: utf-8 -*-
"""
sale.py —— 销售管理（组员2负责）
新增销售单：选会员(可选) + 录明细 + 折扣，写主单+明细
销售出库：调用存储过程 sp_sale_outbound（事务：校验库存→扣库存→写流水→加积分→改状态）
"""
import tkinter as tk
from tkinter import ttk, messagebox
import db


class SaleWindow:
    def __init__(self, parent, employee_id=1):
        self.win = tk.Toplevel(parent)
        self.win.title("销售管理")
        self.win.geometry("880x460")
        self.employee_id = employee_id

        # 筛选条件区（会员名 + 状态）
        filt = tk.Frame(self.win)
        filt.pack(pady=6)
        tk.Label(filt, text="会员").grid(row=0, column=0, padx=4)
        self.f_member = tk.Entry(filt, width=16)
        self.f_member.grid(row=0, column=1, padx=4)
        tk.Label(filt, text="状态").grid(row=0, column=2, padx=4)
        self.f_status = ttk.Combobox(filt, width=10, values=["草稿", "已出库"])
        self.f_status.grid(row=0, column=3, padx=4)

        btn = tk.Frame(self.win)
        btn.pack(pady=8)
        tk.Button(btn, text="新增销售单", width=12, command=self.new_order).pack(side="left", padx=6)
        tk.Button(btn, text="销售出库", width=12, command=self.outbound).pack(side="left", padx=6)
        tk.Button(btn, text="刷新", width=8, command=self.query).pack(side="left", padx=6)
        tk.Button(btn, text="返回", width=8, command=self.close).pack(side="left", padx=6)

        cols = ("sale_order_id", "member_name", "op_date", "total_amount", "discount", "paid_amount", "status")
        heads = ("销售单号", "会员", "日期", "总金额", "折扣", "实收", "状态")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=14)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=115, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.query()

    def query(self):
        """多条件组合查询：会员名模糊，状态精确；填了才生效，条件之间是并且"""
        sql = ("SELECT o.sale_order_id, COALESCE(m.member_name, N'散客') AS member_name, "
               "o.op_date, o.total_amount, o.discount, o.paid_amount, o.status "
               "FROM sale_order o LEFT JOIN member m ON o.member_id = m.member_id")
        where = []
        params = []
        # 会员名：模糊（匹配会员表的姓名）
        mem = self.f_member.get().strip()
        if mem:
            where.append("m.member_name LIKE ?")
            params.append("%" + mem + "%")
        # 状态：精确
        status = self.f_status.get().strip()
        if status:
            where.append("o.status = ?")
            params.append(status)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY o.sale_order_id DESC"
        rows = db.query(sql, params)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["sale_order_id"], r["member_name"],
                                                r["op_date"], r["total_amount"], r["discount"],
                                                r["paid_amount"], r["status"]))

    def new_order(self):
        NewSaleDialog(self.win, self.employee_id, self.query)

    def outbound(self):
        """销售出库：调用存储过程 sp_sale_outbound（事务）"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一张「草稿」状态的销售单")
            return
        oid = int(self.tree.item(sel[0], "values")[0])
        status = self.tree.item(sel[0], "values")[6]
        if status != "草稿":
            messagebox.showwarning("提示", "只有「草稿」状态的销售单才能出库")
            return
        try:
            db.call_proc("sp_sale_outbound", [oid, self.employee_id])
            messagebox.showinfo("成功", "销售出库完成，库存/流水/积分已更新")
            self.query()
        except Exception as e:
            messagebox.showerror("失败", e.args[0] if e.args else str(e))

    def close(self):
        """关闭当前模块窗口，回到主窗口（主窗口一直存在，关掉本窗口即可露出）"""
        self.win.destroy()


class NewSaleDialog:
    """新增销售单弹窗：选会员(可选) + 录明细 + 折扣 + 保存"""
    def __init__(self, parent, employee_id, on_saved):
        self.win = tk.Toplevel(parent)
        self.win.title("新增销售单")
        self.win.geometry("600x460")
        self.employee_id = employee_id
        self.on_saved = on_saved
        self.items = []

        frm = tk.Frame(self.win)
        frm.pack(pady=8)
        tk.Label(frm, text="会员").grid(row=0, column=0, padx=4)
        self.members = db.query("SELECT member_id, member_name FROM member")
        self.cb_member = ttk.Combobox(frm, width=16)
        self.cb_member["values"] = ["散客"] + ["%s-%s" % (m["member_id"], m["member_name"]) for m in self.members]
        self.cb_member.current(0)
        self.cb_member.grid(row=0, column=1, padx=4)
        tk.Label(frm, text="折扣(如0.9)").grid(row=0, column=2, padx=4)
        self.e_discount = tk.Entry(frm, width=8)
        self.e_discount.insert(0, "1.00")
        self.e_discount.grid(row=0, column=3, padx=4)

        frm2 = tk.Frame(self.win)
        frm2.pack(pady=6)
        self.skus = db.query(
            "SELECT s.sku_id, p.style_code, s.color, s.size, s.sale_price "
            "FROM product_sku s JOIN product p ON s.product_id = p.product_id")
        self.cb_sku = ttk.Combobox(frm2, width=20)
        self.cb_sku["values"] = ["%s-%s %s%s" % (s["sku_id"], s["style_code"], s["color"], s["size"])
                                 for s in self.skus]
        self.cb_sku.grid(row=0, column=0, padx=4)
        self.e_qty = tk.Entry(frm2, width=8)
        self.e_qty.grid(row=0, column=1, padx=4)
        self.e_price = tk.Entry(frm2, width=10)
        self.e_price.grid(row=0, column=2, padx=4)
        tk.Button(frm2, text="添加明细", command=self.add_item).grid(row=0, column=3, padx=6)

        cols = ("sku_id", "info", "quantity", "unit_price", "subtotal")
        heads = ("SKU号", "商品规格", "数量", "单价", "小计")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=10)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=115, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)

        tk.Button(self.win, text="保存销售单", width=16, command=self.save).pack(pady=8)

    def add_item(self):
        sku_str = self.cb_sku.get().strip()
        if not sku_str:
            messagebox.showwarning("提示", "请选择 SKU")
            return
        sku_id = int(sku_str.split("-")[0])
        info = sku_str.split("-", 1)[1]
        try:
            qty = int(self.e_qty.get().strip())
            price = float(self.e_price.get().strip())
        except ValueError:
            messagebox.showwarning("提示", "数量/单价必须是数字")
            return
        self.items.append((sku_id, info, qty, price))
        self.tree.insert("", "end", values=(sku_id, info, qty, price, qty * price))

    def save(self):
        if not self.items:
            messagebox.showwarning("提示", "请至少添加一条明细")
            return
        member_id = None
        m = self.cb_member.get().strip()
        if m and m != "散客" and "-" in m:
            member_id = int(m.split("-")[0])
        try:
            discount = float(self.e_discount.get().strip())
        except ValueError:
            messagebox.showwarning("提示", "折扣必须是数字(0~1)")
            return
        total = sum(i[2] * i[3] for i in self.items)
        paid = round(total * discount, 2)
        try:
            with db.get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO sale_order(member_id, employee_id, total_amount, discount, paid_amount, status) "
                    "VALUES (?,?,?,?,?, N'草稿')", [member_id, self.employee_id, total, discount, paid])
                cur.execute("SELECT SCOPE_IDENTITY()")
                order_id = cur.fetchone()[0]
                for sku_id, _info, qty, price in self.items:
                    cur.execute(
                        "INSERT INTO sale_item(sale_order_id, sku_id, quantity, unit_price, subtotal) "
                        "VALUES (?,?,?,?,?)", [order_id, sku_id, qty, price, qty * price])
                conn.commit()
            messagebox.showinfo("成功", "销售单 %s 已保存（草稿），可点击「销售出库」" % order_id)
            self.win.destroy()
            self.on_saved()
        except Exception as e:
            messagebox.showerror("失败", str(e))
