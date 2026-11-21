# -*- coding: utf-8 -*-
"""
stock_report.py —— 库存管理 + 统计报表（组员3 库存 / 组员4 报表）
两级结构：
  库存 StockWindow：第一级完整库存列表，第二级为筛选结果或低库存预警；盘点用存储过程
  统计 ReportWindow：第一级完整销售统计，第二级为日期/款号筛选结果
库存查询用视图 v_stock / v_low_stock；盘点调用 sp_stock_adjust；统计用 v_sales_report
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import db


class StockWindow:
    def __init__(self, parent, employee_id=1):
        self.win = tk.Toplevel(parent)
        self.win.title("库存管理")
        self.win.geometry("860x440")
        self.employee_id = employee_id

        # 视图模式：normal 完整库存（第一级），filter 筛选结果，low 低库存预警（后两者第二级）
        self.view_mode = "normal"
        self.active_where = []
        self.active_params = []

        # 筛选条件区（第一级，用于查询）
        filt = tk.Frame(self.win)
        filt.pack(pady=8)
        tk.Label(filt, text="关键词").grid(row=0, column=0, padx=4)
        self.f_kw = tk.Entry(filt, width=14)
        self.f_kw.grid(row=0, column=1, padx=4)
        tk.Label(filt, text="颜色").grid(row=0, column=2, padx=4)
        self.f_color = tk.Entry(filt, width=10)
        self.f_color.grid(row=0, column=3, padx=4)
        tk.Label(filt, text="状态").grid(row=0, column=4, padx=4)
        self.f_status = ttk.Combobox(filt, width=10, values=["正常", "预警"])
        self.f_status.grid(row=0, column=5, padx=4)

        # 按钮区
        btn = tk.Frame(self.win)
        btn.pack(pady=8)
        tk.Button(btn, text="查询", width=10, command=self.query).pack(side="left", padx=6)
        tk.Button(btn, text="低库存预警", width=10, command=self.query_low).pack(side="left", padx=6)
        tk.Button(btn, text="盘点调整", width=10, command=self.adjust).pack(side="left", padx=6)
        tk.Button(btn, text="返回", width=8, command=self.back).pack(side="left", padx=6)

        # 数据表格区（第一级）
        cols = ("sku_id", "style_code", "product_name", "color", "size",
                "sale_price", "stock_qty", "safe_stock", "stock_status")
        heads = ("SKU号", "款号", "名称", "颜色", "尺码", "售价", "库存", "安全库存", "状态")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=14)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=92, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)

        self._load()

    def query(self):
        """第一级查询：读取筛选框，保存生效条件，进入 filter 模式并加载"""
        where = []
        params = []
        # 关键词：同时匹配款号或商品名称（任一命中即可）
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
        # 保存当前生效条件，供后续刷新使用
        self.active_where = where
        self.active_params = params
        self.view_mode = "filter"
        self._load()

    def query_low(self):
        """进入 low 模式（第二级），显示 v_low_stock 低库存预警列表"""
        self.view_mode = "low"
        self._load()
        messagebox.showinfo("低库存预警", "已显示低于安全库存的 SKU", parent=self.win)

    def _load(self):
        """根据当前模式加载表格，不改变层级状态"""
        if self.view_mode == "low":
            rows = db.query("SELECT * FROM v_low_stock ORDER BY sku_id")
        else:
            sql = "SELECT * FROM v_stock"
            if self.active_where:
                sql += " WHERE " + " AND ".join(self.active_where)
            sql += " ORDER BY sku_id"
            rows = db.query(sql, self.active_params)
        self._fill(rows)

    def _fill(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(
                r["sku_id"], r["style_code"], r["product_name"], r["color"], r["size"],
                r["sale_price"], r["stock_qty"], r["safe_stock"], r["stock_status"]))

    def adjust(self):
        """盘点：选中一行，输入实盘数，调用 sp_stock_adjust，确认后刷新当前视图"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择要盘点的 SKU", parent=self.win)
            return
        sku_id = int(self.tree.item(sel[0], "values")[0])
        actual = simpledialog.askinteger("盘点", "输入实盘库存数量：", parent=self.win)
        if actual is None or actual < 0:
            return
        try:
            db.call_proc("sp_stock_adjust", [sku_id, actual, self.employee_id])
            messagebox.showinfo("成功", "盘点调整完成", parent=self.win)
            self._load()
        except Exception as e:
            messagebox.showerror("失败", str(e), parent=self.win)

    def back(self):
        """返回：处于筛选/预警（第二级）则回完整库存列表；已在第一级则退出模块"""
        if self.view_mode != "normal":
            # 第一次返回：清除模式和条件、清空筛选框、显示全部
            self.view_mode = "normal"
            self.active_where = []
            self.active_params = []
            self.f_kw.delete(0, "end")
            self.f_color.delete(0, "end")
            self.f_status.set("")
            self._load()
        else:
            # 第二次返回：退出模块、回主窗口
            self.win.destroy()


class ReportWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("销售统计报表")
        self.win.geometry("760x420")

        # 当前生效的查询条件；第一级完整统计时这两个为空
        self.active_where = []
        self.active_params = []
        self.is_filtered = False   # 是否正处于筛选结果（第二级）

        # 筛选条件区（第一级，用于查询）
        filt = tk.Frame(self.win)
        filt.pack(pady=8)
        tk.Label(filt, text="起始日期").grid(row=0, column=0, padx=4)
        self.f_date1 = tk.Entry(filt, width=12)
        self.f_date1.grid(row=0, column=1, padx=4)
        tk.Label(filt, text="结束日期").grid(row=0, column=2, padx=4)
        self.f_date2 = tk.Entry(filt, width=12)
        self.f_date2.grid(padx=4, row=0, column=3)
        tk.Label(filt, text="款号").grid(row=0, column=4, padx=4)
        self.f_style = tk.Entry(filt, width=12)
        self.f_style.grid(row=0, column=5, padx=4)

        # 按钮区
        btn = tk.Frame(self.win)
        btn.pack(pady=8)
        tk.Button(btn, text="查询", width=8, command=self.query).pack(side="left", padx=6)
        tk.Button(btn, text="返回", width=8, command=self.back).pack(side="left", padx=6)
        tk.Label(btn, text="（按日期+商品汇总销量与销售额）", fg="#666").pack(side="left", padx=6)

        # 数据表格区（第一级）
        cols = ("sale_date", "style_code", "product_name", "total_qty", "total_amount")
        heads = ("销售日期", "款号", "商品名称", "销量", "销售额(元)")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=13)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=140, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)

        self._load()

    def query(self):
        """第一级查询：读取筛选框，保存生效条件，进入筛选状态并加载"""
        from datetime import datetime
        where = []
        params = []
        # 起始日期：校验格式后，查 sale_date >= 该日期
        d1 = self.f_date1.get().strip()
        if d1:
            try:
                dt1 = datetime.strptime(d1, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showwarning("提示", "起始日期格式应为 2025-01-01", parent=self.win)
                return
            where.append("sale_date >= ?")
            params.append(dt1)
        # 结束日期：查 sale_date <= 该日期
        d2 = self.f_date2.get().strip()
        if d2:
            try:
                dt2 = datetime.strptime(d2, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showwarning("提示", "结束日期格式应为 2025-01-01", parent=self.win)
                return
            where.append("sale_date <= ?")
            params.append(dt2)
        # 款号：模糊
        style = self.f_style.get().strip()
        if style:
            where.append("style_code LIKE ?")
            params.append("%" + style + "%")
        # 保存当前生效条件，供后续刷新使用
        self.active_where = where
        self.active_params = params
        self.is_filtered = bool(where)
        self._load()

    def _load(self):
        """用当前生效条件加载表格（完整统计或筛选结果），不改变层级状态"""
        sql = "SELECT * FROM v_sales_report"
        if self.active_where:
            sql += " WHERE " + " AND ".join(self.active_where)
        sql += " ORDER BY sale_date DESC"
        rows = db.query(sql, self.active_params)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(
                r["sale_date"], r["style_code"], r["product_name"],
                r["total_qty"], r["total_amount"]))

    def back(self):
        """返回：筛选中则清除筛选回完整统计；已在第一级则退出模块"""
        if self.is_filtered:
            # 第一次返回：清除生效条件、清空筛选框、显示全部
            self.active_where = []
            self.active_params = []
            self.is_filtered = False
            self.f_date1.delete(0, "end")
            self.f_date2.delete(0, "end")
            self.f_style.delete(0, "end")
            self._load()
        else:
            # 第二次返回：退出模块、回主窗口
            self.win.destroy()
