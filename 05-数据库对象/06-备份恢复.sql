-- ============================================================
-- 服装销售管理系统 —— 备份与恢复（完整 + 差异 + 日志）
-- 必须完成「备份 → 模拟故障 → 恢复」演练并截图存档
-- 说明：请将备份路径改为本机实际可写目录（如 D:\SQLBackup）
-- ============================================================

-- ---------- 0. 准备工作：创建备份目录（在 Windows 中手动创建或执行下面命令）----------
-- 用 xp_cmdshell 需要先启用（默认关闭）。建议手动新建 D:\SQLBackup 目录即可。
-- EXEC sp_configure 'xp_cmdshell', 1; RECONFIGURE;
-- EXEC xp_cmdshell 'mkdir D:\SQLBackup';
GO

USE master;
GO

-- 先确保为完整恢复模式，否则日志备份（BACKUP LOG）会被拒绝
ALTER DATABASE ClothingSalesDB SET RECOVERY FULL;
GO

-- ============================================================
-- 一、备份策略（推荐组合：完整 + 差异 + 日志）
-- ============================================================

-- 1. 完整备份（全库基线，可独立还原）
BACKUP DATABASE ClothingSalesDB
TO DISK = N'D:\SQLBackup\ClothingSalesDB_Full.bak'
WITH INIT, NAME = N'完整备份-基线', STATS = 10;
GO

-- （模拟一段时间业务后）2. 差异备份（基于最近一次完整备份的增量）
BACKUP DATABASE ClothingSalesDB
TO DISK = N'D:\SQLBackup\ClothingSalesDB_Diff.bak'
WITH INIT, DIFFERENTIAL, NAME = N'差异备份', STATS = 10;
GO

-- 3. 日志备份（支持恢复到任意时间点）
BACKUP LOG ClothingSalesDB
TO DISK = N'D:\SQLBackup\ClothingSalesDB_Log.bak'
WITH INIT, NAME = N'日志备份', STATS = 10;
GO

PRINT '完整/差异/日志备份完成，请截图存档。';
GO

-- ============================================================
-- 二、恢复演练（模拟故障 → 恢复 → 核对）
-- 步骤 1：模拟故障（删除关键数据，制造数据丢失）
-- 步骤 2：按顺序还原 完整 → 差异 → 日志
-- 步骤 3：核对记录数，验证恢复到故障前状态
-- ============================================================

-- 【步骤 1】模拟故障：记录当前行数后，删除销售明细（故意破坏）
USE ClothingSalesDB;
SELECT COUNT(*) AS 故障前销售明细数 FROM sale_item;   -- 记录该数字
DELETE FROM sale_item;                              -- 模拟故障：删除销售明细
GO

-- 【步骤 2】还原数据库（必须断开其他连接后执行，先切到 master 并设为单用户）
USE master;
GO
ALTER DATABASE ClothingSalesDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
GO

-- 2.1 还原完整备份（NORECOVERY：保持"正在还原"状态，等待后续备份）
RESTORE DATABASE ClothingSalesDB
FROM DISK = N'D:\SQLBackup\ClothingSalesDB_Full.bak'
WITH NORECOVERY, REPLACE;
GO

-- 2.2 还原差异备份（仍 NORECOVERY）
RESTORE DATABASE ClothingSalesDB
FROM DISK = N'D:\SQLBackup\ClothingSalesDB_Diff.bak'
WITH NORECOVERY;
GO

-- 2.3 还原日志备份（RECOVERY：完成恢复，数据库上线）
RESTORE LOG ClothingSalesDB
FROM DISK = N'D:\SQLBackup\ClothingSalesDB_Log.bak'
WITH RECOVERY;
GO

-- 恢复为多用户模式
ALTER DATABASE ClothingSalesDB SET MULTI_USER;
GO

-- 【步骤 3】核对：行数应与"故障前销售明细数"一致
USE ClothingSalesDB;
SELECT COUNT(*) AS 恢复后销售明细数 FROM sale_item;   -- 与故障前对比，截图存档
GO

PRINT '恢复演练完成，请截图「故障前/恢复后行数对比」存档。';
GO
