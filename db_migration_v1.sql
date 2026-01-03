-- ============================================
-- Database Schema Migration v1.0
-- Exam-Grade MCQ System - Audit & Versioning
-- ============================================

USE mcq_db;

-- Add new audit and versioning columns
ALTER TABLE video_mcqs
ADD COLUMN schema_version VARCHAR(10) DEFAULT '1.0' NOT NULL AFTER generator,
ADD COLUMN generation_mode VARCHAR(20) DEFAULT 'legacy' NOT NULL AFTER schema_version,
ADD COLUMN quality_metrics JSON NULL AFTER generation_mode,
ADD COLUMN created_by VARCHAR(50) NULL AFTER quality_metrics,
ADD COLUMN updated_by VARCHAR(50) NULL AFTER created_by,
ADD COLUMN generation_count INT DEFAULT 1 NOT NULL AFTER updated_by;

-- Update existing records
UPDATE video_mcqs
SET 
    schema_version = '1.0',
    generation_mode = CASE 
        WHEN JSON_EXTRACT(generator, '$.mode') = 'exam-grade' THEN 'exam-grade'
        ELSE 'legacy'
    END,
    created_by = 'system',
    updated_by = 'system',
    generation_count = 1
WHERE schema_version IS NULL OR schema_version = '';

-- Create indexes for performance
CREATE INDEX idx_generation_mode ON video_mcqs(generation_mode);
CREATE INDEX idx_created_at ON video_mcqs(created_at);
CREATE INDEX idx_updated_at ON video_mcqs(updated_at);

-- Verify migration
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN generation_mode = 'exam-grade' THEN 1 END) as exam_grade_count,
    COUNT(CASE WHEN generation_mode = 'legacy' THEN 1 END) as legacy_count,
    MIN(created_at) as oldest_record,
    MAX(updated_at) as latest_update
FROM video_mcqs;

-- Show sample record structure
SELECT 
    video_id,
    generation_mode,
    schema_version,
    generation_count,
    JSON_PRETTY(quality_metrics) as quality_metrics,
    created_at,
    updated_at
FROM video_mcqs
LIMIT 1;


