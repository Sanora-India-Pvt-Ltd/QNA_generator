# 🚀 Quick Start - MySQL Setup (5 Minutes)

## Step-by-Step Visual Guide

### ✅ Step 1: Install Python Dependencies

Open **Command Prompt** or **PowerShell** in project folder:

```bash
pip install -r requirements.txt
```

Wait for installation to complete.

---

### ✅ Step 2: Open MySQL Workbench

1. Launch **MySQL Workbench** from Start Menu
2. Click on **Local instance MySQL** (or your connection)
3. Enter your **root password**
4. Click **OK**

You should see the SQL Editor open.

---

### ✅ Step 3: Create Database & Table

**In MySQL Workbench:**

1. Click **File** → **Open SQL Script**
2. Navigate to `setup_database_mysql.sql`
3. Click **Open**
4. Click the **⚡ Execute** button (or press `Ctrl+Shift+Enter`)
5. Wait for "Success" messages

**You should see:**
```
Query OK, 0 rows affected
```

---

### ✅ Step 4: Verify Table Created

**In MySQL Workbench left sidebar:**

1. Click the **refresh icon** (🔄) next to "Schemas"
2. Expand **Schemas**
3. Expand **mcq_db**
4. Expand **Tables**
5. You should see **video_mcqs** ✅

---

### ✅ Step 5: Set Environment Variable

**Windows PowerShell:**
```powershell
$env:DATABASE_URL = "mysql+aiomysql://root:YOUR_PASSWORD@127.0.0.1:3306/mcq_db"
```

**Replace `YOUR_PASSWORD` with your MySQL root password!**

**Windows Command Prompt:**
```cmd
setx DATABASE_URL "mysql+aiomysql://root:YOUR_PASSWORD@127.0.0.1:3306/mcq_db"
```
*(Then close and reopen terminal)*

---

### ✅ Step 6: Test Connection

```bash
python test_db_connection.py
```

**You should see:**
```
✅ Database connection successful!
✅ Table 'video_mcqs' exists!
✅ All checks passed!
```

---

### ✅ Step 7: Start Server

```bash
uvicorn api_pg_mcq:app --reload --host 0.0.0.0 --port 8000
```

**You should see:**
```
🚀 Loading Whisper model...
✅ Whisper ready!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### ✅ Step 8: Test API

Open browser:
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

## 🎉 You're Done!

Your API is now running and ready to:
1. Generate MCQs: `POST /generate-and-save`
2. Fetch MCQs: `GET /videos/{video_id}/mcqs`

---

## ❌ Troubleshooting

### "Access denied"
- Check password in `DATABASE_URL`
- Make sure password matches MySQL root password

### "Unknown database"
- Run `setup_database_mysql.sql` again in MySQL Workbench

### "aiomysql not found"
- Run: `pip install aiomysql`

### "Can't connect"
- Make sure MySQL service is running
- Check XAMPP Control Panel if using XAMPP

---

## 📚 Need More Help?

- **Detailed Guide:** [MYSQL_SETUP_GUIDE.md](MYSQL_SETUP_GUIDE.md)
- **MySQL Workbench Tips:** [MYSQL_WORKBENCH_QUICK_START.md](MYSQL_WORKBENCH_QUICK_START.md)

