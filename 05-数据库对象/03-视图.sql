-- ============================================================
-- 服装销售管理系统 —— 视图 VIEW（简化查询 + 逻辑数据隔离）
-- 对应文档：03-逻辑设计/关系模式与3NF论证.md 第 6 节外模式
-- ============================================================
USE ClothingSalesDB;
GO

-- 1. 库存查询视图（联表：规格+商品+分类，含预警状态）
CREATE OR ALTER VIEW v_stock AS
SELECT
    s.sku_id,
    p.style_code,
    p.product_name,
    p.brand,
    c.category_name,
    s.color,
    s.size,
    s.sale_price,
    s.stock_qty,
    s.safe_stock,
    CASE WHEN s.stock_qty < s.safe_stock THEN N'预警' ELSE N'正常' END AS stock_status
FROM product_sku s
JOIN product  p ON s.product_id  = p.product_id
JOIN category c ON p.category_id = c.category_id;
GO

-- 2. 低库存预警视图（列出低于安全库存的 SKU，组员3 负责）
CREATE OR ALTER VIEW v_low_stock AS
SELECT * FROM v_stock WHERE stock_qty < safe_stock;
GO

-- 3. 销售明细视图（联表：销售单+明细+规格+商品+会员+员工，组员2 负责）
CREATE OR ALTER VIEW v_sale_detail AS
SELECT
    o.sale_order_id,
    o.op_date,
    o.discount,
    o.paid_amount,
    o.status,
    m.member_name,
    e.name          AS seller,
    i.item_id,
    p.style_code,
    p.product_name,
    s.color,
    s.size,
    i.quantity,
    i.unit_price,
    i.subtotal
FROM sale_order o
LEFT JOIN member     m ON o.member_id     = m.member_id
JOIN        employee   e ON o.employee_id   = e.employee_id
JOIN        sale_item  i ON o.sale_order_id = i.sale_order_id
JOIN        product_sku s ON i.sku_id        = s.sku_id
JOIN        product     p ON s.product_id    = p.product_id;
GO

-- 4. 销售统计视图（按日期+商品聚合，组员4 负责）
CREATE OR ALTER VIEW v_sales_report AS
SELECT
    CAST(o.op_date AS DATE) AS sale_date,
    p.style_code,
    p.product_name,
    SUM(i.quantity)         AS total_qty,
    SUM(i.subtotal)         AS total_amount
FROM sale_order o
JOIN sale_item  i ON o.sale_order_id = i.sale_order_id
JOIN product_sku s ON i.sku_id        = s.sku_id
JOIN product     p ON s.product_id    = p.product_id
WHERE o.status = N'已出库'
GROUP BY CAST(o.op_date AS DATE), p.style_code, p.product_name;
GO

-- 5. 采购明细视图（联表：采购单+明细+规格+商品+供应商，组员1 负责）
CREATE OR ALTER VIEW v_purchase_detail AS
SELECT
    o.purchase_order_id,
    o.op_date,
    o.status,
    sp.supplier_name,
    e.name AS buyer,
    i.item_id,
    p.style_code,
    p.product_name,
    s.color,
    s.size,
    i.quantity,
    i.unit_price,
    i.subtotal
FROM purchase_order o
JOIN supplier      sp ON o.supplier_id       = sp.supplier_id
JOIN employee      e  ON o.employee_id       = e.employee_id
JOIN purchase_item i  ON o.purchase_order_id = i.purchase_order_id
JOIN product_sku   s  ON i.sku_id            = s.sku_id
JOIN product       p  ON s.product_id        = p.product_id;
GO

PRINT '5 个视图创建完成：v_stock / v_low_stock / v_sale_detail / v_sales_report / v_purchase_detail';
GO
