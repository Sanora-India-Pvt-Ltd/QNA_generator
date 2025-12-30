# MySQL Workbench Quick Start Guide

## 🚀 Quick Setup in 5 Steps

### Step 1: Open MySQL Workbench
- Launch **MySQL Workbench** from Start Menu
- Click on your local connection (usually "Local instance MySQL" or "localhost")
- Enter your **root password** when prompted

### Step 2: Open SQL Script
1. Click **File → Open SQL Script**
2. Navigate to `setup_database_mysql.sql`
3. Click **Open**

### Step 3: Execute Script
1. Click the **Execute** button (⚡ icon) or press `Ctrl+Shift+Enter`
2. Wait for "Success" messages in the Output panel
3. You should see: "Query OK, 0 rows affected"

### Step 4: Verify Table Created
1. In left sidebar, expand **Schemas**
2. Expand **mcq_db**
3. Expand **Tables**
4. You should see **video_mcqs** table ✅

### Step 5: Set Environment Variable

**Windows PowerShell:**
```powershell
$env:DATABASE_URL = "mysql+aiomysql://root:YOUR_PASSWORD@127.0.0.1:3306/mcq_db"
```

**Windows Command Prompt:**
```cmd
setx DATABASE_URL "mysql+aiomysql://root:YOUR_PASSWORD@127.0.0.1:3306/mcq_db"
```
*(Close and reopen terminal after setx)*

---

## 📋 Common MySQL Workbench Operations

### View Table Data
```sql
USE mcq_db;
SELECT * FROM video_mcqs LIMIT 10;
```

### Check Table Structure
```sql
DESCRIBE video_mcqs;
```

### Count Records
```sql
SELECT COUNT(*) FROM video_mcqs;
```

### View All Videos
```sql
SELECT video_id, url, mcq_count, created_at 
FROM video_mcqs 
ORDER BY created_at DESC;
```

### Delete All Records (Testing)
```sql
DELETE FROM video_mcqs;
```

### Drop Table (Start Fresh)
```sql
DROP TABLE IF EXISTS video_mcqs;
-- Then run setup_database_mysql.sql again
```

### Check JSON Data
```sql
SELECT 
    video_id,
    JSON_LENGTH(questions, '$.questions') as question_count,
    created_at
FROM video_mcqs;
```

---

## 🔧 Troubleshooting

### "Access denied for user"
- Check password in `DATABASE_URL`
- Verify user exists: `SELECT user FROM mysql.user;`

### "Unknown database 'mcq_db'"
- Run setup script again
- Or manually: `CREATE DATABASE mcq_db;`

### "Table doesn't exist"
- Run `setup_database_mysql.sql` script
- Check you're using correct database: `USE mcq_db;`

### Can't Connect to MySQL
- Check MySQL service is running
- For XAMPP: Start MySQL from XAMPP Control Panel
- Check port (default: 3306)

---

## 🎯 Next Steps

1. ✅ Database created
2. ✅ Table exists
3. ✅ Environment variable set
4. ✅ Test connection: `python test_db_connection.py`
5. ✅ Start server: `uvicorn api_pg_mcq:app --reload`

---

## 💡 Pro Tips

- **Right-click table** → "Select Rows" to view data
- **Right-click table** → "Table Inspector" to see structure
- Use **Ctrl+Enter** to execute selected SQL
- Use **Ctrl+Shift+Enter** to execute all SQL in editor

