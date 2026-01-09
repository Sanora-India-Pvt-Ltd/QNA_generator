# 🔧 Troubleshooting 502 Bad Gateway Error

## ❌ Problem
```
502: Bad gateway
Error code 502
Host: api.drishtifilmproductions.com - Error
```

**Meaning:** Cloudflare is working, but your backend server is not responding.

---

## ✅ Quick Checks

### 1. Check if Server is Running Locally

```bash
# Check if FastAPI server is running
curl http://localhost:8000/health

# Or check in browser
http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "ready",
  "ollama_available": true,
  "whisper_model": "base",
  "db_configured": true
}
```

---

### 2. Check Server Logs

Look for errors in your server logs:
- Application crashed?
- Database connection failed?
- Port already in use?
- Missing dependencies?

---

### 3. Common Causes & Solutions

#### 🔴 Cause 1: Server Not Running

**Solution:**
```bash
# Start the server
cd c:\Anaconda\envs\sanora
python api_pg_mcq.py

# Or with uvicorn
uvicorn api_pg_mcq:app --host 0.0.0.0 --port 8000
```

---

#### 🔴 Cause 2: Wrong Port/Configuration

**Check:**
- Is server running on correct port?
- Does Cloudflare point to correct backend?
- Is firewall blocking the port?

**Solution:**
```python
# In your code, check:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

#### 🔴 Cause 3: Database Connection Failed

**Check:**
```bash
# Verify DATABASE_URL is set
echo $DATABASE_URL

# Or in Windows PowerShell
$env:DATABASE_URL
```

**Solution:**
- Ensure MySQL is running
- Check DATABASE_URL format: `mysql+aiomysql://user:pass@host:port/db`
- Test connection manually

---

#### 🔴 Cause 4: Application Crashed on Startup

**Check logs for:**
- Import errors
- Missing dependencies
- Ollama not found
- Whisper model loading failed

**Solution:**
```bash
# Install missing dependencies
pip install -r requirements.txt

# Check Ollama
ollama --version

# Test imports
python -c "from faster_whisper import WhisperModel; print('OK')"
```

---

#### 🔴 Cause 5: Timeout Issues

**Symptoms:**
- Server starts but requests timeout
- Health check works but /videos/mcqs times out

**Solution:**
- Increase Cloudflare timeout settings
- Check if video processing is too slow
- Add timeout handling in code

---

## 🧪 Test Script

Create `test_server.py`:

```python
import requests
import sys

def test_server(base_url="http://localhost:8000"):
    print(f"Testing server at {base_url}...")
    
    # Test 1: Health check
    try:
        r = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Health check: {r.status_code}")
        print(f"   Response: {r.json()}")
    except requests.exceptions.ConnectionError:
        print("❌ Server not running!")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Root endpoint
    try:
        r = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Root endpoint: {r.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: API docs
    try:
        r = requests.get(f"{base_url}/docs", timeout=5)
        print(f"✅ API docs: {r.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return True

if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    test_server(base_url)
```

**Run:**
```bash
python test_server.py
python test_server.py http://api.drishtifilmproductions.com
```

---

## 🔍 Debugging Steps

### Step 1: Check Server Status
```bash
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000
```

### Step 2: Check Application Logs
Look for:
- Startup errors
- Database connection errors
- Import errors
- Runtime exceptions

### Step 3: Test Health Endpoint
```bash
curl http://localhost:8000/health
```

### Step 4: Check Cloudflare Settings
- Origin server URL correct?
- SSL/TLS settings correct?
- Timeout settings adequate?

---

## 🚀 Quick Fix: Restart Server

```bash
# Stop existing server (Ctrl+C)
# Then restart:

cd c:\Anaconda\envs\sanora
python api_pg_mcq.py

# Or with uvicorn:
uvicorn api_pg_mcq:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📋 Checklist

- [ ] Server is running locally
- [ ] Health endpoint responds (`/health`)
- [ ] Database connection works
- [ ] Ollama is installed and accessible
- [ ] All dependencies installed
- [ ] Port is not blocked by firewall
- [ ] Cloudflare origin URL is correct
- [ ] Cloudflare timeout settings are adequate
- [ ] SSL certificate is valid (if using HTTPS)

---

## 🆘 Still Not Working?

1. **Check server logs** - Look for error messages
2. **Test locally first** - `http://localhost:8000/health`
3. **Check Cloudflare dashboard** - Origin server status
4. **Verify environment variables** - DATABASE_URL, etc.
5. **Test with curl/Postman** - Bypass Cloudflare temporarily

---

## 📞 Next Steps

If server is running locally but Cloudflare shows 502:

1. **Check Cloudflare Origin Settings**
   - Origin server: `http://your-server-ip:8000`
   - SSL mode: Flexible or Full

2. **Check Firewall**
   - Allow port 8000 (or your port)
   - Allow Cloudflare IPs

3. **Check Server Configuration**
   - Server should listen on `0.0.0.0` not `127.0.0.1`
   - Port should match Cloudflare origin

4. **Test Direct Connection**
   ```bash
   curl http://your-server-ip:8000/health
   ```



