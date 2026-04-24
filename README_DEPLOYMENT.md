# Deployment Guide: Drug Discovery Web UI Agent

## Quick Start (Local Development)

### Prerequisites
```bash
python --version  # 3.8+
node --version    # 16+
npm --version     # 8+
```

### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/drug-discovery-tool.git
cd drug-discovery-tool

# Create .env file (copy from .env.example)
cp .env.example .env

# Add your API key to .env
# Edit: ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Install Dependencies
```bash
# Backend
pip install -r requirements.txt

# Frontend
cd web && npm install && cd ..
```

### 3. Run Locally
```bash
# Terminal 1: Backend (port 8000)
uvicorn src.main:app --reload --port 8000

# Terminal 2: Frontend (port 3000)
cd web && npm start

# Open browser: http://localhost:3000
```

---

## Docker Deployment

### Build & Run
```bash
# Build image
docker build -t drug-discovery-agent .

# Run container
docker run -p 8000:8000 -p 3000:3000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e DISCOVERY_MODEL=claude-3-5-sonnet-20241022 \
  drug-discovery-agent
```

### Docker Compose (Recommended for Development)
```bash
# Create .env file
cp .env.example .env

# Start both services
docker-compose up

# Access:
# - Backend: http://localhost:8000
# - Frontend: http://localhost:3000

# Stop
docker-compose down
```

---

## Cloud Deployment

### Option 1: AWS (EC2 + ECS)
```bash
# 1. Build image
docker build -t drug-discovery-agent .

# 2. Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker tag drug-discovery-agent:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/drug-discovery-agent:latest

docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/drug-discovery-agent:latest

# 3. Deploy ECS task with environment variables
# Set: ANTHROPIC_API_KEY (or OPENAI_API_KEY, GOOGLE_API_KEY, etc.)
```

### Option 2: Google Cloud Run
```bash
# 1. Build image
docker build -t drug-discovery-agent .

# 2. Push to Artifact Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT/drug-discovery-agent

# 3. Deploy
gcloud run deploy drug-discovery-agent \
  --image gcr.io/YOUR_PROJECT/drug-discovery-agent \
  --platform managed \
  --region us-central1 \
  --set-env-vars ANTHROPIC_API_KEY=sk-ant-... \
  --allow-unauthenticated
```

### Option 3: Heroku
```bash
# 1. Create Procfile
echo "web: uvicorn src.main:app --host 0.0.0.0 --port $PORT" > Procfile

# 2. Create app & deploy
heroku create drug-discovery-agent
git push heroku main

# 3. Set environment variables
heroku config:set ANTHROPIC_API_KEY=sk-ant-...
heroku config:set DISCOVERY_MODEL=claude-3-5-sonnet-20241022
```

---

## Environment Variables

### Required
```
DISCOVERY_PROVIDER     # anthropic, openai, google, cohere, bedrock
ANTHROPIC_API_KEY      # sk-ant-... (if using Anthropic)
OPENAI_API_KEY         # sk-... (if using OpenAI)
GOOGLE_API_KEY         # AIzaSy... (if using Google Gemini)
DISCOVERY_MODEL        # Model ID (defaults to claude-3-5-sonnet-20241022)
```

### Optional
```
AWS_REGION             # us-west-2 (for Bedrock)
REACT_APP_API_URL      # http://localhost:8000 (frontend to backend)
PORT                   # 8000 (backend port)
```

---

## Production Checklist

- [ ] API key securely stored in environment variables (not in code)
- [ ] HTTPS enabled (required for production)
- [ ] CORS properly configured (allow your domain only)
- [ ] Session timeout set appropriately (30 min default)
- [ ] Logging enabled for debugging
- [ ] Health check endpoint working (`GET /health`)
- [ ] Load balancer configured (if scaling)
- [ ] Database backup strategy (N/A for this stateless app)
- [ ] SSL certificate valid
- [ ] Security headers configured

---

## Scaling Considerations

### Session Management
- **Current:** In-memory dict (single process)
- **For scaling:** Use Redis for distributed sessions

**Change in `src/session_manager.py`:**
```python
# Replace: self.sessions = {}
# With: Redis store (from redis import Redis)
```

### Database
- **Current:** No persistence (credentials in memory only)
- **Recommendation:** Keep stateless (scale horizontally)

### Rate Limiting
- Consider adding rate limiting per session
- Prevent abuse of workflow endpoints

---

## Monitoring & Logging

### Health Check
```bash
curl http://localhost:8000/health
# Response: {"status": "ok", "service": "drug-discovery-api"}
```

### Logs
```bash
# Backend logs (stdout)
uvicorn logs show request/response activity

# Frontend logs
Browser console → Network tab shows API calls
```

### Metrics to Monitor
- API response time (target: <5s)
- Session creation rate
- Failed authentication attempts
- Active sessions at any time

---

## Troubleshooting Deployment

### Issue: "Cannot find module"
```bash
# Ensure dependencies installed
pip install -r requirements.txt
cd web && npm install
```

### Issue: "Port already in use"
```bash
# Find and kill process
lsof -i :8000
kill -9 <PID>

# Or use different port
uvicorn src.main:app --port 8001
```

### Issue: "CORS error"
```bash
# Check: Allow your domain in src/main.py
allow_origins=["http://localhost:3000", "https://yourdomain.com"]
```

### Issue: "API key not working"
```bash
# Verify:
1. Key is correct (test with provider's own tool)
2. Provider name matches exactly (case-sensitive)
3. Model name is valid for provider
4. Environment variable set correctly
```

---

## Support & Documentation

- **Docs:** See README.md (main documentation)
- **Testing:** See TESTING.md (test scenarios)
- **Security:** See SECURITY.md (credential handling)
- **Issues:** GitHub Issues
- **Questions:** Contact Anthropic support (if using Anthropic)

---

## License

MIT License - See LICENSE file
