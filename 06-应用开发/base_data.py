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

        # 当前生效的查询条件；第一级完整列表时这两个为空
        self.active_where = []
        self.active_params = []
        self.is_filtered = False   # 是否正处于筛选结果（第二级）

        # 筛选条件区（第一级，用于查询）
        filt = tk.Frame(self.win)
        filt.pack(pady=10)
        tk.Label(filt, text="名称").grid(row=0, column=0, padx=4)
        self.e_name = tk.Entry(filt, width=14)
        self.e_name.grid(row=0, column=1, padx=4)
        tk.Label(filt, text="联系人").grid(row=0, column=2, padx=4)
        self.e_contact = tk.Entry(filt, width=12)
        self.e_contact.grid(row=0, column=3, padx=4)
        tk.Label(filt, text="电话").grid(row=0, column=4, padx=4)
        self.e_phone = tk.Entry(filt, width=14)
        self.e_phone.grid(row=0, column=5, padx=4)
        tk.Label(filt, text="地址").grid(row=0, column=6, padx=4)
        self.e_addr = tk.Entry(filt, width=16)
        self.e_addr.grid(row=0, column=7, padx=4)

        # 按钮区
        btn = tk.Frame(self.win)
        btn.pack(pady=6)
        tk.Button(btn, text="查询", width=8, command=self.query).pack(side="left", padx=5)
        tk.Button(btn, text="新增", width=8, command=self.add).pack(side="left", padx=5)
        tk.Button(btn, text="修改", width=8, command=self.update).pack(side="left", padx=5)
        tk.Button(btn, text="删除", width=8, command=self.delete).pack(side="left", padx=5)
        tk.Button(btn, text="返回", width=8, command=self.back).pack(side="left", padx=5)

        # 数据表格区（第一级）
        cols = ("supplier_id", "supplier_name", "contact", "phone", "address", "status")
        heads = ("供应商号", "名称", "联系人", "电话", "地址", "状态")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=12)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=115, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)

        self._load()

    def query(self):
        """第一级查询：读取筛选框，保存生效条件，加载结果；有条件则进入筛选状态"""
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
        # 保存当前生效条件，供后续刷新使用
        self.active_where = where
        self.active_params = params
        self.is_filtered = bool(where)
        self._load()

    def _load(self):
        """用当前生效条件加载表格（完整列表或筛选结果），不改变层级状态"""
        sql = "SELECT supplier_id, supplier_name, contact, phone, address, status FROM supplier"
        if self.active_where:
            sql += " WHERE " + " AND ".join(self.active_where)
        rows = db.query(sql, self.active_params)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["supplier_id"], r["supplier_name"],
                                                r["contact"], r["phone"],
                                                r["address"], r["status"]))

    def add(self):
        """打开第二级新增表单（空白）"""
        SupplierFormDialog(self, None)

    def update(self):
        """打开第二级修改表单，预填选中行"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一行", parent=self.win)
            return
        vals = self.tree.item(sel[0], "values")
        supplier = {
            "supplier_id": vals[0],
            "supplier_name": vals[1],
            "contact": vals[2],
            "phone": vals[3],
            "address": vals[4],
        }
        SupplierFormDialog(self, supplier)

    def delete(self):
        """删除选中行，确认后刷新当前列表（不进第二级）"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一行", parent=self.win)
            return
        sid = self.tree.item(sel[0], "values")[0]
        if messagebox.askyesno("确认", "确定删除该供应商吗？", parent=self.win):
            try:
                db.execute("DELETE FROM supplier WHERE supplier_id=?", [int(sid)])
                messagebox.showinfo("成功", "删除供应商成功", parent=self.win)
                self._load()
            except Exception as e:
                # 外键 NO ACTION 阻止删除被采购单引用的供应商
                messagebox.showerror("失败", str(e) + "\n（该供应商已被采购单引用，禁止删除）", parent=self.win)

    def back(self):
        """返回：筛选中则先清除筛选回完整列表；已在第一级则退出模块"""
        if self.is_filtered:
            # 第一次返回：清除生效条件、清空筛选框、显示全部
            self.active_where = []
            self.active_params = []
            self.is_filtered = False
            self.e_name.delete(0, "end")
            self.e_contact.delete(0, "end")
            self.e_phone.delete(0, "end")
            self.e_addr.delete(0, "end")
            self._load()
        else:
            # 第二次返回：退出模块、回主窗口
            self.win.destroy()


class SupplierFormDialog:
    """供应商新增/修改表单（第二级）。保存或返回后关闭，回到第一级列表"""

    def __init__(self, parent_window, supplier):
        self.parent_window = parent_window   # 第一级 SupplierWindow
        self.supplier = supplier             # 非 None 表示修改，None 表示新增
        self.top = tk.Toplevel(parent_window.win)
        self.top.title("修改供应商" if supplier else "新增供应商")
        self.top.geometry("380x300")

        # 输入框
        frm = tk.Frame(self.top)
        frm.pack(pady=18)
        tk.Label(frm, text="名称").grid(row=0, column=0, padx=6, pady=8)
        self.e_name = tk.Entry(frm, width=18)
        self.e_name.grid(row=0, column=1)
        tk.Label(frm, text="联系人").grid(row=1, column=0, padx=6, pady=8)
        self.e_contact = tk.Entry(frm, width=18)
        self.e_contact.grid(row=1, column=1)
        tk.Label(frm, text="电话").grid(row=2, column=0, padx=6, pady=8)
        self.e_phone = tk.Entry(frm, width=18)
        self.e_phone.grid(row=2, column=1)
        tk.Label(frm, text="地址").grid(row=3, column=0, padx=6, pady=8)
        self.e_addr = tk.Entry(frm, width=18)
        self.e_addr.grid(row=3, column=1)

        # 修改时预填
        if supplier:
            self.e_name.insert(0, supplier["supplier_name"])
            self.e_contact.insert(0, supplier["contact"] or "")
            self.e_phone.insert(0, supplier["phone"] or "")
            self.e_addr.insert(0, supplier["address"] or "")

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
        if not name:
            messagebox.showwarning("提示", "名称不能为空", parent=self.top)
            return
        contact = self.e_contact.get().strip()
        phone = self.e_phone.get().strip()
        addr = self.e_addr.get().strip()
        try:
            if self.supplier:
                db.execute(
                    "UPDATE supplier SET supplier_name=?, contact=?, phone=?, address=? WHERE supplier_id=?",
                    [name, contact, phone, addr, self.supplier["supplier_id"]])
                messagebox.showinfo("成功", "修改供应商成功", parent=self.top)
            else:
                db.execute(
                    "INSERT INTO supplier(supplier_name, contact, phone, address) VALUES (?,?,?,?)",
                    [name, contact, phone, addr])
                messagebox.showinfo("成功", "新增供应商成功", parent=self.top)
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
# 商品管理（含外键：分类用下拉框选择）
# ============================================================
class ProductWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("商品管理")
        self.win.geometry("900x420")

        # 当前生效的查询条件；第一级完整列表时这两个为空
        self.active_where = []
        self.active_params = []
        self.is_filtered = False   # 是否正处于筛选结果（第二级）

        # 分类数据（筛选框和表单都要用）
        self.categories = db.query("SELECT category_id, category_name FROM category")
        cat_values = ["%s-%s" % (c["category_id"], c["category_name"]) for c in self.categories]

        # 筛选条件区（第一级，用于查询）
        filt = tk.Frame(self.win)
        filt.pack(pady=10)
        tk.Label(filt, text="款号").grid(row=0, column=0, padx=3)
        self.e_style = tk.Entry(filt, width=10)
        self.e_style.grid(row=0, column=1, padx=3)
        tk.Label(filt, text="名称").grid(row=0, column=2, padx=3)
        self.e_name = tk.Entry(filt, width=12)
        self.e_name.grid(row=0, column=3, padx=3)
        tk.Label(filt, text="品牌").grid(row=0, column=4, padx=3)
        self.e_brand = tk.Entry(filt, width=10)
        self.e_brand.grid(row=0, column=5, padx=3)
        tk.Label(filt, text="分类").grid(row=0, column=6, padx=3)
        self.cb_category = ttk.Combobox(filt, width=10, values=cat_values)
        self.cb_category.grid(row=0, column=7, padx=3)
        tk.Label(filt, text="标准价").grid(row=0, column=8, padx=3)
        self.e_price = tk.Entry(filt, width=8)
        self.e_price.grid(row=0, column=9, padx=3)

        # 按钮区
        btn = tk.Frame(self.win)
        btn.pack(pady=6)
        tk.Button(btn, text="查询", width=8, command=self.query).pack(side="left", padx=5)
        tk.Button(btn, text="新增", width=8, command=self.add).pack(side="left", padx=5)
        tk.Button(btn, text="修改", width=8, command=self.update).pack(side="left", padx=5)
        tk.Button(btn, text="规格管理", width=10, command=self.manage_sku).pack(side="left", padx=5)
        tk.Button(btn, text="删除", width=8, command=self.delete).pack(side="left", padx=5)
        tk.Button(btn, text="返回", width=8, command=self.back).pack(side="left", padx=5)

        # 数据表格区（第一级）
        cols = ("product_id", "style_code", "product_name", "brand",
                "category_name", "standard_price")
        heads = ("商品号", "款号", "名称", "品牌", "分类", "标准售价")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=12)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=125, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)

        self._load()

    def _parse_category(self, text):
        """从分类文本解析分类号，兼容标准 '1-T恤' 与纯名称 'T恤'"""
        s = (text or "").strip()
        if not s:
            return None
        # 标准格式：横线前是分类号
        if "-" in s:
            try:
                return int(s.split("-")[0])
            except ValueError:
                return None
        # 纯名称：在分类列表里反查 id
        for c in self.categories:
            if c["category_name"] == s:
                return c["category_id"]
        return None

    def query(self):
        """第一级查询：读取筛选框，保存生效条件，加载结果；有条件则进入筛选状态"""
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
        # 分类：解析下拉得到 id
        cat_id = self._parse_category(self.cb_category.get())
        if cat_id is not None:
            where.append("p.category_id = ?")
            params.append(cat_id)
        # 标准价：精确，非数字则中止
        price = self.e_price.get().strip()
        if price:
            try:
                where.append("p.standard_price = ?")
                params.append(float(price))
            except ValueError:
                messagebox.showwarning("提示", "标准价必须是数字", parent=self.win)
                return
        # 保存当前生效条件，供后续刷新使用
        self.active_where = where
        self.active_params = params
        self.is_filtered = bool(where)
        self._load()

    def _load(self):
        """用当前生效条件加载表格（完整列表或筛选结果），不改变层级状态"""
        sql = """SELECT p.product_id, p.style_code, p.product_name, p.brand,
                        c.category_name, p.standard_price
                 FROM product p JOIN category c ON p.category_id = c.category_id"""
        if self.active_where:
            sql += " WHERE " + " AND ".join(self.active_where)
        rows = db.query(sql, self.active_params)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["product_id"], r["style_code"],
                                                r["product_name"], r["brand"],
                                                r["category_name"], r["standard_price"]))

    def manage_sku(self):
        """打开当前选中款的 SKU 规格列表（第二级）"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先在表格中选择一个款", parent=self.win)
            return
        vals = self.tree.item(sel[0], "values")
        product = {
            "product_id": vals[0],
            "style_code": vals[1],
            "product_name": vals[2],
        }
        SkuWindow(self, product)

    def add(self):
        """打开第二级新增表单（空白）"""
        ProductFormDialog(self, None)

    def update(self):
        """打开第二级修改表单，预填选中行"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一行", parent=self.win)
            return
        vals = self.tree.item(sel[0], "values")
        product = {
            "product_id": vals[0],
            "style_code": vals[1],
            "product_name": vals[2],
            "brand": vals[3],
            "category_name": vals[4],
            "standard_price": vals[5],
        }
        ProductFormDialog(self, product)

    def delete(self):
        """删除选中行，确认后刷新当前列表（不进第二级）"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一行", parent=self.win)
            return
        pid = self.tree.item(sel[0], "values")[0]
        if messagebox.askyesno("确认", "确定删除该商品吗？", parent=self.win):
            try:
                db.execute("DELETE FROM product WHERE product_id=?", [int(pid)])
                messagebox.showinfo("成功", "删除商品成功", parent=self.win)
                self._load()
            except Exception as e:
                messagebox.showerror("失败", str(e) + "\n（该商品存在规格 SKU，禁止删除）", parent=self.win)

    def back(self):
        """返回：筛选中则先清除筛选回完整列表；已在第一级则退出模块"""
        if self.is_filtered:
            # 第一次返回：清除生效条件、清空筛选框、显示全部
            self.active_where = []
            self.active_params = []
            self.is_filtered = False
            self.e_style.delete(0, "end")
            self.e_name.delete(0, "end")
            self.e_brand.delete(0, "end")
            self.cb_category.set("")
            self.e_price.delete(0, "end")
            self._load()
        else:
            # 第二次返回：退出模块、回主窗口
            self.win.destroy()


class ProductFormDialog:
    """商品新增/修改表单（第二级）。保存或返回后关闭，回到第一级列表"""

    def __init__(self, parent_window, product):
        self.parent_window = parent_window   # 第一级 ProductWindow
        self.product = product               # 非 None 表示修改，None 表示新增
        self.top = tk.Toplevel(parent_window.win)
        self.top.title("修改商品" if product else "新增商品")
        self.top.geometry("400x340")

        # 分类下拉，统一用标准 id-名称 格式
        cat_values = ["%s-%s" % (c["category_id"], c["category_name"]) for c in parent_window.categories]

        # 输入框
        frm = tk.Frame(self.top)
        frm.pack(pady=16)
        tk.Label(frm, text="款号").grid(row=0, column=0, padx=6, pady=7)
        self.e_style = tk.Entry(frm, width=18)
        self.e_style.grid(row=0, column=1)
        tk.Label(frm, text="名称").grid(row=1, column=0, padx=6, pady=7)
        self.e_name = tk.Entry(frm, width=18)
        self.e_name.grid(row=1, column=1)
        tk.Label(frm, text="品牌").grid(row=2, column=0, padx=6, pady=7)
        self.e_brand = tk.Entry(frm, width=18)
        self.e_brand.grid(row=2, column=1)
        tk.Label(frm, text="分类").grid(row=3, column=0, padx=6, pady=7)
        self.cb_category = ttk.Combobox(frm, width=16, values=cat_values)
        self.cb_category.grid(row=3, column=1)
        tk.Label(frm, text="标准价").grid(row=4, column=0, padx=6, pady=7)
        self.e_price = tk.Entry(frm, width=18)
        self.e_price.grid(row=4, column=1)

        # 修改时预填；分类按名称匹配到对应的 id-名称 项
        if product:
            self.e_style.insert(0, product["style_code"])
            self.e_name.insert(0, product["product_name"])
            self.e_brand.insert(0, product["brand"] or "")
            self.e_price.insert(0, product["standard_price"])
            for cv in cat_values:
                if cv.split("-", 1)[1] == product["category_name"]:
                    self.cb_category.set(cv)
                    break

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
        style = self.e_style.get().strip()
        name = self.e_name.get().strip()
        brand = self.e_brand.get().strip()
        price_text = self.e_price.get().strip() or "0"
        # 表单下拉始终是 id-名称，取横线前 id
        cat_text = self.cb_category.get().strip()
        cat_id = None
        if cat_text and "-" in cat_text:
            try:
                cat_id = int(cat_text.split("-")[0])
            except ValueError:
                cat_id = None
        if not style or not name or cat_id is None:
            messagebox.showwarning("提示", "款号、名称、分类不能为空", parent=self.top)
            return
        try:
            price = float(price_text)
            if self.product:
                db.execute(
                    "UPDATE product SET style_code=?, product_name=?, brand=?, category_id=?, "
                    "standard_price=? WHERE product_id=?",
                    [style, name, brand, cat_id, price, self.product["product_id"]])
                messagebox.showinfo("成功", "修改商品成功", parent=self.top)
            else:
                db.execute(
                    "INSERT INTO product(style_code, product_name, brand, category_id, standard_price) "
                    "VALUES (?,?,?,?,?)",
                    [style, name, brand, cat_id, price])
                messagebox.showinfo("成功", "新增商品成功", parent=self.top)
        except ValueError:
            # float(price_text) 失败
            messagebox.showwarning("提示", "标准价必须是数字", parent=self.top)
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
# 规格 SKU 管理（款列表下的第二级：管理某款的颜色尺码与价格库存）
# ============================================================
class SkuWindow:
    """某款的 SKU 规格列表（第二级）：新增/修改/删除具体规格，返回回款列表"""

    def __init__(self, parent_window, product):
        self.parent_window = parent_window   # 第一级 ProductWindow
        self.product = product               # 所属款信息
        self.win = tk.Toplevel(parent_window.win)
        self.win.title("规格管理 - %s %s" % (product["style_code"], product["product_name"]))
        self.win.geometry("820x420")

        # 顶部提示当前正在管理哪个款
        tk.Label(
            self.win,
            text="款号 %s　%s　（商品号 %s）的具体规格"
                 % (product["style_code"], product["product_name"], product["product_id"]),
            fg="#333").pack(pady=8)

        # 按钮区
        btn = tk.Frame(self.win)
        btn.pack(pady=6)
        tk.Button(btn, text="新增规格", width=10, command=self.add).pack(side="left", padx=5)
        tk.Button(btn, text="修改规格", width=10, command=self.update).pack(side="left", padx=5)
        tk.Button(btn, text="删除规格", width=10, command=self.delete).pack(side="left", padx=5)
        tk.Button(btn, text="返回", width=8, command=self.back).pack(side="left", padx=5)

        # SKU 表格区
        cols = ("sku_id", "color", "size", "purchase_price", "sale_price",
                "stock_qty", "safe_stock")
        heads = ("SKU号", "颜色", "尺码", "进价", "售价", "库存", "安全库存")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=12)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=105, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)

        self._load()

    def _load(self):
        """加载该款的全部 SKU（参数化，按 SKU 号排序）"""
        rows = db.query(
            "SELECT sku_id, color, size, purchase_price, sale_price, stock_qty, safe_stock "
            "FROM product_sku WHERE product_id=? ORDER BY sku_id",
            [int(self.product["product_id"])])
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["sku_id"], r["color"], r["size"],
                                                r["purchase_price"], r["sale_price"],
                                                r["stock_qty"], r["safe_stock"]))

    def add(self):
        """打开空白 SKU 表单（新增）"""
        SkuFormDialog(self, None)

    def update(self):
        """打开预填的 SKU 表单（修改）"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个规格", parent=self.win)
            return
        vals = self.tree.item(sel[0], "values")
        sku = {
            "sku_id": vals[0],
            "color": vals[1],
            "size": vals[2],
            "purchase_price": vals[3],
            "sale_price": vals[4],
            "stock_qty": vals[5],
            "safe_stock": vals[6],
        }
        SkuFormDialog(self, sku)

    def delete(self):
        """删除选中规格，已被单据引用时外键会阻止删除"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个规格", parent=self.win)
            return
        sku_id = self.tree.item(sel[0], "values")[0]
        if messagebox.askyesno("确认", "确定删除该规格吗？若已被采购/销售单据引用将无法删除。",
                               parent=self.win):
            try:
                db.execute("DELETE FROM product_sku WHERE sku_id=?", [int(sku_id)])
                messagebox.showinfo("成功", "删除规格成功", parent=self.win)
                self._load()
            except Exception as e:
                messagebox.showerror("失败", str(e) + "\n（该规格已被单据引用，禁止删除）",
                                     parent=self.win)

    def back(self):
        """返回款列表（第一级）"""
        self.win.destroy()


class SkuFormDialog:
    """SKU 新增/修改表单（模态）。保存或返回后关闭，回 SKU 列表"""

    def __init__(self, parent_window, sku):
        self.parent_window = parent_window   # 第二级 SkuWindow
        self.sku = sku                       # 非 None 表示修改，None 表示新增
        self.top = tk.Toplevel(parent_window.win)
        self.top.title("修改规格" if sku else "新增规格")
        self.top.geometry("380x380")

        # 输入框区
        frm = tk.Frame(self.top)
        frm.pack(pady=16)
        tk.Label(frm, text="颜色").grid(row=0, column=0, padx=6, pady=7)
        self.e_color = tk.Entry(frm, width=18)
        self.e_color.grid(row=0, column=1)
        tk.Label(frm, text="尺码").grid(row=1, column=0, padx=6, pady=7)
        # 只读下拉：只能在数据库允许的 5 个尺码里选，不能自己敲，从源头杜绝填错
        self.e_size = ttk.Combobox(frm, width=16, state="readonly",
                                   values=["S", "M", "L", "XL", "XXL"])
        self.e_size.grid(row=1, column=1)
        tk.Label(frm, text="进价").grid(row=2, column=0, padx=6, pady=7)
        self.e_purchase = tk.Entry(frm, width=18)
        self.e_purchase.grid(row=2, column=1)
        tk.Label(frm, text="售价").grid(row=3, column=0, padx=6, pady=7)
        self.e_sale = tk.Entry(frm, width=18)
        self.e_sale.grid(row=3, column=1)
        tk.Label(frm, text="库存数量").grid(row=4, column=0, padx=6, pady=7)
        self.e_stock = tk.Entry(frm, width=18)
        self.e_stock.grid(row=4, column=1)
        tk.Label(frm, text="安全库存").grid(row=5, column=0, padx=6, pady=7)
        self.e_safe = tk.Entry(frm, width=18)
        self.e_safe.grid(row=5, column=1)

        # 修改时预填；新增时库存与安全库存默认 0
        if sku:
            self.e_color.insert(0, sku["color"])
            self.e_size.set(sku["size"])
            self.e_purchase.insert(0, sku["purchase_price"])
            self.e_sale.insert(0, sku["sale_price"])
            self.e_stock.insert(0, sku["stock_qty"])
            self.e_safe.insert(0, sku["safe_stock"])
        else:
            self.e_stock.insert(0, "0")
            self.e_safe.insert(0, "0")

        # 按钮区
        btn = tk.Frame(self.top)
        btn.pack(pady=8)
        tk.Button(btn, text="保存", width=8, command=self.save).pack(side="left", padx=8)
        tk.Button(btn, text="返回", width=8, command=self.back).pack(side="left", padx=8)

        # 模态：表单打开时锁定 SKU 列表，焦点在表单
        self.top.grab_set()
        self.top.focus_force()

    def save(self):
        """保存：校验输入后，修改走 UPDATE、新增走 INSERT；成功回 SKU 列表并刷新"""
        color = self.e_color.get().strip()
        size = self.e_size.get().strip()
        if not color or not size:
            messagebox.showwarning("提示", "颜色、尺码不能为空", parent=self.top)
            return
        # 价格：必须是数字
        try:
            purchase_price = float(self.e_purchase.get().strip())
            sale_price = float(self.e_sale.get().strip())
        except ValueError:
            messagebox.showwarning("提示", "进价、售价必须是数字", parent=self.top)
            return
        # 库存：必须是整数
        try:
            stock_qty = int(self.e_stock.get().strip())
            safe_stock = int(self.e_safe.get().strip())
        except ValueError:
            messagebox.showwarning("提示", "库存、安全库存必须是整数", parent=self.top)
            return
        # 价格和库存均不允许为负
        if purchase_price < 0 or sale_price < 0 or stock_qty < 0 or safe_stock < 0:
            messagebox.showwarning("提示", "价格和库存不能为负数", parent=self.top)
            return
        # 所属款号由 SKU 列表带入，不让用户手动填，避免填错
        pid = int(self.parent_window.product["product_id"])
        try:
            if self.sku:
                db.execute(
                    "UPDATE product_sku SET color=?, size=?, purchase_price=?, sale_price=?, "
                    "stock_qty=?, safe_stock=? WHERE sku_id=?",
                    [color, size, purchase_price, sale_price, stock_qty, safe_stock,
                     self.sku["sku_id"]])
                messagebox.showinfo("成功", "修改规格成功", parent=self.top)
            else:
                db.execute(
                    "INSERT INTO product_sku(product_id, color, size, purchase_price, "
                    "sale_price, stock_qty, safe_stock) VALUES (?,?,?,?,?,?,?)",
                    [pid, color, size, purchase_price, sale_price, stock_qty, safe_stock])
                messagebox.showinfo("成功", "新增规格成功", parent=self.top)
        except Exception as e:
            messagebox.showerror("失败", str(e), parent=self.top)
            return
        # 关闭表单，回 SKU 列表并刷新
        self.top.grab_release()
        self.top.destroy()
        self.parent_window._load()

    def back(self):
        """只关闭表单、回 SKU 列表，不退出"""
        self.top.grab_release()
        self.top.destroy()
