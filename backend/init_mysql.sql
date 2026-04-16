CREATE DATABASE IF NOT EXISTS ssd_engine
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'ssd_engine'@'%' IDENTIFIED BY '123456';
GRANT ALL PRIVILEGES ON ssd_engine.* TO 'ssd_engine'@'%';
FLUSH PRIVILEGES;

USE ssd_engine;

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;
DROP PROCEDURE IF EXISTS add_fk_if_missing;

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
CALL add_column_if_missing('data_records', 'metadata', 'JSON NULL');
CALL add_column_if_missing('data_records', 'query_scope', 'VARCHAR(64) NULL');
CALL add_index_if_missing('data_records', 'idx_data_records_disk_name', '(disk_name)');
CALL add_index_if_missing('data_records', 'idx_data_records_window_start', '(window_start)');
CALL add_index_if_missing('data_records', 'idx_data_records_window_end', '(window_end)');
CALL add_index_if_missing('data_records', 'idx_data_records_query_scope', '(query_scope)');

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;
DROP PROCEDURE IF EXISTS add_fk_if_missing;
