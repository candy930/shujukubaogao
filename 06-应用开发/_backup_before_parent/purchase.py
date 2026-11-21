# -*- coding: utf-8 -*-
"""
purchase.py —— 采购管理（组员1负责）
新增采购单：录入供应商 + 明细（SKU/数量/单价），写主单+明细
采购入库：调用存储过程 sp_purchase_inbound（事务：加库存+写流水+改状态）
"""
import tkinter as tk
from tkinter import ttk, messagebox
import db


class PurchaseWindow:
    def __init__(self, parent, employee_id=1):
        self.win = tk.Toplevel(parent)
        self.win.title("采购管理")
        self.win.geometry("860x460")
        self.employee_id = employee_id

        # 筛选条件区（供应商名 + 状态）
        filt = tk.Frame(self.win)
        filt.pack(pady=6)
        tk.Label(filt, text="供应商").grid(row=0, column=0, padx=4)
        self.f_supplier = tk.Entry(filt, width=16)
        self.f_supplier.grid(row=0, column=1, padx=4)
        tk.Label(filt, text="状态").grid(row=0, column=2, padx=4)
        self.f_status = ttk.Combobox(filt, width=10, values=["草稿", "已入库"])
        self.f_status.grid(row=0, column=3, padx=4)

        btn = tk.Frame(self.win)
        btn.pack(pady=8)
        tk.Button(btn, text="新增采购单", width=12, command=self.new_order).pack(side="left", padx=6)
        tk.Button(btn, text="采购入库", width=12, command=self.inbound).pack(side="left", padx=6)
        tk.Button(btn, text="刷新", width=8, command=self.query).pack(side="left", padx=6)
        tk.Button(btn, text="返回", width=8, command=self.close).pack(side="left", padx=6)

        cols = ("purchase_order_id", "supplier_name", "op_date", "total_amount", "status")
        heads = ("采购单号", "供应商", "日期", "总金额", "状态")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=14)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=150, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.query()

    def query(self):
        """多条件组合查询：供应商名模糊，状态精确；填了才生效，条件之间是并且"""
        sql = ("SELECT o.purchase_order_id, s.supplier_name, o.op_date, o.total_amount, o.status "
               "FROM purchase_order o JOIN supplier s ON o.supplier_id = s.supplier_id")
        where = []
        params = []
        # 供应商名：模糊
        sup = self.f_supplier.get().strip()
        if sup:
            where.append("s.supplier_name LIKE ?")
            params.append("%" + sup + "%")
        # 状态：精确
        status = self.f_status.get().strip()
        if status:
            where.append("o.status = ?")
            params.append(status)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY o.purchase_order_id DESC"
        rows = db.query(sql, params)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["purchase_order_id"], r["supplier_name"],
                                                r["op_date"], r["total_amount"], r["status"]))

    def new_order(self):
        NewPurchaseDialog(self.win, self.employee_id, self.query)

    def inbound(self):
        """采购入库：调用存储过程 sp_purchase_inbound（事务）"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一张「草稿」状态的采购单")
            return
        oid = int(self.tree.item(sel[0], "values")[0])
        status = self.tree.item(sel[0], "values")[4]
        if status != "草稿":
            messagebox.showwarning("提示", "只有「草稿」状态的采购单才能入库")
            return
        try:
            db.call_proc("sp_purchase_inbound", [oid, self.employee_id])
            messagebox.showinfo("成功", "采购入库完成，库存与流水已更新")
            self.query()
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def close(self):
        """关闭当前模块窗口，回到主窗口（主窗口一直存在，关掉本窗口即可露出）"""
        self.win.destroy()


class NewPurchaseDialog:
    """新增采购单弹窗：选供应商 + 录明细 + 保存"""
    def __init__(self, parent, employee_id, on_saved):
        self.win = tk.Toplevel(parent)
        self.win.title("新增采购单")
        self.win.geometry("560x420")
        self.employee_id = employee_id
        self.on_saved = on_saved
        self.items = []  # 临时明细 [(sku_id, qty, price), ...]

        # 供应商选择
        frm = tk.Frame(self.win)
        frm.pack(pady=8)
        tk.Label(frm, text="供应商").grid(row=0, column=0, padx=4)
        self.suppliers = db.query("SELECT supplier_id, supplier_name FROM supplier")
        self.cb_supplier = ttk.Combobox(frm, width=24)
        self.cb_supplier["values"] = ["%s-%s" % (s["supplier_id"], s["supplier_name"]) for s in self.suppliers]
        self.cb_supplier.grid(row=0, column=1, padx=4)

        # 明细录入
        frm2 = tk.Frame(self.win)
        frm2.pack(pady=6)
        self.skus = db.query(
            "SELECT s.sku_id, p.style_code, s.color, s.size, s.purchase_price "
            "FROM product_sku s JOIN product p ON s.product_id = p.product_id")
        self.cb_sku = ttk.Combobox(frm2, width=22)
        self.cb_sku["values"] = ["%s-%s %s%s" % (s["sku_id"], s["style_code"], s["color"], s["size"])
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
            self.tree.column(c, width=110, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)

        tk.Button(self.win, text="保存采购单", width=16, command=self.save).pack(pady=8)

    def add_item(self):
        """添加一行明细到临时列表"""
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
        """保存：写主单 + 循环写明细（参数化，事务）"""
        sup_str = self.cb_supplier.get().strip()
        if not sup_str or not self.items:
            messagebox.showwarning("提示", "请选择供应商并至少添加一条明细")
            return
        supplier_id = int(sup_str.split("-")[0])
        total = sum(i[2] * i[3] for i in self.items)
        try:
            with db.get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO purchase_order(supplier_id, employee_id, total_amount, status) "
                    "VALUES (?,?,?, N'草稿')", [supplier_id, self.employee_id, total])
                cur.execute("SELECT SCOPE_IDENTITY()")
                order_id = cur.fetchone()[0]
                for sku_id, _info, qty, price in self.items:
                    cur.execute(
                        "INSERT INTO purchase_item(purchase_order_id, sku_id, quantity, unit_price, subtotal) "
                        "VALUES (?,?,?,?,?)", [order_id, sku_id, qty, price, qty * price])
                conn.commit()
            messagebox.showinfo("成功", "采购单 %s 已保存（草稿），可点击「采购入库」" % order_id)
            self.win.destroy()
            self.on_saved()
        except Exception as e:
            messagebox.showerror("失败", str(e))
