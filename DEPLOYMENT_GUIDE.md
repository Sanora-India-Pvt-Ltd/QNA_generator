# 🚀 Deployment Guide - FastAPI MCQ Generator

आपके FastAPI + MySQL project को deploy करने के लिए best options:

---

## 🎯 Recommended Deployment Platforms

### Option 1: **Railway** (Easiest - Recommended) ⭐
- ✅ Free tier available
- ✅ MySQL database included
- ✅ Easy setup
- ✅ Auto-deploy from GitHub
- ✅ Good for MVP/Production

### Option 2: **Render**
- ✅ Free tier available
- ✅ PostgreSQL/MySQL support
- ✅ Easy deployment
- ✅ Good documentation

### Option 3: **DigitalOcean App Platform**
- ✅ Managed MySQL
- ✅ Good performance
- ✅ $5/month starting

### Option 4: **AWS EC2** (Advanced)
- ✅ Full control
- ✅ Scalable
- ✅ Requires more setup

### Option 5: **Heroku** (Limited Free Tier)
- ⚠️ No longer free
- ✅ Easy setup
- ✅ Good for learning

---

## 🚂 Option 1: Railway Deployment (Recommended)

### Step 1: Prepare Your Code

1. **Create `Procfile`** (for Railway):
```
web: uvicorn api_pg_mcq:app --host 0.0.0.0 --port $PORT
```

2. **Create `runtime.txt`** (optional, specify Python version):
```
python-3.11.0
```

3. **Update `requirements.txt`** (make sure all dependencies are there)

### Step 2: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/mcq-generator.git
git push -u origin main
```

### Step 3: Deploy on Railway

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose your repository
6. Railway will auto-detect FastAPI

### Step 4: Add MySQL Database

1. In Railway project, click **"+ New"**
2. Select **"Database"** → **"MySQL"**
3. Railway will create MySQL instance
4. Copy the connection string

### Step 5: Set Environment Variables

In Railway project settings, add:

```
DATABASE_URL=mysql+aiomysql://user:pass@host:port/dbname
OLLAMA_MODEL=qwen2.5:1.5b
WHISPER_MODEL_SIZE=base
MCQ_COUNT=20
```

### Step 6: Run Database Setup

1. Go to MySQL service in Railway
2. Click **"Connect"** → **"MySQL Shell"**
3. Run `setup_database_mysql.sql` script

### Step 7: Deploy!

Railway will automatically deploy. Your API will be live!

---

## 🎨 Option 2: Render Deployment

### Step 1: Prepare Code (same as Railway)

### Step 2: Deploy on Render

1. Go to [render.com](https://render.com)
2. Sign up
3. Click **"New +"** → **"Web Service"**
4. Connect GitHub repository
5. Settings:
   - **Name:** mcq-generator
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api_pg_mcq:app --host 0.0.0.0 --port $PORT`

### Step 3: Add MySQL Database

1. Click **"New +"** → **"PostgreSQL"** (or MySQL if available)
2. Copy connection string
3. Add to environment variables

### Step 4: Set Environment Variables

In Render dashboard:
```
DATABASE_URL=your_connection_string
OLLAMA_MODEL=qwen2.5:1.5b
WHISPER_MODEL_SIZE=base
```

---

## ☁️ Option 3: DigitalOcean App Platform

### Step 1: Create App

1. Go to [DigitalOcean](https://www.digitalocean.com)
2. **App Platform** → **Create App**
3. Connect GitHub repository

### Step 2: Configure

- **Build Command:** `pip install -r requirements.txt`
- **Run Command:** `uvicorn api_pg_mcq:app --host 0.0.0.0 --port $PORT`

### Step 3: Add Managed Database

1. Add **Managed MySQL Database**
2. Copy connection string
3. Add to environment variables

---

## 🐳 Option 4: Docker Deployment (Any Platform)

### Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "api_pg_mcq:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+aiomysql://root:password@db:3306/mcq_db
      - OLLAMA_MODEL=qwen2.5:1.5b
      - WHISPER_MODEL_SIZE=base
    depends_on:
      - db

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=mcq_db
    volumes:
      - mysql_data:/var/lib/mysql
      - ./setup_database_mysql.sql:/docker-entrypoint-initdb.d/init.sql

volumes:
  mysql_data:
```

### Deploy:

```bash
docker-compose up -d
```

---

## ⚠️ Important Considerations

### 1. **FFmpeg Required**
- Most platforms need FFmpeg installed
- Railway/Render: Add buildpack or install in Dockerfile
- DigitalOcean: Install via package manager

### 2. **Ollama Installation**
- Ollama needs to be installed on server
- Or use external Ollama API
- Consider using cloud LLM API instead

### 3. **Whisper Model**
- First run downloads model (~150MB for base)
- Consider pre-downloading in Docker image

### 4. **Database Setup**
- Run `setup_database_mysql.sql` after database creation
- Or use auto-migration in code

### 5. **Environment Variables**
Always set:
```
DATABASE_URL=...
OLLAMA_MODEL=qwen2.5:1.5b
WHISPER_MODEL_SIZE=base
MCQ_COUNT=20
```

---

## 📋 Pre-Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] `requirements.txt` updated
- [ ] Environment variables documented
- [ ] Database connection string ready
- [ ] FFmpeg installation method decided
- [ ] Ollama setup planned
- [ ] Tested locally with production-like settings

---

## 🎯 Quick Recommendation

**For MVP/Testing:** Use **Railway**
- Easiest setup
- Free tier
- MySQL included
- Auto-deploy

**For Production:** Use **DigitalOcean** or **AWS**
- Better performance
- More control
- Scalable

---

## 📚 Next Steps

1. Choose a platform
2. Follow platform-specific guide above
3. Test deployment
4. Set up monitoring
5. Configure domain (optional)

---

## 🆘 Need Help?

- Railway Docs: https://docs.railway.app
- Render Docs: https://render.com/docs
- DigitalOcean Docs: https://docs.digitalocean.com

Good luck with deployment! 🚀





