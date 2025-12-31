# 🚂 Railway Deployment Guide (Step-by-Step)

## Prerequisites
- GitHub account
- Railway account (free signup)

---

## Step 1: Prepare Your Code

### 1.1 Create `Procfile`
Already created! ✅

### 1.2 Update `requirements.txt`
Make sure all dependencies are listed.

### 1.3 Test Locally
```bash
python api_pg_mcq.py
# Or
uvicorn api_pg_mcq:app --reload
```

---

## Step 2: Push to GitHub

```bash
# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "Ready for deployment"

# Add remote (replace with your repo)
git remote add origin https://github.com/YOUR_USERNAME/mcq-generator.git

# Push
git push -u origin main
```

---

## Step 3: Deploy on Railway

### 3.1 Sign Up
1. Go to [railway.app](https://railway.app)
2. Click **"Start a New Project"**
3. Sign up with GitHub

### 3.2 Create Project
1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose your repository
4. Railway will auto-detect FastAPI

### 3.3 Add MySQL Database
1. In your project, click **"+ New"**
2. Select **"Database"**
3. Choose **"MySQL"**
4. Railway creates MySQL instance automatically
5. **Copy the connection string** (you'll need it)

### 3.4 Configure Environment Variables
1. Go to your **Web Service** → **Variables**
2. Add these:

```
DATABASE_URL=<paste_mysql_connection_string_from_database_service>
OLLAMA_MODEL=qwen2.5:1.5b
WHISPER_MODEL_SIZE=base
MCQ_COUNT=20
SAMPLE_CLIPS=8
CLIP_SECONDS=12
```

**Note:** Railway gives you DATABASE_URL automatically. Click on MySQL service → **Variables** → Copy `DATABASE_URL`

### 3.5 Setup Database
1. Go to MySQL service
2. Click **"Connect"** → **"MySQL Shell"**
3. Run:
```sql
USE mcq_db;
SOURCE /path/to/setup_database_mysql.sql;
```
Or manually run the SQL from `setup_database_mysql.sql`

### 3.6 Deploy
Railway automatically deploys when you push to GitHub!

---

## Step 4: Get Your URL

1. Go to your **Web Service**
2. Click **"Settings"**
3. Under **"Domains"**, you'll see your URL
4. Example: `https://your-app-name.up.railway.app`

---

## Step 5: Test Your API

```bash
# Health check
curl https://your-app-name.up.railway.app/health

# API docs
https://your-app-name.up.railway.app/docs
```

---

## Step 6: Custom Domain (Optional)

1. In Railway → **Settings** → **Domains**
2. Click **"Generate Domain"** or add custom domain
3. Follow DNS setup instructions

---

## Troubleshooting

### Build Fails
- Check Railway logs
- Verify `requirements.txt` is correct
- Check Python version compatibility

### Database Connection Error
- Verify `DATABASE_URL` is set correctly
- Check MySQL service is running
- Verify database name is `mcq_db`

### FFmpeg Not Found
- Add to Dockerfile (if using Docker)
- Or use Railway's buildpack

### Ollama Not Available
- Install Ollama in build process
- Or use external Ollama API
- Consider cloud LLM alternative

---

## Railway Pricing

- **Free Tier:** $5 credit/month
- **Hobby:** $5/month (after free tier)
- **Pro:** $20/month

Free tier is usually enough for testing/MVP!

---

## Next Steps

1. ✅ Deploy on Railway
2. ✅ Test all endpoints
3. ✅ Monitor usage
4. ✅ Set up custom domain (optional)
5. ✅ Configure backups

Your API is now live! 🎉



