# MySQL Setup Guide for Video MCQ Generator

Complete step-by-step guide to set up MySQL/MariaDB for the FastAPI MCQ Generator.

## Prerequisites

- MySQL 5.7+ or MariaDB 10.2+ (for JSON support)
- MySQL Workbench installed (or mysql command line)
- Python 3.8+
- FFmpeg installed
- Ollama installed

---

## Step 1: Install MySQL/MariaDB

### Option A: MySQL (Windows)

1. Download MySQL Installer from: https://dev.mysql.com/downloads/installer/
2. Run the installer
3. Choose "Developer Default" or "Server only"
4. Set root password (remember it!)
5. Complete installation

### Option B: MariaDB (Windows)

1. Download from: https://mariadb.org/download/
2. Run installer
3. Set root password
4. Complete installation

### Option C: XAMPP (Easiest - includes MySQL + phpMyAdmin)

1. Download XAMPP: https://www.apachefriends.org/
2. Install and start MySQL from XAMPP Control Panel
3. Root password is usually empty (blank) by default

---

## Step 2: Open MySQL Workbench

1. Launch **MySQL Workbench**
2. Click on your local connection (usually "Local instance MySQL" or "localhost")
3. Enter your root password when prompted
4. You should see the connection established

---

## Step 3: Create Database and Table

### Method 1: Using MySQL Workbench (GUI)

1. In MySQL Workbench, click **File → Open SQL Script**
2. Navigate to `setup_database_mysql.sql` file
3. Click **Execute** (or press `Ctrl+Shift+Enter`)
4. You should see "Success" messages

### Method 2: Using SQL Editor in Workbench

1. In MySQL Workbench, click the **SQL Editor** tab
2. Copy and paste the following SQL:

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS mcq_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE mcq_db;

-- Create table
CREATE TABLE IF NOT EXISTS video_mcqs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  video_id VARCHAR(32) UNIQUE NOT NULL,
  url TEXT NOT NULL,
  mcq_count INT NOT NULL DEFAULT 20,
  questions JSON NOT NULL,
  generator JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_video_mcqs_url ON video_mcqs(url(255));
CREATE INDEX IF NOT EXISTS idx_video_mcqs_video_id ON video_mcqs(video_id);
```

3. Click **Execute** (or press `Ctrl+Shift+Enter`)

### Method 3: Using Command Line

Open Command Prompt or PowerShell and run:

```bash
mysql -u root -p < setup_database_mysql.sql
```

Enter your root password when prompted.

---

## Step 4: Verify Table Creation

In MySQL Workbench:

1. In the left sidebar, expand **Schemas**
2. Expand **mcq_db**
3. Expand **Tables**
4. You should see **video_mcqs** table
5. Right-click on **video_mcqs** → **Select Rows - Limit 1000** to view structure

Or run this SQL:

```sql
USE mcq_db;
SHOW TABLES;
DESCRIBE video_mcqs;
```

---

## Step 5: Create Database User (Recommended for Production)

For security, create a dedicated user instead of using root:

```sql
-- Create user
CREATE USER 'mcq_user'@'localhost' IDENTIFIED BY 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON mcq_db.* TO 'mcq_user'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;
```

**Note:** Replace `'your_secure_password'` with a strong password.

---

## Step 6: Install Python Dependencies

Open Command Prompt or PowerShell in your project directory:

```bash
pip install -r requirements.txt
```

This installs:
- FastAPI
- SQLAlchemy
- aiomysql (async MySQL driver)
- faster-whisper
- numpy
- pydantic
- uvicorn

---

## Step 7: Set Environment Variable

### Windows PowerShell:

```powershell
# If using root user
$env:DATABASE_URL = "mysql+aiomysql://root:your_password@127.0.0.1:3306/mcq_db"

# If using dedicated user
$env:DATABASE_URL = "mysql+aiomysql://mcq_user:your_secure_password@127.0.0.1:3306/mcq_db"
```

### Windows Command Prompt:

```cmd
setx DATABASE_URL "mysql+aiomysql://root:your_password@127.0.0.1:3306/mcq_db"
```

**Important:** After using `setx`, close and reopen your terminal.

### Linux/Mac:

```bash
export DATABASE_URL="mysql+aiomysql://root:your_password@127.0.0.1:3306/mcq_db"
```

### Connection String Format:

```
mysql+aiomysql://[USERNAME]:[PASSWORD]@[HOST]:[PORT]/[DATABASE_NAME]
```

**Examples:**
- Local with root: `mysql+aiomysql://root:mypassword@127.0.0.1:3306/mcq_db`
- Local with user: `mysql+aiomysql://mcq_user:securepass@localhost:3306/mcq_db`
- Remote server: `mysql+aiomysql://user:pass@192.168.1.100:3306/mcq_db`

---

## Step 8: Test Database Connection

Create a test script `test_db.py`:

```python
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine

async def test_connection():
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        print("❌ DATABASE_URL not set!")
        return
    
    try:
        engine = create_async_engine(database_url, echo=True)
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1")
            print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())
```

Run it:

```bash
python test_db.py
```

---

## Step 9: Start the FastAPI Server

```bash
uvicorn api_pg_mcq:app --reload --host 0.0.0.0 --port 8000
```

Or use the start script:

**Windows:**
```bash
start_server.bat
```

**Linux/Mac:**
```bash
chmod +x start_server.sh
./start_server.sh
```

---

## Step 10: Test the API

Open your browser or use curl:

1. **Health Check:**
   ```
   http://localhost:8000/health
   ```

2. **API Docs:**
   ```
   http://localhost:8000/docs
   ```

3. **Generate MCQs:**
   ```bash
   curl -X POST "http://localhost:8000/generate-and-save" \
        -H "Content-Type: application/json" \
        -d '{"url": "https://example.com/video.mp4"}'
   ```

---

## Troubleshooting

### Error: "Access denied for user"

- Check username and password in `DATABASE_URL`
- Verify user has privileges: `GRANT ALL PRIVILEGES ON mcq_db.* TO 'user'@'localhost';`

### Error: "Unknown database 'mcq_db'"

- Run the SQL setup script again
- Or manually create: `CREATE DATABASE mcq_db;`

### Error: "aiomysql not found"

- Install: `pip install aiomysql`
- Or reinstall requirements: `pip install -r requirements.txt`

### Error: "JSON type not supported"

- MySQL version must be 5.7+ or MariaDB 10.2+
- Check version: `SELECT VERSION();`

### Error: "Can't connect to MySQL server"

- Check if MySQL service is running
- Verify port (default: 3306)
- Check firewall settings
- For XAMPP: Start MySQL from XAMPP Control Panel

### Error: "Table doesn't exist"

- Run the setup SQL script
- Check database name matches in connection string

---

## Common MySQL Workbench Operations

### View Table Data:
```sql
USE mcq_db;
SELECT * FROM video_mcqs LIMIT 10;
```

### Check Table Structure:
```sql
DESCRIBE video_mcqs;
```

### Count Records:
```sql
SELECT COUNT(*) FROM video_mcqs;
```

### Delete All Records (for testing):
```sql
DELETE FROM video_mcqs;
```

### Drop Table (start fresh):
```sql
DROP TABLE IF EXISTS video_mcqs;
-- Then run setup script again
```

---

## Production Recommendations

1. **Use dedicated database user** (not root)
2. **Set strong password** for database user
3. **Enable SSL** for remote connections
4. **Regular backups** of `mcq_db` database
5. **Monitor connection pool** size
6. **Add indexes** as needed for performance

---

## Next Steps

Once setup is complete:

1. ✅ Database created and table exists
2. ✅ Environment variable `DATABASE_URL` is set
3. ✅ Python dependencies installed
4. ✅ Server starts without errors
5. ✅ Test API endpoints work

You're ready to generate and fetch MCQs! 🚀

