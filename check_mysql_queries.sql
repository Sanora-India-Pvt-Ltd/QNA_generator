-- SQL Queries to Verify Data in MySQL
-- Run these in MySQL Workbench to check if your data is saved

-- 1. Check if table exists and count records
USE mcq_db;
SELECT COUNT(*) as total_videos FROM video_mcqs;

-- 2. List all videos with basic info
SELECT 
    video_id,
    LEFT(url, 50) as url_preview,
    mcq_count,
    created_at,
    updated_at
FROM video_mcqs
ORDER BY created_at DESC;

-- 3. Check JSON data structure
SELECT 
    video_id,
    JSON_LENGTH(questions, '$.questions') as question_count,
    JSON_EXTRACT(questions, '$.questions[0].question') as first_question
FROM video_mcqs
LIMIT 5;

-- 4. View full JSON for a specific video (replace 'YOUR_VIDEO_ID' with actual video_id)
-- SELECT 
--     video_id,
--     url,
--     questions,
--     generator
-- FROM video_mcqs
-- WHERE video_id = 'YOUR_VIDEO_ID';

-- 5. Check most recent video
SELECT 
    video_id,
    url,
    mcq_count,
    created_at
FROM video_mcqs
ORDER BY created_at DESC
LIMIT 1;

-- 6. Count questions per video
SELECT 
    video_id,
    mcq_count,
    JSON_LENGTH(questions, '$.questions') as actual_question_count
FROM video_mcqs;

-- 7. Check for videos created today
SELECT 
    video_id,
    url,
    mcq_count,
    created_at
FROM video_mcqs
WHERE DATE(created_at) = CURDATE();

-- 8. View table structure
DESCRIBE video_mcqs;

-- 9. Check indexes
SHOW INDEXES FROM video_mcqs;

