# Phase 10: Deployment Guide

Complete guide to deploy Wen-Arkhas to production using Railway (backend) and Vercel (frontend).

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Backend Deployment (Railway)](#backend-deployment-railway)
3. [Frontend Deployment (Vercel)](#frontend-deployment-vercel)
4. [Environment Variables](#environment-variables)
5. [Post-Deployment](#post-deployment)
6. [Monitoring & Logs](#monitoring--logs)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Accounts
- [Railway.app](https://railway.app) account
- [Vercel.com](https://vercel.com) account
- GitHub account (for git integration)

### Required API Keys
- OpenRouter API key (Claude AI)
- Google Maps API key
- Pinecone API key

### Local Setup
```bash
# Install Railway CLI
npm i -g @railway/cli

# Install Vercel CLI
npm i -g vercel

# Authenticate
railway login
vercel login
```

---

## Backend Deployment (Railway)

### Step 1: Prepare Repository

Ensure your GitHub repo is updated:
```bash
cd wen-arkhas
git add .
git commit -m "Phase 10: Deployment configuration"
git push origin main
```

### Step 2: Create Railway Project

Option A: Using Railway CLI
```bash
railway init
# Select "Create a new project"
# Name: wen-arkhas-backend
```

Option B: Using Web Dashboard
1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub"
4. Connect your repository
5. Select the `backend` directory as root

### Step 3: Configure Environment Variables

In Railway dashboard:
1. Go to Project → Variables
2. Add the following:

```
OPENROUTER_API_KEY=your_api_key_here
GOOGLE_MAPS_API_KEY=your_api_key_here
PINECONE_API_KEY=your_api_key_here
PINECONE_ENVIRONMENT=us-east1-aws
REDIS_URL=redis://redis:6379  # Railway will provide this
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Step 4: Add PostgreSQL (Optional)

For production data storage:
1. Click "+ Add Service"
2. Select "PostgreSQL"
3. Railway will automatically add `DATABASE_URL`

### Step 5: Deploy

Option A: Auto-deploy (Recommended)
```bash
# Push to main branch triggers automatic deployment
git push origin main
```

Option B: Manual deploy
```bash
railway deploy
```

### Step 6: Verify Deployment

```bash
# Check service status
railway status

# View logs
railway logs

# Test health endpoint
curl https://your-railway-app.railway.app/health
```

---

## Frontend Deployment (Vercel)

### Step 1: Prepare for Vercel

Update environment for Vercel build:
```bash
# Create vercel.json (already done)
# Ensure next.config.js is production-ready
```

### Step 2: Deploy Using Vercel CLI

```bash
cd frontend
vercel login
vercel deploy --prod
```

### Step 3: Deploy Using Web Dashboard

1. Go to [vercel.com](https://vercel.com)
2. Click "Add New → Project"
3. Select your GitHub repository
4. Select `frontend` as root directory
5. Click "Deploy"

### Step 4: Configure Environment Variables

In Vercel dashboard:
1. Go to Project → Settings → Environment Variables
2. Add:

```
NEXT_PUBLIC_API_URL=https://your-railway-app.railway.app
```

3. Click "Save and Deploy"

### Step 5: Custom Domain (Optional)

1. Go to Project → Settings → Domains
2. Add your domain (e.g., `wen-arkhas.app`)
3. Follow DNS setup instructions
4. Wait for SSL certificate (usually 24 hours)

### Step 6: Verify Deployment

```bash
# Test in browser
https://your-vercel-app.vercel.app

# Check analytics and logs
# Available in Vercel dashboard → Analytics
```

---

## Environment Variables

### Backend (Railway)

| Variable | Required | Description |
|----------|----------|-------------|
| OPENROUTER_API_KEY | ✅ | API key for Claude AI via OpenRouter |
| GOOGLE_MAPS_API_KEY | ✅ | API key for Google Places API |
| PINECONE_API_KEY | ✅ | API key for Pinecone vector DB |
| PINECONE_ENVIRONMENT | ✅ | Pinecone region (us-east1-aws) |
| REDIS_URL | ✅ | Redis connection string |
| ENVIRONMENT | ❌ | Set to "production" |
| LOG_LEVEL | ❌ | INFO, DEBUG, or ERROR |

### Frontend (Vercel)

| Variable | Required | Description |
|----------|----------|-------------|
| NEXT_PUBLIC_API_URL | ✅ | Backend API URL (Railway app URL) |
| NEXT_PUBLIC_GA_ID | ❌ | Google Analytics tracking ID |

---

## Post-Deployment

### Step 1: Verify Integration

```bash
# Test search endpoint
curl -X POST https://your-railway-app.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test product",
    "location": {"lat": 33.89, "lng": 35.50}
  }'

# Test health check
curl https://your-railway-app.railway.app/health

# Test frontend loads
curl https://your-vercel-app.vercel.app
```

### Step 2: Enable CORS Properly

Update backend `app/main.py` with production domain:

```python
allow_origins=[
    "http://localhost:3000",
    "https://your-vercel-app.vercel.app",
    "https://your-custom-domain.app"
]
```

Deploy the change:
```bash
git add backend/app/main.py
git commit -m "Update CORS for production domains"
git push origin main
```

### Step 3: Set Up SSL/TLS

Both Railway and Vercel provide free SSL automatically. ✅

### Step 4: Configure Monitoring

#### Railway
1. Go to Project → Logs
2. Set up log retention (30 days recommended)
3. Enable error notifications

#### Vercel
1. Go to Project → Analytics
2. Set up performance monitoring
3. Enable Slack/email notifications

---

## Monitoring & Logs

### Railway Logs

View real-time logs:
```bash
railway logs -f  # Follow logs
railway logs --tail 100  # Last 100 lines
```

### Vercel Analytics

1. Go to Project → Analytics
2. Monitor:
   - Web Vitals (LCP, FID, CLS)
   - Edge requests and cache hits
   - Bandwidth usage

### Health Checks

Set up automated monitoring:

```bash
# Health check script
#!/bin/bash
response=$(curl -s https://your-railway-app.railway.app/health)
if echo "$response" | grep -q "healthy"; then
  echo "✅ Backend healthy"
else
  echo "❌ Backend down - Alert!"
  # Send notification
fi
```

---

## Troubleshooting

### Issue: Backend not starting

**Solution:**
```bash
# Check logs
railway logs

# Common issues:
# 1. Missing environment variables - Add to Railway dashboard
# 2. Port not exposed - Ensure PORT=8000 in Dockerfile
# 3. Dependencies - Check requirements.txt is complete
```

### Issue: CORS errors in browser

**Solution:**
```python
# Update CORS origins in app/main.py
allow_origins=[
    "https://your-vercel-app.vercel.app",
    "https://your-domain.app"
]

# Redeploy
git push origin main
```

### Issue: Frontend can't reach backend

**Solution:**
```bash
# Check environment variable
# Vercel → Settings → Environment Variables
# NEXT_PUBLIC_API_URL should be Railway app URL

# Verify connectivity
curl https://your-railway-app.railway.app/health

# Check CORS headers in response
curl -i https://your-railway-app.railway.app/health
```

### Issue: Slow API responses

**Solutions:**
```
1. Check database queries - Optimize in app/services/
2. Enable caching - Verify Redis connection
3. Scale up - Railway → Settings → Scale up resources
4. Optimize embeddings - Check Pinecone performance
```

### Issue: High memory usage

**Solutions:**
```
1. Monitor - Railway → Metrics
2. Reduce batch size in scrapers
3. Implement pagination for large results
4. Clear old cache entries
```

### Issue: Vercel deployment fails

**Solution:**
```bash
# Check build logs
vercel logs --tail

# Common issues:
# 1. Missing dependencies - npm install
# 2. TypeScript errors - npm run build (locally)
# 3. Environment variables - Check .env handling
# 4. Build time limit - Optimize build
```

---

## Performance Optimization

### Backend (Railway)

1. **Caching Strategy**
   - Redis for store cache (24h)
   - Redis for product cache (6h)
   - In-memory for search results (1h)

2. **Database Optimization**
   - Add indexes to frequently queried columns
   - Implement query pagination
   - Use connection pooling

3. **Scraping Optimization**
   - Respect rate limits (1 req/sec)
   - Cache aggressively
   - Parallel scraping with limits

4. **Scaling**
   - Monitor CPU/Memory in Railway
   - Scale vertically (Railway) or horizontally (Render)

### Frontend (Vercel)

1. **Build Optimization**
   - Image optimization enabled
   - Code splitting automatic
   - CSS minification enabled

2. **Runtime Optimization**
   - Next.js middleware for caching
   - ISR (Incremental Static Regeneration) for static pages
   - SWR/React Query for data caching

3. **Monitoring**
   - Track Web Vitals
   - Monitor error rates
   - Track API latency

---

## Security Checklist

- [ ] All API keys stored in environment variables (not in code)
- [ ] HTTPS enabled on both backend and frontend
- [ ] CORS properly configured for production domains
- [ ] Rate limiting enabled (1 req/sec per domain)
- [ ] Input validation on all endpoints
- [ ] Error messages don't leak sensitive info
- [ ] Logs don't contain sensitive data
- [ ] Security headers set (Railway/Vercel do this)
- [ ] Environment variables not logged
- [ ] Regular security updates for dependencies

---

## Rollback Procedure

### Railway
```bash
# View deployment history
railway status

# Rollback to previous version
railway rollback
```

### Vercel
1. Go to Project → Deployments
2. Find previous successful deployment
3. Click "..." → "Promote to Production"

---

## Post-Launch Tasks

1. **Monitoring**
   - [ ] Set up uptime monitoring (Uptime Robot, etc.)
   - [ ] Set up error alerts (Sentry, LogRocket)
   - [ ] Monitor API response times

2. **Analytics**
   - [ ] Set up Google Analytics
   - [ ] Track user behavior
   - [ ] Monitor search trends

3. **Optimization**
   - [ ] Analyze slow endpoints
   - [ ] Optimize database queries
   - [ ] Cache frequently used data

4. **Maintenance**
   - [ ] Set up automated backups
   - [ ] Plan security updates schedule
   - [ ] Document runbooks for common issues

---

## Support & Resources

- **Railway Docs:** https://docs.railway.app
- **Vercel Docs:** https://vercel.com/docs
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment
- **Next.js Deployment:** https://nextjs.org/docs/deployment

---

## Production URLs (Example)

```
Backend:  https://wen-arkhas-api.railway.app
Frontend: https://wen-arkhas.vercel.app
Domain:   https://wen-arkhas.app (optional)
```

---

**Deployment Date:** 2025-12-10
**Status:** Ready for Production
**Version:** 1.0.0
**Last Updated:** 2025-12-10
