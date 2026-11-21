# -*- coding: utf-8 -*-
"""
stock_report.py —— 库存管理 + 统计报表（组员3 库存 / 组员4 报表）
库存查询用视图 v_stock；盘点调用存储过程 sp_stock_adjust；
统计用视图 v_sales_report / v_low_stock。
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import db


# ============================================================
# 库存管理（查询 + 盘点调整 + 低库存预警）
# ============================================================
class StockWindow:
    def __init__(self, parent, employee_id=1):
        self.win = tk.Toplevel(parent)
        self.win.title("库存管理")
        self.win.geometry("860x460")
        self.employee_id = employee_id

        # 筛选条件区（关键词 + 颜色 + 状态）
        filt = tk.Frame(self.win)
        filt.pack(pady=6)
        tk.Label(filt, text="关键词").grid(row=0, column=0, padx=4)
        self.f_kw = tk.Entry(filt, width=14)
        self.f_kw.grid(row=0, column=1, padx=4)
        tk.Label(filt, text="颜色").grid(row=0, column=2, padx=4)
        self.f_color = tk.Entry(filt, width=10)
        self.f_color.grid(row=0, column=3, padx=4)
        tk.Label(filt, text="状态").grid(row=0, column=4, padx=4)
        self.f_status = ttk.Combobox(filt, width=10, values=["正常", "预警"])
        self.f_status.grid(row=0, column=5, padx=4)

        btn = tk.Frame(self.win)
        btn.pack(pady=8)
        tk.Button(btn, text="刷新库存", width=10, command=self.query).pack(side="left", padx=6)
        tk.Button(btn, text="低库存预警", width=10, command=self.query_low).pack(side="left", padx=6)
        tk.Button(btn, text="盘点调整", width=10, command=self.adjust).pack(side="left", padx=6)
        tk.Button(btn, text="返回", width=8, command=self.close).pack(side="left", padx=6)

        cols = ("sku_id", "style_code", "product_name", "color", "size",
                "sale_price", "stock_qty", "safe_stock", "stock_status")
        heads = ("SKU号", "款号", "名称", "颜色", "尺码", "售价", "库存", "安全库存", "状态")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=14)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=92, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.query()

    def query(self):
        """多条件组合查询：关键词匹配款号/名称，颜色模糊，状态精确；填了才生效，条件之间是并且"""
        sql = "SELECT * FROM v_stock"
        where = []
        params = []
        # 关键词：同时匹配款号或商品名称（任一中即命中）
        kw = self.f_kw.get().strip()
        if kw:
            where.append("(style_code LIKE ? OR product_name LIKE ?)")
            params.append("%" + kw + "%")
            params.append("%" + kw + "%")
        # 颜色：模糊
        color = self.f_color.get().strip()
        if color:
            where.append("color LIKE ?")
            params.append("%" + color + "%")
        # 状态：精确
        status = self.f_status.get().strip()
        if status:
            where.append("stock_status = ?")
            params.append(status)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY sku_id"
        rows = db.query(sql, params)
        self._fill(rows)

    def query_low(self):
        rows = db.query("SELECT * FROM v_low_stock ORDER BY sku_id")
        self._fill(rows)
        messagebox.showinfo("低库存预警", "已显示 %d 个低于安全库存的 SKU" % len(rows))

    def _fill(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(
                r["sku_id"], r["style_code"], r["product_name"], r["color"], r["size"],
                r["sale_price"], r["stock_qty"], r["safe_stock"], r["stock_status"]))

    def adjust(self):
        """盘点：选中一行，输入实盘数，调用存储过程 sp_stock_adjust"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择要盘点的 SKU")
            return
        sku_id = int(self.tree.item(sel[0], "values")[0])
        actual = simpledialog.askinteger("盘点", "输入实盘库存数量：", parent=self.win)
        if actual is None or actual < 0:
            return
        try:
            db.call_proc("sp_stock_adjust", [sku_id, actual, self.employee_id])
            messagebox.showinfo("成功", "盘点调整完成")
            self.query()
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def close(self):
        """关闭当前模块窗口，回到主窗口（主窗口一直存在，关掉本窗口即可露出）"""
        self.win.destroy()


# ============================================================
# 销售统计报表（查询视图 v_sales_report）
# ============================================================
class ReportWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("销售统计报表")
        self.win.geometry("760x420")

        # 筛选条件区（起始日期 + 结束日期 + 款号）
        filt = tk.Frame(self.win)
        filt.pack(pady=6)
        tk.Label(filt, text="起始日期").grid(row=0, column=0, padx=4)
        self.f_date1 = tk.Entry(filt, width=12)
        self.f_date1.grid(row=0, column=1, padx=4)
        tk.Label(filt, text="结束日期").grid(row=0, column=2, padx=4)
        self.f_date2 = tk.Entry(filt, width=12)
        self.f_date2.grid(padx=4, row=0, column=3)
        tk.Label(filt, text="款号").grid(row=0, column=4, padx=4)
        self.f_style = tk.Entry(filt, width=12)
        self.f_style.grid(row=0, column=5, padx=4)

        btn = tk.Frame(self.win)
        btn.pack(pady=8)
        tk.Button(btn, text="刷新统计", width=12, command=self.query).pack(padx=6)
        tk.Button(btn, text="返回", width=8, command=self.close).pack(side="left", padx=6)
        tk.Label(btn, text="（按日期+商品汇总销量与销售额）", fg="#666").pack(side="left", padx=6)

        cols = ("sale_date", "style_code", "product_name", "total_qty", "total_amount")
        heads = ("销售日期", "款号", "商品名称", "销量", "销售额(元)")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=13)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=140, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.query()

    def query(self):
        """多条件组合查询：日期区间 + 款号模糊；填了才生效，条件之间是并且"""
        from datetime import datetime
        sql = "SELECT * FROM v_sales_report"
        where = []
        params = []
        # 起始日期：校验格式后，查 sale_date >= 该日期
        d1 = self.f_date1.get().strip()
        if d1:
            try:
                dt1 = datetime.strptime(d1, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showwarning("提示", "起始日期格式应为 2025-01-01")
                return
            where.append("sale_date >= ?")
            params.append(dt1)
        # 结束日期：查 sale_date <= 该日期
        d2 = self.f_date2.get().strip()
        if d2:
            try:
                dt2 = datetime.strptime(d2, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showwarning("提示", "结束日期格式应为 2025-01-01")
                return
            where.append("sale_date <= ?")
            params.append(dt2)
        # 款号：模糊
        style = self.f_style.get().strip()
        if style:
            where.append("style_code LIKE ?")
            params.append("%" + style + "%")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY sale_date DESC"
        rows = db.query(sql, params)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(
                r["sale_date"], r["style_code"], r["product_name"],
                r["total_qty"], r["total_amount"]))

    def close(self):
        """关闭当前模块窗口，回到主窗口（主窗口一直存在，关掉本窗口即可露出）"""
        self.win.destroy()
