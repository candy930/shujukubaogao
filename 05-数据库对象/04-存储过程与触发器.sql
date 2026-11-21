-- ============================================================
-- 服装销售管理系统 —— 存储过程 + 触发器 + 事务
-- 重点：参数化查询防注入、事务一致性、审计日志触发器
-- ============================================================
USE ClothingSalesDB;
GO

-- ============================================================
-- 一、审计日志表（触发器写入）
-- ============================================================
-- 幂等写法：表已存在则跳过，保证整个脚本可重复执行
IF OBJECT_ID('dbo.audit_log','U') IS NULL
CREATE TABLE audit_log (
    log_id     INT IDENTITY(1,1) NOT NULL,
    table_name VARCHAR(50) NOT NULL,             -- 被操作的表
    operation  VARCHAR(10) NOT NULL,             -- INSERT/UPDATE/DELETE/库存变动
    record_id  VARCHAR(50) NULL,                 -- 被操作的记录主键
    detail     VARCHAR(200) NULL,                -- 变更详情
    op_time    DATETIME2 NOT NULL CONSTRAINT df_audit_time DEFAULT SYSDATETIME(),
    CONSTRAINT pk_audit_log PRIMARY KEY (log_id)
);
GO

-- ============================================================
-- 二、触发器（审计日志：增删改后触发）
-- ============================================================

-- 2.1 员工表审计触发器
CREATE OR ALTER TRIGGER trg_employee_audit
ON employee
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @op VARCHAR(10);
    IF EXISTS(SELECT 1 FROM inserted) AND EXISTS(SELECT 1 FROM deleted)
        SET @op = 'UPDATE';
    ELSE IF EXISTS(SELECT 1 FROM inserted)
        SET @op = 'INSERT';
    ELSE
        SET @op = 'DELETE';

    INSERT INTO audit_log(table_name, operation, record_id, detail)
    SELECT 'employee', @op,
           CAST(COALESCE(i.employee_id, d.employee_id) AS VARCHAR(20)),
           'name=' + COALESCE(i.name, d.name) + ', role=' + COALESCE(i.role, d.role)
    FROM inserted i
    FULL OUTER JOIN deleted d ON i.employee_id = d.employee_id;
END;
GO

-- 2.2 商品表审计触发器
CREATE OR ALTER TRIGGER trg_product_audit
ON product
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @op VARCHAR(10);
    IF EXISTS(SELECT 1 FROM inserted) AND EXISTS(SELECT 1 FROM deleted)
        SET @op = 'UPDATE';
    ELSE IF EXISTS(SELECT 1 FROM inserted)
        SET @op = 'INSERT';
    ELSE
        SET @op = 'DELETE';

    INSERT INTO audit_log(table_name, operation, record_id, detail)
    SELECT 'product', @op,
           CAST(COALESCE(i.product_id, d.product_id) AS VARCHAR(20)),
           'style=' + COALESCE(i.style_code, d.style_code)
    FROM inserted i
    FULL OUTER JOIN deleted d ON i.product_id = d.product_id;
END;
GO

-- 2.3 库存变动审计触发器（记录库存量变化，体现触发器"隐性执行"风险）
CREATE OR ALTER TRIGGER trg_sku_stock_audit
ON product_sku
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF UPDATE(stock_qty)
    BEGIN
        INSERT INTO audit_log(table_name, operation, record_id, detail)
        SELECT 'product_sku', N'库存变动',
               CAST(i.sku_id AS VARCHAR(20)),
               'stock ' + CAST(d.stock_qty AS VARCHAR) + N' -> ' + CAST(i.stock_qty AS VARCHAR)
        FROM inserted i
        JOIN deleted d ON i.sku_id = d.sku_id
        WHERE i.stock_qty <> d.stock_qty;
    END;
END;
GO

-- ============================================================
-- 三、存储过程（封装业务逻辑，与前端解耦；全部参数化防注入）
-- ============================================================

-- 3.1 登录验证（参数化查询，防 SQL 注入）
CREATE OR ALTER PROCEDURE sp_login
    @login_name VARCHAR(20),
    @password   VARCHAR(64)
AS
BEGIN
    SET NOCOUNT ON;
    -- 参数化查询：登录名作为参数传递，杜绝 ' OR '1'='1 注入
    SELECT employee_id, name, role
    FROM employee
    WHERE login_name = @login_name
      AND password   = @password
      AND status     = N'在职';
END;
GO

-- 3.2 采购入库（事务：更新库存 + 写流水 + 改状态，组员1 负责）
CREATE OR ALTER PROCEDURE sp_purchase_inbound
    @purchase_order_id INT,
    @operator_id       INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        -- 防止重复入库：只有「草稿」状态的采购单才能入库（数据库层最后防线）
        IF EXISTS (SELECT 1 FROM purchase_order
                   WHERE purchase_order_id = @purchase_order_id AND status <> N'草稿')
            RAISERROR(N'该采购单已处理，不能重复入库！', 16, 1);

        BEGIN TRAN;   -- 事务开始

        -- ① 增加对应 SKU 库存
        UPDATE s
        SET s.stock_qty = s.stock_qty + i.quantity
        FROM product_sku s
        JOIN purchase_item i ON s.sku_id = i.sku_id
        WHERE i.purchase_order_id = @purchase_order_id;

        -- ② 写入库流水
        INSERT INTO stock_io(sku_id, io_type, quantity, ref_no, employee_id)
        SELECT i.sku_id, N'入库', i.quantity,
               'PO' + CAST(@purchase_order_id AS VARCHAR), @operator_id
        FROM purchase_item i
        WHERE i.purchase_order_id = @purchase_order_id;

        -- ③ 更新采购单状态
        UPDATE purchase_order
        SET status = N'已入库'
        WHERE purchase_order_id = @purchase_order_id;

        COMMIT TRAN; -- 全部成功才提交
        PRINT N'采购入库完成，库存与流水已更新。';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRAN;  -- 任一失败则回滚
        THROW;
    END CATCH;
END;
GO

-- 3.3 销售出库（事务：校验库存 → 扣库存 → 写流水 → 加积分 → 改状态，组员2 负责）
CREATE OR ALTER PROCEDURE sp_sale_outbound
    @sale_order_id INT,
    @operator_id   INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        -- 防止重复出库：只有「草稿」状态的销售单才能出库
        IF EXISTS (SELECT 1 FROM sale_order
                   WHERE sale_order_id = @sale_order_id AND status <> N'草稿')
            RAISERROR(N'该销售单已处理，不能重复出库！', 16, 1);

        BEGIN TRAN;

        -- ① 校验库存是否充足（不足则中止，防止负库存）
        IF EXISTS (
            SELECT 1
            FROM sale_item i
            JOIN product_sku s ON i.sku_id = s.sku_id
            WHERE i.sale_order_id = @sale_order_id
              AND s.stock_qty < i.quantity
        )
        BEGIN
            RAISERROR(N'库存不足，无法出库！', 16, 1);
        END;

        -- ② 扣减库存
        UPDATE s
        SET s.stock_qty = s.stock_qty - i.quantity
        FROM product_sku s
        JOIN sale_item i ON s.sku_id = i.sku_id
        WHERE i.sale_order_id = @sale_order_id;

        -- ③ 写出库流水
        INSERT INTO stock_io(sku_id, io_type, quantity, ref_no, employee_id)
        SELECT i.sku_id, N'出库', i.quantity,
               'SO' + CAST(@sale_order_id AS VARCHAR), @operator_id
        FROM sale_item i
        WHERE i.sale_order_id = @sale_order_id;

        -- ④ 累加会员积分（每消费 1 元积 1 分）
        UPDATE m
        SET m.points = m.points + CAST(o.paid_amount AS INT)
        FROM member m
        JOIN sale_order o ON m.member_id = o.member_id
        WHERE o.sale_order_id = @sale_order_id
          AND o.member_id IS NOT NULL;

        -- ⑤ 更新销售单状态
        UPDATE sale_order
        SET status = N'已出库'
        WHERE sale_order_id = @sale_order_id;

        COMMIT TRAN;
        PRINT N'销售出库完成，库存/流水/积分已更新。';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRAN;
        THROW;
    END CATCH;
END;
GO

-- 3.4 库存盘点调整（事务：按实盘数调整并写盘点流水，组员3 负责）
CREATE OR ALTER PROCEDURE sp_stock_adjust
    @sku_id      INT,
    @actual_qty  INT,
    @operator_id INT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @current INT, @diff INT;
    SELECT @current = stock_qty FROM product_sku WHERE sku_id = @sku_id;
    SET @diff = @actual_qty - @current;

    BEGIN TRY
        BEGIN TRAN;
        UPDATE product_sku SET stock_qty = @actual_qty WHERE sku_id = @sku_id;
        IF @diff <> 0
            INSERT INTO stock_io(sku_id, io_type, quantity, ref_no, employee_id)
            VALUES(@sku_id, N'盘点调整', @diff, N'CHECK', @operator_id);
        COMMIT TRAN;
        PRINT N'盘点调整完成，差异 ' + CAST(@diff AS VARCHAR) + N' 已记录。';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRAN;
        THROW;
    END CATCH;
END;
GO

-- ============================================================
-- 四、事务与隔离级别说明（答辩要点）
-- ============================================================
-- 1. 采购入库、销售出库均为多步写操作，用 BEGIN TRAN/COMMIT/ROLLBACK
--    保证原子性：要么全部成功，要么全部回滚。
-- 2. 隔离级别：默认 READ COMMITTED，可避免脏读（不读未提交数据）。
--    本系统在出库事务中先读库存再扣减，配合 WHERE 条件与事务，
--    避免"丢失修改"（两个出库并发扣同一 SKU 时串行化保护）。
-- 3. 脏读/不可重复读/丢失修改：
--      脏读        = 读到别的事务未提交的数据（READ UNCOMMITTED 才发生）
--      不可重复读  = 同一事务内两次读同一数据结果不同
--      丢失修改    = 两个事务并发修改同一数据，后提交的覆盖先提交的
--    如需更强隔离，可在事务内 SET TRANSACTION ISOLATION LEVEL SERIALIZABLE。
GO

PRINT '存储过程(4)与触发器(3)及审计日志表创建完成。';
GO
