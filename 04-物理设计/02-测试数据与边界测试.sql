-- ============================================================
-- 服装销售管理系统 —— 测试数据 + 边界测试（检验约束有效性）
-- 先执行 01-建库建表.sql，再执行本文件
-- ============================================================
USE ClothingSalesDB;
GO

-- ============================================================
-- 一、正常测试数据（支撑系统演示）
-- ============================================================

-- 1. 员工（密码为演示占位，正式版存储哈希）
INSERT INTO employee(name, login_name, password, role, phone) VALUES
 ('张伟','admin','e10adc3949ba59abbe56e057f20f883e','管理员','13800000001'),
 ('李娜','buyer','e10adc3949ba59abbe56e057f20f883e','采购员','13800000002'),
 ('王强','seller','e10adc3949ba59abbe56e057f20f883e','销售员','13800000003'),
 ('赵敏','keeper','e10adc3949ba59abbe56e057f20f883e','仓管','13800000004'),
 ('刘洋','seller2','e10adc3949ba59abbe56e057f20f883e','销售员','13800000005');
GO

-- 2. 商品分类（含父子层级）
INSERT INTO category(category_name, parent_id, season) VALUES
 ('上装', NULL, '四季'),
 ('下装', NULL, '四季'),
 ('外套', NULL, '秋冬');
INSERT INTO category(category_name, parent_id, season) VALUES
 ('T恤', 1, '夏季'),
 ('衬衫', 1, '四季'),
 ('牛仔裤', 2, '四季'),
 ('休闲裤', 2, '四季'),
 ('风衣', 3, '秋冬'),
 ('羽绒服', 3, '冬季');
GO

-- 3. 供应商
INSERT INTO supplier(supplier_name, contact, phone, address) VALUES
 ('广州恒源服装厂','陈老板','020-88886666','广州市白云区'),
 ('杭州美尚服饰','周经理','0571-66668888','杭州市余杭区'),
 ('深圳潮流制衣','吴总','0755-33336666','深圳市南山区');
GO

-- 4. 会员
INSERT INTO member(member_name, phone, points, level, reg_date) VALUES
 ('陈晓','13900000001', 120, '银卡', '2025-01-15'),
 ('林芳','13900000002', 0,   '普通', '2025-06-20'),
 ('吴敏','13900000003', 860, '金卡', '2024-12-01');
GO

-- 5. 商品（服装款式）
INSERT INTO product(style_code, product_name, brand, category_id, standard_price, description) VALUES
 ('T001','白色圆领T恤','优衣库', 4, 99.00,  '纯棉基础款'),
 ('J002','蓝色修身牛仔裤','Levi''s', 6, 299.00, '弹力直筒'),
 ('C003','卡其色风衣','太平鸟', 8, 599.00,  '中长款风衣'),
 ('S004','黑色衬衫','海澜之家', 5, 199.00,  '商务免烫');
GO

-- 6. 商品规格 SKU（颜色×尺码）
INSERT INTO product_sku(product_id, color, size, purchase_price, sale_price, stock_qty, safe_stock) VALUES
 (1,'白色','M', 40.00, 99.00,  48, 10),   -- T001 白M（入库50-出库2）
 (1,'白色','L', 40.00, 99.00,  60, 10),   -- T001 白L
 (1,'黑色','M', 40.00, 99.00,  30, 10),   -- T001 黑M
 (2,'蓝色','M', 120.00,299.00, 40, 8),    -- J002 蓝M
 (2,'蓝色','L', 120.00,299.00, 34, 8),    -- J002 蓝L（入库35-出库1）
 (2,'蓝色','XL',120.00,299.00, 20, 8),    -- J002 蓝XL
 (3,'卡其','M', 280.00,599.00, 15, 5),    -- C003 卡其M
 (3,'卡其','L', 280.00,599.00, 12, 5),    -- C003 卡其L
 (4,'黑色','L', 80.00, 199.00, 25, 6),    -- S004 黑L
 (4,'白色','XL',80.00, 199.00, 18, 6);    -- S004 白XL
GO

-- 7. 采购单（已入库）+ 明细 + 库存更新（演示：采购入库）
INSERT INTO purchase_order(supplier_id, employee_id, op_date, total_amount, status) VALUES
 (1, 2, '2025-06-01', 5600.00, '已入库');
INSERT INTO purchase_item(purchase_order_id, sku_id, quantity, unit_price, subtotal) VALUES
 (1, 1, 50, 40.00, 2000.00),
 (1, 2, 60, 40.00, 2400.00),
 (1, 3, 30, 40.00, 1200.00);
-- 入库流水（正式版由触发器自动完成；SKU4-10 为期初库存流水）
INSERT INTO stock_io(sku_id, io_type, quantity, ref_no, employee_id, io_time) VALUES
 (1,'入库',50,'PO0001',2,'2025-06-01'),
 (2,'入库',60,'PO0001',2,'2025-06-01'),
 (3,'入库',30,'PO0001',2,'2025-06-01'),
 (4,'入库',40,'INIT',2,'2025-05-01'),
 (5,'入库',35,'INIT',2,'2025-05-01'),
 (6,'入库',20,'INIT',2,'2025-05-01'),
 (7,'入库',15,'INIT',2,'2025-05-01'),
 (8,'入库',12,'INIT',2,'2025-05-01'),
 (9,'入库',25,'INIT',2,'2025-05-01'),
 (10,'入库',18,'INIT',2,'2025-05-01');
GO

-- 8. 销售单（已出库）+ 明细 + 库存扣减（演示：销售出库）
INSERT INTO sale_order(member_id, employee_id, op_date, total_amount, discount, paid_amount, status) VALUES
 (1, 3, '2025-06-15', 348.00, 0.90, 313.20, '已出库');
INSERT INTO sale_item(sale_order_id, sku_id, quantity, unit_price, subtotal) VALUES
 (1, 1, 2, 99.00, 198.00),
 (1, 5, 1, 150.00, 150.00);   -- 演示：单价可与标准价不同（促销价）
-- 出库流水
INSERT INTO stock_io(sku_id, io_type, quantity, ref_no, employee_id, io_time) VALUES
 (1,'出库',2,'SO0001',3,'2025-06-15'),
 (5,'出库',1,'SO0001',3,'2025-06-15');
GO

PRINT '正常测试数据导入完成。';
GO

-- ============================================================
-- 二、边界测试（检验约束有效性，逐条运行并截图存档）
--    老师要求：测试数据覆盖空值、超长、重复主键、违反外键、违反 CHECK
-- ============================================================

DECLARE @msg NVARCHAR(300);

-- 测试1：违反 NOT NULL（员工姓名不能为空）
BEGIN TRY
    INSERT INTO employee(name, login_name, password, role) VALUES (NULL,'test1','x','管理员');
    PRINT '测试1 失败：空值未被拒绝';
END TRY
BEGIN CATCH
    PRINT '测试1 通过：违反 NOT NULL 被拒绝 -> ' + ERROR_MESSAGE();
END CATCH;
GO

-- 测试2：违反 UNIQUE（登录名重复）
BEGIN TRY
    INSERT INTO employee(name, login_name, password, role) VALUES ('测试','admin','x','采购员');
    PRINT '测试2 失败：重复登录名未被拒绝';
END TRY
BEGIN CATCH
    PRINT '测试2 通过：违反 UNIQUE 被拒绝 -> ' + ERROR_MESSAGE();
END CATCH;
GO

-- 测试3：违反 CHECK（库存量不能为负）
BEGIN TRY
    UPDATE product_sku SET stock_qty = -1 WHERE sku_id = 1;
    PRINT '测试3 失败：负库存未被拒绝';
END TRY
BEGIN CATCH
    PRINT '测试3 通过：违反 CHECK(stock_qty>=0) 被拒绝 -> ' + ERROR_MESSAGE();
END CATCH;
GO

-- 测试4：违反 CHECK（折扣超出 0..1）
BEGIN TRY
    INSERT INTO sale_order(employee_id, discount, status) VALUES (3, 1.50, '草稿');
    PRINT '测试4 失败：非法折扣未被拒绝';
END TRY
BEGIN CATCH
    PRINT '测试4 通过：违反 CHECK(0<=discount<=1) 被拒绝 -> ' + ERROR_MESSAGE();
END CATCH;
GO

-- 测试5：违反外键（引用不存在的分类号）
BEGIN TRY
    INSERT INTO product(style_code, product_name, category_id, standard_price)
    VALUES ('X999','测试商品', 999, 10.00);
    PRINT '测试5 失败：非法外键未被拒绝';
END TRY
BEGIN CATCH
    PRINT '测试5 通过：违反外键约束被拒绝 -> ' + ERROR_MESSAGE();
END CATCH;
GO

-- 测试6：违反主键（重复主键）
BEGIN TRY
    INSERT INTO category(category_id, category_name) VALUES (1, '重复分类');
    PRINT '测试6 失败：重复主键未被拒绝';
END TRY
BEGIN CATCH
    PRINT '测试6 通过：违反主键约束被拒绝 -> ' + ERROR_MESSAGE();
END CATCH;
GO

-- 测试7：违反 CHECK（尺码非法）
BEGIN TRY
    INSERT INTO product_sku(product_id, color, size, purchase_price, sale_price)
    VALUES (1,'红色','XXS', 40.00, 99.00);
    PRINT '测试7 失败：非法尺码未被拒绝';
END TRY
BEGIN CATCH
    PRINT '测试7 通过：违反 CHECK(size) 被拒绝 -> ' + ERROR_MESSAGE();
END CATCH;
GO

-- 测试8：超长字符串（VARCHAR 超长截断报错）
BEGIN TRY
    INSERT INTO supplier(supplier_name) VALUES (REPLICATE('超', 60));
    PRINT '测试8 失败：超长字符串未被拒绝';
END TRY
BEGIN CATCH
    PRINT '测试8 通过：超长字符串被拒绝 -> ' + ERROR_MESSAGE();
END CATCH;
GO

PRINT '边界测试执行完毕（预期 8 条全部"通过"）。';
GO
