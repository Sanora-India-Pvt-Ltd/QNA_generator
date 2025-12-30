# How to Verify Data is Saved in MySQL

After getting a successful response from `/generate-and-save`, here are **4 ways** to verify the data is actually saved in MySQL:

---

## Method 1: Using API Endpoints (Easiest) ✅

### A. List All Videos
**GET** `http://localhost:8000/videos/list`

Returns all videos saved in the database:
```json
{
  "status": "success",
  "total": 2,
  "videos": [
    {
      "video_id": "abc123def456",
      "url": "https://example.com/video.mp4",
      "mcq_count": 20,
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:30:00"
    }
  ]
}
```

### B. Verify Specific Video
**GET** `http://localhost:8000/videos/{video_id}/verify`

Replace `{video_id}` with the video_id from your response:
```json
{
  "status": "found",
  "video_id": "abc123def456",
  "saved": true,
  "url": "https://example.com/video.mp4",
  "mcq_count": 20,
  "created_at": "2024-01-15T10:30:00"
}
```

### C. Fetch MCQs (Confirms Data is There)
**GET** `http://localhost:8000/videos/{video_id}/mcqs`

If this returns questions, data is definitely saved!

---

## Method 2: Using Python Script 🐍

Run the verification script:

```bash
python verify_mysql_data.py
```

**Output:**
```
============================================================
MySQL Database Verification
============================================================
🔗 Connecting to: 127.0.0.1:3306/mcq_db

✅ Table 'video_mcqs' exists

📊 Total videos saved: 2

============================================================
Recent Videos (Last 10)
============================================================

1. Video ID: abc123def456
   URL: https://example.com/video.mp4
   MCQs: 20
   Created: 2024-01-15 10:30:00
   Updated: 2024-01-15 10:30:00
```

---

## Method 3: Using MySQL Workbench (Visual) 🖥️

### Step 1: Open MySQL Workbench
- Launch MySQL Workbench
- Connect to your database

### Step 2: Run SQL Queries

**Quick Check:**
```sql
USE mcq_db;
SELECT COUNT(*) as total_videos FROM video_mcqs;
```

**List All Videos:**
```sql
SELECT 
    video_id,
    LEFT(url, 50) as url_preview,
    mcq_count,
    created_at
FROM video_mcqs
ORDER BY created_at DESC;
```

**View Full Data:**
```sql
SELECT * FROM video_mcqs;
```

**Check JSON Data:**
```sql
SELECT 
    video_id,
    JSON_LENGTH(questions, '$.questions') as question_count
FROM video_mcqs;
```

**See all queries:** Open `check_mysql_queries.sql` in MySQL Workbench

---

## Method 4: Using Command Line 💻

```bash
mysql -u root -p mcq_db -e "SELECT video_id, url, mcq_count, created_at FROM video_mcqs;"
```

---

## Quick Verification Checklist ✅

After calling `/generate-and-save`:

1. ✅ **Check API Response:**
   - Status should be `"saved"` or `"cached"`
   - `video_id` should be present
   - `count` should show number of MCQs

2. ✅ **Verify in Database:**
   - Call `GET /videos/{video_id}/verify`
   - Or run `python verify_mysql_data.py`
   - Or check in MySQL Workbench

3. ✅ **Test Fetch:**
   - Call `GET /videos/{video_id}/mcqs`
   - Should return questions instantly

---

## Troubleshooting

### "Video not found" Error
- Check if `video_id` is correct
- Verify database connection
- Check if generation actually completed

### "No videos found"
- Make sure you called `/generate-and-save` successfully
- Check database connection string
- Verify table exists: `SHOW TABLES;`

### Data Not Appearing
- Check if transaction was committed (should be automatic)
- Verify MySQL service is running
- Check for errors in FastAPI logs

---

## Example Workflow

```bash
# 1. Generate and save
curl -X POST "http://localhost:8000/generate-and-save" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/video.mp4"}'

# Response: {"status": "saved", "video_id": "abc123", "count": 20}

# 2. Verify it's saved
curl "http://localhost:8000/videos/abc123/verify"

# 3. List all videos
curl "http://localhost:8000/videos/list"

# 4. Fetch MCQs (confirms data is there)
curl "http://localhost:8000/videos/abc123/mcqs"
```

---

## Pro Tips 💡

- **Use `/videos/list`** to see all saved videos at once
- **Use `/videos/{video_id}/verify`** for quick checks
- **Check MySQL Workbench** for visual confirmation
- **Run verification script** for detailed report

All methods confirm the same thing: **Your data is safely stored in MySQL!** 🎉

