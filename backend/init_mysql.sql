CREATE DATABASE IF NOT EXISTS ssd_engine
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'ssd_engine'@'%' IDENTIFIED BY '123456';
GRANT ALL PRIVILEGES ON ssd_engine.* TO 'ssd_engine'@'%';
FLUSH PRIVILEGES;

USE ssd_engine;

SET time_zone = '+08:00';

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;
DROP PROCEDURE IF EXISTS add_fk_if_missing;

-- V2.5: nvme_tests 表
CREATE TABLE IF NOT EXISTS `nvme_tests` (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id INT NOT NULL,
    disk_name VARCHAR(64) NOT NULL,
    test_type VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    result JSON NULL,
    verdict VARCHAR(16) NULL DEFAULT NULL,
    error TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_nvme_test_device (device_id, disk_name),
    INDEX idx_nvme_test_type (test_type),
    CONSTRAINT fk_nvme_tests_device FOREIGN KEY (device_id) REFERENCES devices(id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- V2.5: nvme_smart_data 新增字段（过程定义后调用）
-- CALL add_column_if_missing 已移至 DELIMITER ; 之后

DELIMITER $$

CREATE PROCEDURE add_column_if_missing(
  IN p_table_name VARCHAR(64),
  IN p_column_name VARCHAR(64),
  IN p_definition TEXT
)
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = DATABASE()
      AND table_name = p_table_name
  ) AND NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = p_table_name
      AND column_name = p_column_name
  ) THEN
    SET @sql = CONCAT('ALTER TABLE `', p_table_name, '` ADD COLUMN `', p_column_name, '` ', p_definition);
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END $$

CREATE PROCEDURE add_index_if_missing(
  IN p_table_name VARCHAR(64),
  IN p_index_name VARCHAR(64),
  IN p_index_definition TEXT
)
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = DATABASE()
      AND table_name = p_table_name
  ) AND NOT EXISTS (
    SELECT 1
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = p_table_name
      AND index_name = p_index_name
  ) THEN
    SET @sql = CONCAT('ALTER TABLE `', p_table_name, '` ADD INDEX `', p_index_name, '` ', p_index_definition);
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END $$

CREATE PROCEDURE add_fk_if_missing(
  IN p_table_name VARCHAR(64),
  IN p_constraint_name VARCHAR(64),
  IN p_fk_definition TEXT
)
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = DATABASE()
      AND table_name = p_table_name
  ) AND NOT EXISTS (
    SELECT 1
    FROM information_schema.table_constraints
    WHERE table_schema = DATABASE()
      AND table_name = p_table_name
      AND constraint_name = p_constraint_name
      AND constraint_type = 'FOREIGN KEY'
  ) THEN
    SET @sql = CONCAT('ALTER TABLE `', p_table_name, '` ADD CONSTRAINT `', p_constraint_name, '` ', p_fk_definition);
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END $$

DELIMITER ;

-- V2.5: nvme_smart_data 新增字段
CALL add_column_if_missing('nvme_smart_data', 'num_err_log_entries', 'BIGINT NOT NULL DEFAULT 0');
CALL add_column_if_missing('nvme_smart_data', 'unsafe_shutdowns', 'BIGINT NOT NULL DEFAULT 0');

CALL add_column_if_missing('tasks', 'started_at', 'DATETIME NULL');
CALL add_column_if_missing('tasks', 'finished_at', 'DATETIME NULL');
CALL add_column_if_missing('tasks', 'data_window_start', 'DATETIME NULL');
CALL add_column_if_missing('tasks', 'data_window_end', 'DATETIME NULL');
CALL add_column_if_missing('tasks', 'retention_policy', 'JSON NULL');
CALL add_column_if_missing('tasks', 'last_analysis_at', 'DATETIME NULL');
CALL add_index_if_missing('tasks', 'idx_tasks_started_at', '(started_at)');
CALL add_index_if_missing('tasks', 'idx_tasks_finished_at', '(finished_at)');

CALL add_column_if_missing('fio_trend_data', 'device_ip', 'VARCHAR(50) NOT NULL DEFAULT ''''');
CALL add_column_if_missing('fio_trend_data', 'device_path', 'VARCHAR(255) NOT NULL DEFAULT ''''');
CALL add_column_if_missing('fio_trend_data', 'sample_interval_ms', 'INT NOT NULL DEFAULT 1000');
CALL add_column_if_missing('fio_trend_data', 'source', 'VARCHAR(32) NOT NULL DEFAULT ''agent_fio''');
CALL add_column_if_missing('fio_trend_data', 'created_at', 'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP');
CALL add_index_if_missing('fio_trend_data', 'idx_fio_trend_task_time', '(task_id, timestamp)');
CALL add_index_if_missing('fio_trend_data', 'idx_fio_trend_device_time', '(device_ip, timestamp)');

SET @has_tasks_table = (
  SELECT COUNT(*)
  FROM information_schema.tables
  WHERE table_schema = DATABASE()
    AND table_name = 'tasks'
);

SET @create_disk_monitor_samples_sql = IF(
  @has_tasks_table > 0,
  'CREATE TABLE IF NOT EXISTS `disk_monitor_samples` (id BIGINT PRIMARY KEY AUTO_INCREMENT, device_ip VARCHAR(50) NOT NULL, disk_name VARCHAR(64) NOT NULL, event_time DATETIME(3) NOT NULL, task_id INT NULL, sample_interval_ms INT NOT NULL DEFAULT 1000, disk_iops_read DOUBLE NOT NULL DEFAULT 0, disk_iops_write DOUBLE NOT NULL DEFAULT 0, disk_bw_read_bytes_per_sec DOUBLE NOT NULL DEFAULT 0, disk_bw_write_bytes_per_sec DOUBLE NOT NULL DEFAULT 0, disk_latency_read_ms DOUBLE NOT NULL DEFAULT 0, disk_latency_write_ms DOUBLE NOT NULL DEFAULT 0, disk_queue_depth DOUBLE NOT NULL DEFAULT 0, disk_await_ms DOUBLE NOT NULL DEFAULT 0, disk_svctm_ms DOUBLE NOT NULL DEFAULT 0, disk_util_percent DOUBLE NOT NULL DEFAULT 0, disk_rrqm_per_sec DOUBLE NOT NULL DEFAULT 0, disk_wrqm_per_sec DOUBLE NOT NULL DEFAULT 0, source VARCHAR(32) NOT NULL DEFAULT ''agent_disk'', created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, INDEX idx_disk_time (device_ip, disk_name, event_time), INDEX idx_task_time (task_id, event_time), INDEX idx_event_time (event_time), CONSTRAINT fk_disk_monitor_samples_task FOREIGN KEY (task_id) REFERENCES tasks(id))',
  'SELECT ''skip disk_monitor_samples because tasks table is missing'''
);
PREPARE stmt FROM @create_disk_monitor_samples_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CALL add_column_if_missing('ai_analyses', 'data_window_start', 'DATETIME NULL');
CALL add_column_if_missing('ai_analyses', 'data_window_end', 'DATETIME NULL');
CALL add_column_if_missing('ai_analyses', 'input_manifest', 'JSON NULL');
CALL add_column_if_missing('ai_analyses', 'source_snapshot_version', 'VARCHAR(64) NULL');

CALL add_column_if_missing('data_records', 'disk_name', 'VARCHAR(64) NULL');
CALL add_column_if_missing('data_records', 'window_start', 'DATETIME NULL');
CALL add_column_if_missing('data_records', 'window_end', 'DATETIME NULL');
CALL add_column_if_missing('data_records', 'record_count', 'BIGINT NOT NULL DEFAULT 0');
CALL add_column_if_missing('data_records', 'storage_backend', 'VARCHAR(32) NOT NULL DEFAULT ''mysql''');
CALL add_column_if_missing('data_records', 'storage_format', 'VARCHAR(32) NOT NULL DEFAULT ''table''');
CALL add_column_if_missing('data_records', 'manifest_path', 'VARCHAR(500) NULL');
CALL add_column_if_missing('data_records', 'hot_table_name', 'VARCHAR(128) NULL');
CALL add_column_if_missing('data_records', 'checksum', 'VARCHAR(128) NULL');
CALL add_column_if_missing('data_records', 'extra_metadata', 'JSON NULL');
CALL add_column_if_missing('data_records', 'query_scope', 'VARCHAR(64) NULL');
CALL add_column_if_missing('data_records', 'version', 'INT NOT NULL DEFAULT 1');
CALL add_column_if_missing('data_records', 'updated_at', 'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP');
CALL add_index_if_missing('data_records', 'idx_data_records_disk_name', '(disk_name)');
CALL add_index_if_missing('data_records', 'idx_data_records_window_start', '(window_start)');
CALL add_index_if_missing('data_records', 'idx_data_records_window_end', '(window_end)');
CALL add_index_if_missing('data_records', 'idx_data_records_query_scope', '(query_scope)');
-- 新增缺失的关键索引
CALL add_index_if_missing('data_records', 'idx_data_records_status', '(status)');
CALL add_index_if_missing('data_records', 'idx_data_records_device_ip', '(device_ip)');
CALL add_index_if_missing('data_records', 'idx_data_records_data_type', '(data_type)');
CALL add_index_if_missing('data_records', 'idx_data_records_created_at', '(created_at DESC)');
CALL add_index_if_missing('data_records', 'idx_data_records_version', '(id, version)');
CALL add_index_if_missing('ai_analyses', 'idx_ai_analyses_task_created', '(task_id, created_at DESC)');
CALL add_index_if_missing('disk_monitor_samples', 'idx_disk_monitor_device_ip', '(device_ip)');

-- nvme_smart_data 表
CREATE TABLE IF NOT EXISTS `nvme_smart_data` (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_ip VARCHAR(50) NOT NULL,
    disk_name VARCHAR(64) NOT NULL,
    event_time DATETIME(3) NOT NULL,
    temperature SMALLINT NOT NULL DEFAULT 0,
    percentage_used SMALLINT NOT NULL DEFAULT 0,
    power_on_hours BIGINT NOT NULL DEFAULT 0,
    power_cycles BIGINT NOT NULL DEFAULT 0,
    media_errors BIGINT NOT NULL DEFAULT 0,
    critical_warning SMALLINT NOT NULL DEFAULT 0,
    data_units_read BIGINT NOT NULL DEFAULT 0,
    data_units_written BIGINT NOT NULL DEFAULT 0,
    available_spare SMALLINT NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'agent_smart',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_smart_device_disk_time (device_ip, disk_name, event_time),
    INDEX idx_smart_event_time (event_time),
    INDEX idx_smart_device_ip (device_ip)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- V1: devices 表新增主机信息字段
CALL add_column_if_missing('devices', 'hostname', 'VARCHAR(64) NULL');
CALL add_column_if_missing('devices', 'os_version', 'VARCHAR(128) NULL');
CALL add_column_if_missing('devices', 'kernel_version', 'VARCHAR(128) NULL');
CALL add_column_if_missing('devices', 'cpu_usage', 'FLOAT NULL');
CALL add_column_if_missing('devices', 'memory_usage', 'FLOAT NULL');

-- V2: baselines 表
CREATE TABLE IF NOT EXISTS `baselines` (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(128) NOT NULL,
    device_model VARCHAR(128) NULL,
    firmware VARCHAR(64) NULL,
    fio_config JSON NOT NULL,
    result JSON NOT NULL,
    source_task_id INT NOT NULL,
    device_ip VARCHAR(50) NOT NULL,
    device_path VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(64) NOT NULL DEFAULT 'system',
    INDEX idx_baselines_device_ip (device_ip),
    INDEX idx_baselines_source_task_id (source_task_id),
    CONSTRAINT fk_baselines_source_task FOREIGN KEY (source_task_id) REFERENCES tasks(id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- V2: regression_results 表
CREATE TABLE IF NOT EXISTS `regression_results` (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_id INT NOT NULL,
    baseline_id INT NOT NULL,
    iops_diff FLOAT NULL,
    bw_diff FLOAT NULL,
    lat_mean_diff FLOAT NULL,
    lat_p99_diff FLOAT NULL,
    verdict VARCHAR(10) NOT NULL,
    detail JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_regression_task_id (task_id),
    INDEX idx_regression_baseline_id (baseline_id),
    INDEX idx_regression_verdict (verdict),
    CONSTRAINT fk_regression_task FOREIGN KEY (task_id) REFERENCES tasks(id),
    CONSTRAINT fk_regression_baseline FOREIGN KEY (baseline_id) REFERENCES baselines(id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- V2: group_tasks 表
CREATE TABLE IF NOT EXISTS `group_tasks` (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(128) NOT NULL,
    fio_config JSON NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    summary JSON NULL,
    total_count INT NOT NULL DEFAULT 0,
    done_count INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_group_tasks_status (status)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- V2: snia_tasks 表
CREATE TABLE IF NOT EXISTS `snia_tasks` (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(128) NOT NULL,
    device_id INT NOT NULL,
    device_ip VARCHAR(50) NOT NULL,
    device_path VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    current_phase VARCHAR(20) NULL,
    current_round INT NOT NULL DEFAULT 0,
    total_rounds INT NOT NULL DEFAULT 25,
    iops_history TEXT NULL,
    is_steady BOOLEAN NOT NULL DEFAULT FALSE,
    config JSON NOT NULL,
    result JSON NULL,
    error TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_snia_tasks_device_id (device_id),
    INDEX idx_snia_tasks_status (status),
    CONSTRAINT fk_snia_tasks_device FOREIGN KEY (device_id) REFERENCES devices(id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- V2: fw_upgrade_tests 表
CREATE TABLE IF NOT EXISTS `fw_upgrade_tests` (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(128) NOT NULL,
    device_id INT NOT NULL,
    device_ip VARCHAR(50) NOT NULL,
    device_path VARCHAR(255) NOT NULL,
    fw_before VARCHAR(64) NULL,
    fw_after VARCHAR(64) NULL,
    fio_config JSON NOT NULL,
    result_before JSON NULL,
    task_before_id INT NULL,
    result_after JSON NULL,
    task_after_id INT NULL,
    regression_id INT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_fw_tests_device_id (device_id),
    INDEX idx_fw_tests_status (status),
    INDEX idx_fw_tests_device_ip (device_ip),
    CONSTRAINT fk_fw_tests_device FOREIGN KEY (device_id) REFERENCES devices(id),
    CONSTRAINT fk_fw_tests_regression FOREIGN KEY (regression_id) REFERENCES regression_results(id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- V2: tasks 表扩展 group_task 字段
CALL add_column_if_missing('tasks', 'group_task_id', 'INT NULL');
CALL add_column_if_missing('tasks', 'is_sub_task', 'BOOLEAN DEFAULT FALSE');
CALL add_index_if_missing('tasks', 'idx_tasks_group_task_id', '(group_task_id)');

-- m10: 补全 tasks.group_task_id 的 FK 约束
CALL add_fk_if_missing('tasks', 'fk_tasks_group_task_id',
  'FOREIGN KEY (group_task_id) REFERENCES group_tasks(id) ON DELETE SET NULL');

-- M15: data_records 列名 metadata → extra_metadata（MySQL 保留字修正）
SET @col_meta = (SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'data_records' AND column_name = 'metadata');
SET @sql_meta = IF(@col_meta > 0,
    'ALTER TABLE data_records CHANGE COLUMN `metadata` `extra_metadata` JSON NULL',
    'SELECT 1');
PREPARE stmt FROM @sql_meta;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;
DROP PROCEDURE IF EXISTS add_fk_if_missing;
