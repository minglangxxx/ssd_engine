-- Migration: add raw_output column to tasks table
-- Date: 2026-06-16
-- Description: Separate FIO raw JSON output from task.result JSON column
--   into an independent TEXT column to avoid API response bloat.

-- Step 1: Add the new column
ALTER TABLE tasks ADD COLUMN raw_output TEXT NULL;

-- Step 2: Migrate existing data — extract raw_json from result JSON
-- MySQL 5.7+: JSON_EXTRACT returns quoted JSON string, need JSON_UNQUOTE
UPDATE tasks
SET raw_output = JSON_UNQUOTE(JSON_EXTRACT(result, '$.raw_json')),
    result = JSON_REMOVE(result, '$.raw_json')
WHERE result IS NOT NULL
  AND JSON_CONTAINS_PATH(result, 'one', '$.raw_json');
