-- ============================================================
-- 服装销售管理系统 —— 数据库物理设计：建库建表 + 约束 + 索引
-- DBMS：SQL Server 2022
-- 排序规则：Chinese_PRC_CI_AS（避免中文乱码）
-- 对应文档：03-逻辑设计/关系模式与3NF论证.md（先设计再编码，结构完全一致）
-- ============================================================

-- ---------- 1. 创建数据库 ----------
IF DB_ID('ClothingSalesDB') IS NOT NULL
    DROP DATABASE ClothingSalesDB;
GO

CREATE DATABASE ClothingSalesDB
COLLATE Chinese_PRC_CI_AS;
GO

USE ClothingSalesDB;
GO

-- ============================================================
-- 2. 建表（按依赖顺序：先父表后子表）
-- ============================================================

-- 2.1 员工表（登录账号 + 角色）
CREATE TABLE employee (
    employee_id  INT IDENTITY(1,1) NOT NULL,        -- 员工号 主键
    name         VARCHAR(20)  NOT NULL,             -- 姓名
    login_name   VARCHAR(20)  NOT NULL,             -- 登录名 唯一
    password     VARCHAR(64)  NOT NULL,             -- 密码（存储哈希，非明文）
    role         VARCHAR(10)  NOT NULL,             -- 角色
    phone        VARCHAR(20)  NULL,                 -- 电话
    status       VARCHAR(10)  NOT NULL CONSTRAINT df_employee_status DEFAULT '在职', -- 状态
    CONSTRAINT pk_employee PRIMARY KEY (employee_id),
    CONSTRAINT uq_employee_login UNIQUE (login_name),
    CONSTRAINT ck_employee_role   CHECK (role   IN ('管理员','采购员','销售员','仓管')),
    CONSTRAINT ck_employee_status CHECK (status IN ('在职','停用'))
);
GO

-- 2.2 商品分类表（自引用父子分类）
CREATE TABLE category (
    category_id   INT IDENTITY(1,1) NOT NULL,       -- 分类号 主键
    category_name VARCHAR(30) NOT NULL,             -- 分类名
    parent_id     INT NULL,                         -- 上级分类（自引用外键，可空）
    season        VARCHAR(10) NULL,                 -- 季节
    CONSTRAINT pk_category PRIMARY KEY (category_id),
    CONSTRAINT fk_category_parent FOREIGN KEY (parent_id)
        REFERENCES category(category_id)
        ON DELETE NO ACTION ON UPDATE NO ACTION
);
GO

-- 2.3 供应商表
CREATE TABLE supplier (
    supplier_id   INT IDENTITY(1,1) NOT NULL,       -- 供应商号 主键
    supplier_name VARCHAR(50) NOT NULL,             -- 供应商名称
    contact       VARCHAR(20) NULL,                 -- 联系人
    phone         VARCHAR(20) NULL,                 -- 电话
    address       VARCHAR(100) NULL,                -- 地址
    status        VARCHAR(10) NOT NULL CONSTRAINT df_supplier_status DEFAULT '合作中',
    CONSTRAINT pk_supplier PRIMARY KEY (supplier_id),
    CONSTRAINT ck_supplier_status CHECK (status IN ('合作中','停用'))
);
GO

-- 2.4 会员表
CREATE TABLE member (
    member_id   INT IDENTITY(1,1) NOT NULL,         -- 会员号 主键
    member_name VARCHAR(20) NOT NULL,               -- 会员姓名
    phone       VARCHAR(20) NULL,                   -- 电话
    points      INT NOT NULL CONSTRAINT df_member_points DEFAULT 0,  -- 积分
    level       VARCHAR(10) NOT NULL CONSTRAINT df_member_level DEFAULT '普通', -- 等级
    reg_date    DATE NOT NULL CONSTRAINT df_member_reg DEFAULT CAST(GETDATE() AS DATE), -- 注册日期
    CONSTRAINT pk_member PRIMARY KEY (member_id),
    CONSTRAINT ck_member_points CHECK (points >= 0),
    CONSTRAINT ck_member_level  CHECK (level IN ('普通','银卡','金卡'))
);
GO

-- 2.5 商品表（服装款式）
CREATE TABLE product (
    product_id     INT IDENTITY(1,1) NOT NULL,      -- 商品号 主键
    style_code     VARCHAR(30) NOT NULL,            -- 款号 唯一
    product_name   VARCHAR(50) NOT NULL,            -- 商品名称
    brand          VARCHAR(30) NULL,                -- 品牌
    category_id    INT NOT NULL,                    -- 分类号 外键
    standard_price DECIMAL(10,2) NOT NULL,          -- 标准售价（金额用 DECIMAL，不用 FLOAT）
    description    VARCHAR(200) NULL,               -- 描述
    CONSTRAINT pk_product PRIMARY KEY (product_id),
    CONSTRAINT uq_product_style UNIQUE (style_code),
    CONSTRAINT fk_product_category FOREIGN KEY (category_id)
        REFERENCES category(category_id)
        ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT ck_product_price CHECK (standard_price >= 0)
);
GO

-- 2.6 商品规格表 SKU（颜色×尺码多规格，服装行业特色）
CREATE TABLE product_sku (
    sku_id         INT IDENTITY(1,1) NOT NULL,      -- SKU号 主键
    product_id     INT NOT NULL,                    -- 商品号 外键
    color          VARCHAR(20) NOT NULL,            -- 颜色
    size           VARCHAR(10) NOT NULL,            -- 尺码
    purchase_price DECIMAL(10,2) NOT NULL,          -- 进价
    sale_price     DECIMAL(10,2) NOT NULL,          -- 售价
    stock_qty      INT NOT NULL CONSTRAINT df_sku_stock DEFAULT 0,   -- 库存量
    safe_stock     INT NOT NULL CONSTRAINT df_sku_safe  DEFAULT 0,   -- 安全库存
    CONSTRAINT pk_product_sku PRIMARY KEY (sku_id),
    CONSTRAINT uq_sku_product_color_size UNIQUE (product_id, color, size), -- 同款同色同码唯一
    CONSTRAINT fk_sku_product FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT ck_sku_size        CHECK (size IN ('S','M','L','XL','XXL')),
    CONSTRAINT ck_sku_purchase_price CHECK (purchase_price >= 0),
    CONSTRAINT ck_sku_sale_price     CHECK (sale_price >= 0),
    CONSTRAINT ck_sku_stock      CHECK (stock_qty >= 0),
    CONSTRAINT ck_sku_safe       CHECK (safe_stock >= 0)
);
GO

-- 2.7 采购单表
CREATE TABLE purchase_order (
    purchase_order_id INT IDENTITY(1,1) NOT NULL,   -- 采购单号 主键
    supplier_id       INT NOT NULL,                 -- 供应商号 外键
    employee_id       INT NOT NULL,                 -- 采购员号 外键
    op_date           DATETIME2 NOT NULL CONSTRAINT df_po_date DEFAULT SYSDATETIME(), -- 日期
    total_amount      DECIMAL(12,2) NOT NULL CONSTRAINT df_po_total DEFAULT 0,        -- 总金额
    status            VARCHAR(10) NOT NULL CONSTRAINT df_po_status DEFAULT '草稿',
    CONSTRAINT pk_purchase_order PRIMARY KEY (purchase_order_id),
    CONSTRAINT fk_po_supplier FOREIGN KEY (supplier_id)
        REFERENCES supplier(supplier_id) ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT fk_po_employee FOREIGN KEY (employee_id)
        REFERENCES employee(employee_id) ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT ck_po_total  CHECK (total_amount >= 0),
    CONSTRAINT ck_po_status CHECK (status IN ('草稿','已入库','已取消'))
);
GO

-- 2.8 采购明细表（联系实体）
CREATE TABLE purchase_item (
    item_id           INT IDENTITY(1,1) NOT NULL,   -- 明细号 主键
    purchase_order_id INT NOT NULL,                 -- 采购单号 外键（随主单删除）
    sku_id            INT NOT NULL,                 -- SKU号 外键
    quantity          INT NOT NULL,                 -- 数量
    unit_price        DECIMAL(10,2) NOT NULL,       -- 单价
    subtotal          DECIMAL(12,2) NOT NULL,       -- 小计（可控冗余）
    CONSTRAINT pk_purchase_item PRIMARY KEY (item_id),
    CONSTRAINT uq_pi_order_sku UNIQUE (purchase_order_id, sku_id),
    CONSTRAINT fk_pi_order FOREIGN KEY (purchase_order_id)
        REFERENCES purchase_order(purchase_order_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_pi_sku FOREIGN KEY (sku_id)
        REFERENCES product_sku(sku_id) ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT ck_pi_quantity CHECK (quantity > 0),
    CONSTRAINT ck_pi_unit_price CHECK (unit_price >= 0),
    CONSTRAINT ck_pi_subtotal CHECK (subtotal >= 0)
);
GO

-- 2.9 销售单表
CREATE TABLE sale_order (
    sale_order_id INT IDENTITY(1,1) NOT NULL,       -- 销售单号 主键
    member_id     INT NULL,                         -- 会员号 外键（散客可空）
    employee_id   INT NOT NULL,                     -- 销售员号 外键
    op_date       DATETIME2 NOT NULL CONSTRAINT df_so_date DEFAULT SYSDATETIME(), -- 日期
    total_amount  DECIMAL(12,2) NOT NULL CONSTRAINT df_so_total DEFAULT 0,        -- 总金额
    discount      DECIMAL(4,2) NOT NULL CONSTRAINT df_so_discount DEFAULT 1.00,   -- 折扣 0..1
    paid_amount   DECIMAL(12,2) NOT NULL CONSTRAINT df_so_paid DEFAULT 0,         -- 实收
    status        VARCHAR(10) NOT NULL CONSTRAINT df_so_status DEFAULT '草稿',
    CONSTRAINT pk_sale_order PRIMARY KEY (sale_order_id),
    CONSTRAINT fk_so_member FOREIGN KEY (member_id)
        REFERENCES member(member_id) ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT fk_so_employee FOREIGN KEY (employee_id)
        REFERENCES employee(employee_id) ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT ck_so_total    CHECK (total_amount >= 0),
    CONSTRAINT ck_so_discount CHECK (discount >= 0 AND discount <= 1),
    CONSTRAINT ck_so_paid     CHECK (paid_amount >= 0),
    CONSTRAINT ck_so_status   CHECK (status IN ('草稿','已出库','已取消'))
);
GO

-- 2.10 销售明细表（联系实体）
CREATE TABLE sale_item (
    item_id      INT IDENTITY(1,1) NOT NULL,        -- 明细号 主键
    sale_order_id INT NOT NULL,                     -- 销售单号 外键（随主单删除）
    sku_id       INT NOT NULL,                      -- SKU号 外键
    quantity     INT NOT NULL,                      -- 数量
    unit_price   DECIMAL(10,2) NOT NULL,            -- 单价
    subtotal     DECIMAL(12,2) NOT NULL,            -- 小计（可控冗余）
    CONSTRAINT pk_sale_item PRIMARY KEY (item_id),
    CONSTRAINT uq_si_order_sku UNIQUE (sale_order_id, sku_id),
    CONSTRAINT fk_si_order FOREIGN KEY (sale_order_id)
        REFERENCES sale_order(sale_order_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_si_sku FOREIGN KEY (sku_id)
        REFERENCES product_sku(sku_id) ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT ck_si_quantity CHECK (quantity > 0),
    CONSTRAINT ck_si_unit_price CHECK (unit_price >= 0),
    CONSTRAINT ck_si_subtotal CHECK (subtotal >= 0)
);
GO

-- 2.11 库存流水表（出入库留痕）
CREATE TABLE stock_io (
    io_id      INT IDENTITY(1,1) NOT NULL,          -- 流水号 主键
    sku_id     INT NOT NULL,                        -- SKU号 外键
    io_type    VARCHAR(10) NOT NULL,                -- 类型：入库/出库/盘点调整
    quantity   INT NOT NULL,                        -- 数量
    ref_no     VARCHAR(30) NULL,                    -- 关联单号
    employee_id INT NOT NULL,                       -- 操作人 外键
    io_time    DATETIME2 NOT NULL CONSTRAINT df_io_time DEFAULT SYSDATETIME(), -- 时间
    CONSTRAINT pk_stock_io PRIMARY KEY (io_id),
    CONSTRAINT fk_io_sku FOREIGN KEY (sku_id)
        REFERENCES product_sku(sku_id) ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT fk_io_employee FOREIGN KEY (employee_id)
        REFERENCES employee(employee_id) ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT ck_io_type CHECK (io_type IN ('入库','出库','盘点调整')),
    CONSTRAINT ck_io_quantity CHECK (quantity <> 0)
);
GO

-- ============================================================
-- 3. 索引设计（主键已自带聚簇索引；以下为高频查询建的非聚簇索引）
--    原则：高频查询字段建索引；注意索引会降低写入速度，按需建立
-- ============================================================

-- 按分类查商品
CREATE NONCLUSTERED INDEX ix_product_category ON product(category_id);
GO

-- 按商品查规格（UNIQUE(product_id,color,size) 已覆盖 product_id 前缀，此处补充单列便于提示）
CREATE NONCLUSTERED INDEX ix_sku_product ON product_sku(product_id);
GO

-- 采购单按供应商/采购员/日期查询
CREATE NONCLUSTERED INDEX ix_po_supplier ON purchase_order(supplier_id);
CREATE NONCLUSTERED INDEX ix_po_employee ON purchase_order(employee_id);
CREATE NONCLUSTERED INDEX ix_po_date     ON purchase_order(op_date);
GO

-- 采购明细按单/按规格查询
CREATE NONCLUSTERED INDEX ix_pi_order ON purchase_item(purchase_order_id);
CREATE NONCLUSTERED INDEX ix_pi_sku   ON purchase_item(sku_id);
GO

-- 销售单按会员/销售员/日期查询
CREATE NONCLUSTERED INDEX ix_so_member   ON sale_order(member_id);
CREATE NONCLUSTERED INDEX ix_so_employee ON sale_order(employee_id);
CREATE NONCLUSTERED INDEX ix_so_date     ON sale_order(op_date);
GO

-- 销售明细按单/按规格查询
CREATE NONCLUSTERED INDEX ix_si_order ON sale_item(sale_order_id);
CREATE NONCLUSTERED INDEX ix_si_sku   ON sale_item(sku_id);
GO

-- 库存流水按规格/时间查询
CREATE NONCLUSTERED INDEX ix_io_sku  ON stock_io(sku_id);
CREATE NONCLUSTERED INDEX ix_io_time ON stock_io(io_time);
GO

PRINT '数据库 ClothingSalesDB 及 11 张表、约束、索引创建完成。';
GO
