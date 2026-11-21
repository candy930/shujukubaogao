# -*- coding: utf-8 -*-
"""
base_data.py —— 基础数据管理：商品管理 + 供应商管理（组长负责）
照 main.py 的会员管理模板实现，全部参数化查询防注入。
"""
import tkinter as tk
from tkinter import ttk, messagebox
import db


# ============================================================
# 供应商管理（标准 CRUD，与会员管理结构一致）
# ============================================================
class SupplierWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("供应商管理")
        self.win.geometry("700x420")

        frm = tk.Frame(self.win)
        frm.pack(pady=10)
        tk.Label(frm, text="名称").grid(row=0, column=0, padx=4)
        self.e_name = tk.Entry(frm, width=16)
        self.e_name.grid(row=0, column=1, padx=4)
        tk.Label(frm, text="联系人").grid(row=0, column=2, padx=4)
        self.e_contact = tk.Entry(frm, width=12)
        self.e_contact.grid(row=0, column=3, padx=4)
        tk.Label(frm, text="电话").grid(row=0, column=4, padx=4)
        self.e_phone = tk.Entry(frm, width=14)
        self.e_phone.grid(row=0, column=5, padx=4)
        tk.Label(frm, text="地址").grid(row=0, column=6, padx=4)
        self.e_addr = tk.Entry(frm, width=18)
        self.e_addr.grid(row=0, column=7, padx=4)

        btn = tk.Frame(self.win)
        btn.pack(pady=6)
        tk.Button(btn, text="查询", width=8, command=self.query).pack(side="left", padx=5)
        tk.Button(btn, text="新增", width=8, command=self.add).pack(side="left", padx=5)
        tk.Button(btn, text="修改", width=8, command=self.update).pack(side="left", padx=5)
        tk.Button(btn, text="删除", width=8, command=self.delete).pack(side="left", padx=5)
        tk.Button(btn, text="返回", width=8, command=self.close).pack(side="left", padx=5)

        cols = ("supplier_id", "supplier_name", "contact", "phone", "address", "status")
        heads = ("供应商号", "名称", "联系人", "电话", "地址", "状态")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=12)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=115, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.tree.bind("<ButtonRelease-1>", self.on_select)
        self.query()

    def query(self):
        """多条件组合查询：名称/联系人/电话/地址都支持模糊，填了才生效，条件之间是并且"""
        sql = "SELECT supplier_id, supplier_name, contact, phone, address, status FROM supplier"
        where = []
        params = []
        # 名称：模糊
        name = self.e_name.get().strip()
        if name:
            where.append("supplier_name LIKE ?")
            params.append("%" + name + "%")
        # 联系人：模糊
        contact = self.e_contact.get().strip()
        if contact:
            where.append("contact LIKE ?")
            params.append("%" + contact + "%")
        # 电话：模糊
        phone = self.e_phone.get().strip()
        if phone:
            where.append("phone LIKE ?")
            params.append("%" + phone + "%")
        # 地址：模糊
        addr = self.e_addr.get().strip()
        if addr:
            where.append("address LIKE ?")
            params.append("%" + addr + "%")
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = db.query(sql, params)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["supplier_id"], r["supplier_name"],
                                                r["contact"], r["phone"],
                                                r["address"], r["status"]))

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        v = self.tree.item(sel[0], "values")
        self.e_name.delete(0, "end"); self.e_name.insert(0, v[1])
        self.e_contact.delete(0, "end"); self.e_contact.insert(0, v[2])
        self.e_phone.delete(0, "end"); self.e_phone.insert(0, v[3])
        self.e_addr.delete(0, "end"); self.e_addr.insert(0, v[4])

    def add(self):
        name = self.e_name.get().strip()
        if not name:
            messagebox.showwarning("提示", "名称不能为空")
            return
        try:
            db.execute("INSERT INTO supplier(supplier_name, contact, phone, address) VALUES (?,?,?,?)",
                       [name, self.e_contact.get().strip(), self.e_phone.get().strip(),
                        self.e_addr.get().strip()])
            messagebox.showinfo("成功", "新增供应商成功")
            self.query()
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def update(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一行")
            return
        sid = self.tree.item(sel[0], "values")[0]
        try:
            db.execute("UPDATE supplier SET supplier_name=?, contact=?, phone=?, address=? WHERE supplier_id=?",
                       [self.e_name.get().strip(), self.e_contact.get().strip(),
                        self.e_phone.get().strip(), self.e_addr.get().strip(), int(sid)])
            messagebox.showinfo("成功", "修改供应商成功")
            self.query()
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一行")
            return
        sid = self.tree.item(sel[0], "values")[0]
        if messagebox.askyesno("确认", "确定删除该供应商吗？"):
            try:
                db.execute("DELETE FROM supplier WHERE supplier_id=?", [int(sid)])
                messagebox.showinfo("成功", "删除供应商成功")
                self.query()
            except Exception as e:
                # 外键 NO ACTION 会阻止删除被采购单引用的供应商
                messagebox.showerror("失败", str(e) + "\n（该供应商已被采购单引用，禁止删除）")

    def close(self):
        """关闭当前模块窗口，回到主窗口（主窗口一直存在，关掉本窗口即可露出）"""
        self.win.destroy()


# ============================================================
# 商品管理（含外键：分类用下拉框选择）
# ============================================================
class ProductWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("商品管理")
        self.win.geometry("820x440")

        frm = tk.Frame(self.win)
        frm.pack(pady=10)
        tk.Label(frm, text="款号").grid(row=0, column=0, padx=3)
        self.e_style = tk.Entry(frm, width=10)
        self.e_style.grid(row=0, column=1, padx=3)
        tk.Label(frm, text="名称").grid(row=0, column=2, padx=3)
        self.e_name = tk.Entry(frm, width=14)
        self.e_name.grid(row=0, column=3, padx=3)
        tk.Label(frm, text="品牌").grid(row=0, column=4, padx=3)
        self.e_brand = tk.Entry(frm, width=10)
        self.e_brand.grid(row=0, column=5, padx=3)
        tk.Label(frm, text="分类").grid(row=0, column=6, padx=3)
        self.cb_category = ttk.Combobox(frm, width=10)
        self.cb_category.grid(row=0, column=7, padx=3)
        tk.Label(frm, text="标准价").grid(row=0, column=8, padx=3)
        self.e_price = tk.Entry(frm, width=8)
        self.e_price.grid(row=0, column=9, padx=3)
        # 加载分类下拉
        self.categories = db.query("SELECT category_id, category_name FROM category")
        self.cb_category["values"] = ["%s-%s" % (c["category_id"], c["category_name"]) for c in self.categories]

        btn = tk.Frame(self.win)
        btn.pack(pady=6)
        tk.Button(btn, text="查询", width=8, command=self.query).pack(side="left", padx=5)
        tk.Button(btn, text="新增", width=8, command=self.add).pack(side="left", padx=5)
        tk.Button(btn, text="修改", width=8, command=self.update).pack(side="left", padx=5)
        tk.Button(btn, text="删除", width=8, command=self.delete).pack(side="left", padx=5)
        tk.Button(btn, text="返回", width=8, command=self.close).pack(side="left", padx=5)

        cols = ("product_id", "style_code", "product_name", "brand",
                "category_name", "standard_price")
        heads = ("商品号", "款号", "名称", "品牌", "分类", "标准售价")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=12)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=125, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.tree.bind("<ButtonRelease-1>", self.on_select)
        self.query()

    def _parse_category(self):
        """从分类下拉框解析出分类号，兼容两种写法：标准 '1-T恤' 与点选表格后的纯名称 'T恤'"""
        s = self.cb_category.get().strip()
        if not s:
            return None
        # 情况一：标准格式 'id-名称'，横线前就是分类号
        if "-" in s:
            try:
                return int(s.split("-")[0])
            except ValueError:
                return None
        # 情况二：点选表格行后下拉框被填成纯名称，按名称在分类列表里反查 id
        for c in self.categories:
            if c["category_name"] == s:
                return c["category_id"]
        return None

    def query(self):
        """多条件组合查询：款号/名称/品牌模糊，分类按id，标准价精确；填了才生效，条件之间是并且"""
        sql = """SELECT p.product_id, p.style_code, p.product_name, p.brand,
                        c.category_name, p.standard_price
                 FROM product p JOIN category c ON p.category_id = c.category_id"""
        where = []
        params = []
        # 款号：模糊
        style = self.e_style.get().strip()
        if style:
            where.append("p.style_code LIKE ?")
            params.append("%" + style + "%")
        # 名称：模糊
        name = self.e_name.get().strip()
        if name:
            where.append("p.product_name LIKE ?")
            params.append("%" + name + "%")
        # 品牌：模糊
        brand = self.e_brand.get().strip()
        if brand:
            where.append("p.brand LIKE ?")
            params.append("%" + brand + "%")
        # 分类：解析下拉框（兼容 id-名称 和纯名称）得到分类 id
        cat_id = self._parse_category()
        if cat_id is not None:
            where.append("p.category_id = ?")
            params.append(cat_id)
        # 标准价：精确匹配（必须是数字，否则提示并中止）
        price = self.e_price.get().strip()
        if price:
            try:
                where.append("p.standard_price = ?")
                params.append(float(price))
            except ValueError:
                messagebox.showwarning("提示", "标准价必须是数字")
                return
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = db.query(sql, params)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["product_id"], r["style_code"],
                                                r["product_name"], r["brand"],
                                                r["category_name"], r["standard_price"]))

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        v = self.tree.item(sel[0], "values")
        self.e_style.delete(0, "end"); self.e_style.insert(0, v[1])
        self.e_name.delete(0, "end");  self.e_name.insert(0, v[2])
        self.e_brand.delete(0, "end"); self.e_brand.insert(0, v[3])
        self.cb_category.set(v[4])
        self.e_price.delete(0, "end"); self.e_price.insert(0, v[5])

    def add(self):
        style, name = self.e_style.get().strip(), self.e_name.get().strip()
        cat_id = self._parse_category()
        if not style or not name or cat_id is None:
            messagebox.showwarning("提示", "款号、名称、分类不能为空")
            return
        try:
            db.execute(
                "INSERT INTO product(style_code, product_name, brand, category_id, standard_price) "
                "VALUES (?,?,?,?,?)",
                [style, name, self.e_brand.get().strip(), cat_id,
                 float(self.e_price.get().strip() or 0)])
            messagebox.showinfo("成功", "新增商品成功")
            self.query()
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def update(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一行")
            return
        pid = self.tree.item(sel[0], "values")[0]
        cat_id = self._parse_category()
        try:
            db.execute(
                "UPDATE product SET style_code=?, product_name=?, brand=?, category_id=?, "
                "standard_price=? WHERE product_id=?",
                [self.e_style.get().strip(), self.e_name.get().strip(),
                 self.e_brand.get().strip(), cat_id,
                 float(self.e_price.get().strip() or 0), int(pid)])
            messagebox.showinfo("成功", "修改商品成功")
            self.query()
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一行")
            return
        pid = self.tree.item(sel[0], "values")[0]
        if messagebox.askyesno("确认", "确定删除该商品吗？"):
            try:
                db.execute("DELETE FROM product WHERE product_id=?", [int(pid)])
                messagebox.showinfo("成功", "删除商品成功")
                self.query()
            except Exception as e:
                messagebox.showerror("失败", str(e) + "\n（该商品存在规格 SKU，禁止删除）")

    def close(self):
        """关闭当前模块窗口，回到主窗口（主窗口一直存在，关掉本窗口即可露出）"""
        self.win.destroy()
