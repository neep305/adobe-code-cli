# Troubleshooting Guide - Adobe AEP Web UI

## Signup/Registration Issues

### Quick Diagnostic Steps

1. **Check if backend is running:**
   ```bash
   # Windows
   aep web status
   
   # Or check directly
   curl http://localhost:8000/health
   ```
   
   **Expected:** `{"status":"healthy","app":"Adobe AEP Web UI","version":"0.1.0"}`

2. **Use the diagnostic tool:**
   ```bash
   # Open diagnostic page
   start web/signup_diagnostic.html
   
   # Or access via frontend (if running)
   start http://localhost:3000/diagnostic.html
   ```
   
   The diagnostic tool will automatically test:
   - Backend health check
   - CORS configuration
   - Registration API
   - Login functionality
   - Environment information

3. **Check browser console:**
   - Open DevTools (F12)
   - Go to Console tab
   - Look for error messages starting with `[API]`, `[Auth]`, or `[Register]`
   - Note any red error messages

### Common Errors and Solutions

#### Error: "Cannot connect to server"
**Symptoms:**
- Registration form submits but fails immediately
- Console shows: "Network error - backend may not be reachable"
- Browser shows: "Cannot connect to backend"

**Solutions:**
1. Check if backend is running:
   ```bash
   aep web status
   ```

2. If not running, start it:
   ```bash
   aep web start
   ```

3. If backend is running but still can't connect, check port 8000:
   ```powershell
   netstat -ano | Select-String "8000"
   ```

4. Verify backend URL in browser console:
   - Open http://localhost:3000/register
   - Open DevTools Console
   - Check for logs showing API URL (should be http://localhost:8000)

#### Error: "This email is already registered"
**Symptoms:**
- Registration fails with message about duplicate email
- Backend is working correctly

**Solutions:**
1. Use a different email address
2. Or login with existing credentials
3. To reset test database:
   ```bash
   aep web stop
   docker volume rm aep-web-postgres-data
   aep web start
   ```

#### Error: "Browser security error (CORS)"
**Symptoms:**
- Console shows CORS-related errors
- Message contains "Access-Control-Allow-Origin"
- Registration request fails before reaching backend

**Solutions:**
1. Check CORS configuration in backend:
   ```bash
   # Check backend config
   docker exec aep-web-backend cat /app/app/config.py | grep -A 2 "cors_origins"
   ```

2. Verify frontend is running on correct port (3000):
   ```bash
   aep web status
   ```

3. If using custom ports, update CORS in `web/backend/app/config.py`:
   ```python
   cors_origins: list[str] = Field(
       default=["http://localhost:3000", "http://localhost:YOUR_PORT"],
       ...
   )
   ```

4. Restart backend after config changes:
   ```bash
   aep web stop
   aep web start
   ```

#### Error: Password validation fails
**Symptoms:**
- Form shows "Password must be at least 8 characters"
- Passwords don't match error

**Solutions:**
1. Ensure password is at least 8 characters
2. Ensure both password fields match exactly
3. Check for extra spaces in password fields

#### Frontend not loading or showing blank page
**Symptoms:**
- http://localhost:3000 doesn't load
- White or blank page
- "This site can't be reached" error

**Solutions:**
1. Check if frontend container is running:
   ```bash
   aep web status
   ```

2. Check frontend logs:
   ```bash
   aep web logs frontend
   ```

3. Rebuild frontend if needed:
   ```bash
   aep web stop
   docker-compose -f web/docker-compose.yml build frontend
   aep web start
   ```

### Advanced Debugging

#### Enable verbose API logging

The frontend now logs all API requests to the browser console. To see them:

1. Open http://localhost:3000/register
2. Open DevTools (F12) → Console tab
3. Try registering - you'll see logs like:
   ```
   [API] POST /api/auth/register
   [Auth] Starting registration for: test@example.com
   [API] Response: 200 OK
   [Auth] Registration successful, token received
   [Auth] Fetching user data...
   [API] GET /api/auth/me
   [Auth] User data loaded, redirecting to /batches
   ```

#### Test registration directly with curl

```bash
# Test registration API
curl -X POST http://localhost:8000/api/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"test@example.com","password":"testpass123","name":"Test User"}'

# Expected response:
# {"access_token":"eyJhbGci...","token_type":"bearer"}
```

#### Check Docker container health

```bash
# Check all containers
docker ps -a

# Expected: 4 containers running (backend, frontend, postgres, redis)

# Check specific container logs
docker logs aep-web-backend --tail 50
docker logs aep-web-frontend --tail 50
docker logs aep-web-postgres --tail 20
docker logs aep-web-redis --tail 20
```

#### Verify database connection

```bash
# Connect to database
docker exec -it aep-web-postgres psql -U aep_user -d aep_web

# Check if users table exists
\dt

# Check existing users
SELECT id, email, name, created_at FROM users;

# Exit
\q
```

#### Reset everything

If all else fails, clean slate:

```bash
# Stop all services
aep web stop

# Remove all containers and volumes
docker-compose -f web/docker-compose.yml down -v

# Remove images
docker rmi aep-web-backend aep-web-frontend

# Rebuild and start
docker-compose -f web/docker-compose.yml build --no-cache
aep web start
```

## Backend API Issues

### Health check fails

**Check if backend is accessible:**
```bash
curl http://localhost:8000/health
```

**If connection refused:**
```bash
# Check if container is running
docker ps | grep aep-web-backend

# Check backend logs
docker logs aep-web-backend --tail 50

# Look for:
# - Port binding errors
# - Database connection errors
# - Import errors
```

### Database connection errors

**Symptoms:**
- Backend logs show "connection refused" or "password authentication failed"
- Registration fails with 500 error

**Solutions:**
1. Check if postgres container is running:
   ```bash
   docker ps | grep aep-web-postgres
   ```

2. Verify database credentials in `web/docker-compose.yml` match

3. Wait for postgres to fully start (takes ~10 seconds):
   ```bash
   docker logs aep-web-postgres | grep "ready to accept connections"
   ```

## Getting Help

If you've tried all the above and still have issues:

1. **Collect diagnostic information:**
   ```bash
   # Save all logs
   aep web logs > web-logs.txt
   
   # Save container status
   docker ps -a > docker-status.txt
   
   # Save environment info
   docker-compose -f web/docker-compose.yml config > config.txt
   ```

2. **Run the diagnostic tool** and screenshot results:
   ```bash
   start web/signup_diagnostic.html
   ```

3. **Check browser console** and screenshot any errors

4. **Include in bug report:**
   - Output of `aep web status`
   - Browser console errors
   - Diagnostic tool results
   - Relevant log snippets
   - What you were trying to do
   - What happened instead

## Known Issues

### Issue: Password hashing incompatibility
**Status:** FIXED in latest version
**Details:** Earlier versions used incompatible bcrypt library. Now uses `bcrypt==4.0.1`
**Solution:** Update to latest version or rebuild containers

### Issue: Port 8000 already in use
**Symptoms:** Backend won't start, "address already in use" error
**Solution:** 
```powershell
# Find process using port 8000
netstat -ano | Select-String "8000"

# Stop the process
Stop-Process -Id <PID>

# Or use different port (requires docker-compose.yml changes)
```

### Issue: Frontend can't find API URL
**Symptoms:** All API calls fail, console shows requests to wrong URL
**Solution:** Verify `NEXT_PUBLIC_API_URL` is set in docker-compose.yml:
```yaml
frontend:
  environment:
    NEXT_PUBLIC_API_URL: http://localhost:8000
```

## Development Tips

### Hot reload not working

**Frontend changes not reflecting:**
```bash
# Check if volume mounts are correct
docker inspect aep-web-frontend | grep -A 10 Mounts

# Restart with fresh build
aep web stop
docker-compose -f web/docker-compose.yml up -d --build frontend
```

**Backend changes not reflecting:**
```bash
# Backend uses uvicorn with --reload, but requires restart for dependency changes
aep web logs backend

# If not seeing reload messages, restart:
docker restart aep-web-backend
```

### Testing with different users

```python
# In Python console or test script
import requests

# Register multiple users
for i in range(5):
    resp = requests.post(
        "http://localhost:8000/api/auth/register",
        json={
            "email": f"testuser{i}@example.com",
            "password": "testpass123",
            "name": f"Test User {i}"
        }
    )
    print(f"User {i}: {resp.status_code}")
```

### Debugging authentication issues

Check JWT token structure:
```bash
# Get token from login/register
TOKEN="eyJhbGci..."

# Decode (without verification)
echo $TOKEN | cut -d'.' -f2 | base64 -d

# Or use online tool: https://jwt.io
```
