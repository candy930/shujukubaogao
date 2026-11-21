-- ============================================================
-- 服装销售管理系统 —— 安全性设计：登录名 / 数据库用户 / 角色 / 权限
-- 原则：最小权限（每个角色只授予完成本职所需的最小权限）
-- ============================================================

-- ---------- 1. 创建登录名（SQL Server 认证）----------
USE master;
GO

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'sales_login')
    CREATE LOGIN sales_login WITH PASSWORD = 'Sales@123', DEFAULT_DATABASE = ClothingSalesDB;
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'purchase_login')
    CREATE LOGIN purchase_login WITH PASSWORD = 'Purchase@123', DEFAULT_DATABASE = ClothingSalesDB;
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'admin_login')
    CREATE LOGIN admin_login WITH PASSWORD = 'Admin@123', DEFAULT_DATABASE = ClothingSalesDB;
GO

-- ---------- 2. 创建数据库用户（登录名与用户分离）----------
USE ClothingSalesDB;
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'sales_user')
    CREATE USER sales_user FOR LOGIN sales_login;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'purchase_user')
    CREATE USER purchase_user FOR LOGIN purchase_login;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'admin_user')
    CREATE USER admin_user FOR LOGIN admin_login;
GO

-- ---------- 3. 创建数据库角色 ----------
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'role_sales' AND type = 'R')
    CREATE ROLE role_sales;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'role_purchase' AND type = 'R')
    CREATE ROLE role_purchase;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'role_admin' AND type = 'R')
    CREATE ROLE role_admin;
GO

-- ---------- 4. 用户加入角色 ----------
ALTER ROLE role_sales    ADD MEMBER sales_user;
ALTER ROLE role_purchase ADD MEMBER purchase_user;
ALTER ROLE role_admin    ADD MEMBER admin_user;
GO

-- ---------- 5. 最小权限分配（GRANT）----------

-- 5.1 销售角色：仅销售相关表的增改查 + 出库存储过程（不能删、不能动采购）
GRANT SELECT, INSERT, UPDATE ON sale_order TO role_sales;
GRANT SELECT, INSERT, UPDATE ON sale_item  TO role_sales;
GRANT SELECT, UPDATE          ON product_sku TO role_sales;  -- 只改库存，不动价格
GRANT SELECT                  ON product     TO role_sales;
GRANT SELECT                  ON member      TO role_sales;
GRANT SELECT                  ON v_sale_detail TO role_sales;
GRANT EXECUTE ON sp_sale_outbound TO role_sales;

-- 5.2 采购角色：仅采购相关表的增改查 + 入库存储过程
GRANT SELECT, INSERT, UPDATE ON purchase_order TO role_purchase;
GRANT SELECT, INSERT, UPDATE ON purchase_item  TO role_purchase;
GRANT SELECT, UPDATE          ON product_sku   TO role_purchase;
GRANT SELECT                  ON supplier      TO role_purchase;
GRANT SELECT                  ON v_purchase_detail TO role_purchase;
GRANT EXECUTE ON sp_purchase_inbound TO role_purchase;

-- 5.3 管理员角色：全局控制（含备份）
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::dbo TO role_admin;
GRANT EXECUTE ON sp_stock_adjust TO role_admin;
GO

-- ---------- 6. 撤销与拒绝（REVOKE / DENY 演示）----------

-- 撤销销售角色对销售单的删除权（回收刚才未授予的删除，保持最小权限）
REVOKE DELETE ON sale_order FROM role_sales;

-- 拒绝：即使将来被其他途径授予，也禁止销售角色修改销售单号（DENY 优先于 GRANT）
DENY UPDATE ON sale_order(sale_order_id) TO role_sales;

-- 拒绝采购角色直接删除采购单（必须走取消流程，而非物理删除）
DENY DELETE ON purchase_order TO role_purchase;
GO

-- ---------- 7. 查询验证（答辩演示用）----------
-- 查看数据库用户
SELECT name, type_desc FROM sys.database_principals WHERE type IN ('S','R');
-- 查看角色成员
SELECT r.name AS role_name, m.name AS member_name
FROM sys.database_role_members rm
JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id
JOIN sys.database_principals m ON rm.member_principal_id = m.principal_id;
GO

PRINT '登录名(3)、用户(3)、角色(3)及最小权限分配完成。';
GO
