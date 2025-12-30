# Fast Video MCQ Generator + MySQL Cache

A FastAPI service that generates multiple-choice questions (MCQs) from video URLs, stores them in MySQL/MariaDB, and serves them instantly.

## Features

- **Generate Once**: MCQs are generated once per video and cached in MySQL
- **Fast Fetch**: Retrieve MCQs in <200ms (target: <5 seconds)
- **Async MySQL**: Uses SQLAlchemy async + aiomysql for high performance
- **Video Processing**: Uses Faster Whisper for transcription and Ollama for MCQ generation

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup MySQL Database

**Option A: Using MySQL Workbench (Recommended)**

1. Open MySQL Workbench
2. Connect to your MySQL server
3. File → Open SQL Script → Select `setup_database_mysql.sql`
4. Click Execute (or press `Ctrl+Shift+Enter`)

**Option B: Using Command Line**

```bash
mysql -u root -p < setup_database_mysql.sql
```

**See detailed guide:** [MYSQL_SETUP_GUIDE.md](MYSQL_SETUP_GUIDE.md)

### 3. Set Environment Variable

**Windows PowerShell:**
```powershell
$env:DATABASE_URL = "mysql+aiomysql://root:your_password@127.0.0.1:3306/mcq_db"
```

**Windows Command Prompt:**
```cmd
setx DATABASE_URL "mysql+aiomysql://root:your_password@127.0.0.1:3306/mcq_db"
```
*(Close and reopen terminal after setx)*

**Linux/Mac:**
```bash
export DATABASE_URL="mysql+aiomysql://root:your_password@127.0.0.1:3306/mcq_db"
```

### 4. Test Database Connection

```bash
python test_db_connection.py
```

### 5. Start the Server

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

## API Endpoints

### 1. Generate and Save MCQs

**POST** `/generate-and-save`

Generate MCQs for a video URL and save to database.

**Request Body:**
```json
{
  "url": "https://example.com/video.mp4",
  "force": false
}
```

**Response:**
```json
{
  "status": "saved",
  "video_id": "abc123def456",
  "count": 20,
  "time_seconds": 45.23
}
```

### 2. Fetch MCQs by Video ID

**GET** `/videos/{video_id}/mcqs`

Fetch MCQs for a video (fast, from database).

**Query Parameters:**
- `include_answers` (bool, default: false) - Include correct answers
- `randomize` (bool, default: true) - Randomize question order
- `limit` (int, default: 20, max: 50) - Number of questions to return

**Example:**
```
GET /videos/abc123def456/mcqs?limit=20&randomize=true
```

**Response:**
```json
{
  "status": "success",
  "video_id": "abc123def456",
  "count": 20,
  "questions": [
    {
      "question": "What is the main topic?",
      "options": {
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
      }
    }
  ]
}
```

### 3. Fetch MCQs by URL

**POST** `/videos/mcqs/by-url?url={video_url}`

Convenience endpoint to fetch by URL directly.

**Query Parameters:**
- `url` (required) - Video URL

**Request Body:**
```json
{
  "include_answers": false,
  "randomize": true,
  "limit": 20
}
```

### 4. Health Check

**GET** `/health`

Check service status and configuration.

### 5. API Documentation

**GET** `/docs`

Interactive API documentation (Swagger UI).

## Usage Workflow

### When Video is Uploaded (Admin/Background)

1. Save video URL in your main backend
2. Call the generate endpoint:

```python
import requests

response = requests.post(
    "http://localhost:8000/generate-and-save",
    json={"url": "https://example.com/video.mp4"}
)
print(response.json())
```

This may take time, but happens **once per video**.

### When User Opens "Test"

Call the fetch endpoint:

```python
video_id = "abc123def456"  # From generate response
response = requests.get(
    f"http://localhost:8000/videos/{video_id}/mcqs",
    params={"limit": 20, "randomize": True}
)
mcqs = response.json()["questions"]
```

This returns in **milliseconds** (<200ms typical).

## Database Connection Strings

### Local MySQL
```
mysql+aiomysql://root:password@127.0.0.1:3306/mcq_db
```

### Local MySQL with Custom User
```
mysql+aiomysql://mcq_user:secure_password@localhost:3306/mcq_db
```

### Remote MySQL Server
```
mysql+aiomysql://user:password@192.168.1.100:3306/mcq_db
```

### Connection String Format
```
mysql+aiomysql://[USERNAME]:[PASSWORD]@[HOST]:[PORT]/[DATABASE_NAME]
```

## Requirements

- Python 3.8+
- MySQL 5.7+ or MariaDB 10.2+ (for JSON support)
- FFmpeg (for video processing)
- Ollama (for MCQ generation)
- Faster Whisper (installed via pip)

## Configuration

Set these environment variables to customize behavior:

```bash
OLLAMA_MODEL=qwen2.5:1.5b          # Ollama model to use
WHISPER_MODEL_SIZE=base              # Whisper model size
MCQ_COUNT=20                         # Number of MCQs to generate (default: 20)
SAMPLE_CLIPS=8                      # Number of video clips to sample
CLIP_SECONDS=12                     # Duration of each clip in seconds
```

**To generate 50 questions per video:**
```bash
setx MCQ_COUNT 50
```

## Documentation

- **[MYSQL_SETUP_GUIDE.md](MYSQL_SETUP_GUIDE.md)** - Complete MySQL setup guide
- **[MYSQL_WORKBENCH_QUICK_START.md](MYSQL_WORKBENCH_QUICK_START.md)** - Quick start for MySQL Workbench

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

## Notes

- **Generate Once**: MCQs are generated once and cached. Use `force=true` to regenerate.
- **Anti-Cheat**: By default, correct answers are NOT included in fetch responses.
- **Video ID**: Deterministic SHA1 hash of URL (first 16 chars).
- **50 Questions**: Set `MCQ_COUNT=50` environment variable to generate 50 questions per video.

## Production Deployment

For production, consider:

1. **Background Jobs**: Don't run generation inside user requests. Use a job queue (Celery, RQ, etc.)
2. **Connection Pooling**: Adjust SQLAlchemy pool settings for your database
3. **Error Handling**: Add retry logic and proper error responses
4. **Monitoring**: Add logging and metrics
5. **Security**: Add authentication/authorization
6. **Backups**: Regular backups of `mcq_db` database

## License

MIT
