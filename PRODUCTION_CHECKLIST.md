# Production Checklist - Phase 10

Complete checklist before deploying Wen-Arkhas to production.

## Pre-Deployment

### Code Quality
- [ ] All tests passing (`npm test` in backend)
- [ ] No console errors or warnings
- [ ] No hardcoded credentials or API keys
- [ ] All environment variables documented
- [ ] Code linting clean (`npm run lint`)
- [ ] TypeScript compilation without errors
- [ ] No deprecated dependencies
- [ ] All endpoints documented in API docs

### Backend
- [ ] Health check endpoint working
- [ ] All 5 agents tested with real data
- [ ] Error handling comprehensive
- [ ] Logging configured properly
- [ ] Database migrations tested
- [ ] Redis connection working
- [ ] Rate limiting configured
- [ ] CORS configured for frontend domain
- [ ] All external APIs accessible
- [ ] Timeout values appropriate
- [ ] Request validation in place
- [ ] Response compression enabled

### Frontend
- [ ] All pages load without errors
- [ ] Mobile responsive on all screen sizes
- [ ] Images optimized and loading correctly
- [ ] API integration tested
- [ ] Forms validate properly
- [ ] Error messages user-friendly
- [ ] Loading states show correctly
- [ ] Accessibility checks passed (WCAG)
- [ ] SEO meta tags present
- [ ] No console errors in browser

### Testing
- [ ] Unit tests passing (backend)
- [ ] Integration tests passing
- [ ] Manual smoke tests completed
- [ ] E2E tests passing (if implemented)
- [ ] Performance tests completed
- [ ] Security scan completed

---

## Environment Setup

### Backend (Railway)
- [ ] Project created in Railway
- [ ] Git repository connected
- [ ] Environment variables added:
  - [ ] OPENROUTER_API_KEY
  - [ ] GOOGLE_MAPS_API_KEY
  - [ ] PINECONE_API_KEY
  - [ ] PINECONE_ENVIRONMENT
  - [ ] REDIS_URL
  - [ ] ENVIRONMENT=production
  - [ ] LOG_LEVEL=INFO
- [ ] Redis service provisioned
- [ ] PostgreSQL added (if needed)
- [ ] Domain configured
- [ ] SSL certificate auto-generated
- [ ] Health checks enabled

### Frontend (Vercel)
- [ ] Project created in Vercel
- [ ] Git repository connected
- [ ] Environment variables added:
  - [ ] NEXT_PUBLIC_API_URL (Railway backend URL)
  - [ ] NEXT_PUBLIC_GA_ID (if using analytics)
- [ ] Build settings configured
- [ ] Output directory set to `.next`
- [ ] Domain configured
- [ ] SSL certificate auto-generated
- [ ] Auto-deploy on push enabled (main branch)

### External Services
- [ ] OpenRouter API account created and funded
- [ ] Google Maps API key created and enabled
- [ ] Pinecone account created
- [ ] Pinecone index created
- [ ] All API keys rotated and secure
- [ ] API rate limits reviewed

---

## Deployment

### Preparation
- [ ] Code committed and pushed to main
- [ ] No pending changes in git
- [ ] Feature branches merged and deleted
- [ ] Commit messages clear and descriptive
- [ ] Tags created for release version (v1.0.0)

### Backend Deployment
- [ ] Docker build succeeds locally
- [ ] Dockerfile tested locally
- [ ] docker-compose.yml works locally
- [ ] Railway deployment triggered
- [ ] Deployment logs checked for errors
- [ ] No failed builds
- [ ] Service marked as healthy
- [ ] Health endpoint responds with 200

### Frontend Deployment
- [ ] Build succeeds locally (`npm run build`)
- [ ] Build time under 2 minutes
- [ ] No build warnings
- [ ] Vercel deployment triggered
- [ ] Deployment logs checked
- [ ] No failed builds
- [ ] Preview URL works
- [ ] Production URL works

---

## Post-Deployment Verification

### API Endpoints
- [ ] Health check endpoint responds
  ```bash
  curl https://backend-url/health
  ```
- [ ] Search endpoint accessible
  ```bash
  curl -X POST https://backend-url/api/search \
    -H "Content-Type: application/json" \
    -d '{"query":"test","location":{"lat":33.89,"lng":35.50}}'
  ```
- [ ] Stream endpoint accessible
  ```bash
  curl "https://backend-url/api/search/stream?query=test&lat=33.89&lng=35.50"
  ```
- [ ] CORS headers present in responses
- [ ] Response times acceptable (<5s for search)

### Frontend
- [ ] Home page loads without errors
- [ ] Search form accepts input
- [ ] API URL configured correctly
- [ ] Responsive on mobile/tablet/desktop
- [ ] No console errors
- [ ] Recent searches appear
- [ ] Results page displays properly
- [ ] Product cards render correctly
- [ ] Filters work correctly
- [ ] Sorting works correctly

### Integration
- [ ] Frontend can reach backend
- [ ] Search works end-to-end
- [ ] Results display properly
- [ ] Product images load
- [ ] External links work
- [ ] No CORS errors
- [ ] Error messages display correctly

### Performance
- [ ] Page load time < 3s (frontend)
- [ ] Search response time < 10s
- [ ] No console warnings
- [ ] Images optimized
- [ ] CSS minified
- [ ] JavaScript optimized
- [ ] Core Web Vitals green

### Security
- [ ] HTTPS enabled on both endpoints
- [ ] Security headers present
- [ ] No sensitive data in logs
- [ ] API keys not exposed
- [ ] Input validation working
- [ ] SQL injection prevented
- [ ] XSS protection enabled
- [ ] CSRF protection enabled
- [ ] Rate limiting working

---

## Monitoring Setup

### Railway Backend
- [ ] Logs configured and accessible
- [ ] Error alerts configured
- [ ] Uptime monitoring enabled
- [ ] Performance metrics collected
- [ ] Database backups configured
- [ ] Auto-scaling configured (if needed)

### Vercel Frontend
- [ ] Analytics enabled
- [ ] Web Vitals tracked
- [ ] Error reporting enabled
- [ ] Performance insights available
- [ ] Deployment notifications set up

### Third-Party Services
- [ ] Uptime monitoring service configured (Uptime Robot)
- [ ] Error tracking service set up (Sentry)
- [ ] Analytics configured (Google Analytics)
- [ ] Notification channels set up (Slack, Email)

---

## Documentation

- [ ] Deployment guide updated
- [ ] API documentation complete
- [ ] Frontend documentation complete
- [ ] Environment variables documented
- [ ] Troubleshooting guide updated
- [ ] Runbooks created for common issues
- [ ] Architecture diagram created
- [ ] Database schema documented
- [ ] API endpoints documented
- [ ] Release notes prepared

---

## Backup & Recovery

- [ ] Database backups automated
- [ ] Backup retention policy set (30 days)
- [ ] Backup restoration tested
- [ ] Disaster recovery plan documented
- [ ] Rollback procedure tested
- [ ] Data export procedure documented

---

## Security Audit

### Code
- [ ] No hardcoded secrets in code
- [ ] No API keys in .env files checked into git
- [ ] Dependencies scanned for vulnerabilities
- [ ] No deprecated packages
- [ ] SQL prepared statements used
- [ ] Input validation on all endpoints
- [ ] Output encoding enabled
- [ ] HTTPS enforced

### Infrastructure
- [ ] Firewall configured
- [ ] Only necessary ports open
- [ ] DDoS protection enabled (Vercel/Railway)
- [ ] WAF rules configured
- [ ] Security headers set
- [ ] CORS configured securely
- [ ] Rate limiting enabled

### Operations
- [ ] Access control configured
- [ ] Admin credentials secured
- [ ] API keys rotated
- [ ] Logs encrypted at rest
- [ ] Audit logging enabled
- [ ] Incident response plan ready

---

## Performance Optimization

- [ ] Database queries optimized
- [ ] Caching strategy implemented
- [ ] Image optimization enabled
- [ ] Code splitting implemented
- [ ] CSS minification enabled
- [ ] JavaScript minification enabled
- [ ] Lazy loading enabled
- [ ] CDN configured (if applicable)

---

## User Communication

- [ ] Release announcement prepared
- [ ] Known issues documented
- [ ] Support contact information available
- [ ] Feedback mechanism set up
- [ ] Analytics tracking configured
- [ ] User guide updated

---

## Sign-Off

- [ ] Project Manager Approval: _________________ Date: _______
- [ ] Backend Lead Approval: _________________ Date: _______
- [ ] Frontend Lead Approval: _________________ Date: _______
- [ ] DevOps/Infrastructure Lead: _________________ Date: _______
- [ ] QA Lead Approval: _________________ Date: _______

---

## Post-Launch Tasks (First Week)

- [ ] Monitor error rates
- [ ] Review user feedback
- [ ] Check analytics
- [ ] Verify performance metrics
- [ ] Address any urgent issues
- [ ] Plan next improvements
- [ ] Document lessons learned

---

**Checklist Completed Date:** _______________
**Deployment Status:** ✅ Ready / ❌ Not Ready
**Comments:** _______________________________________________

---

*Last Updated: 2025-12-10*
*Phase: 10 (Deployment)*
