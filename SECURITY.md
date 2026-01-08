# Security & Production Readiness

## Security Issues Fixed

### 1. **Request Timeouts**
- ✅ Added 30-second default timeout to prevent hanging connections
- ✅ Configurable via `timeout` parameter
- **Impact**: Prevents resource exhaustion from slow/hanging requests

### 2. **Retry Logic & Circuit Breaking**
- ✅ Implemented automatic retry with exponential backoff
- ✅ Retries on transient errors (429, 500, 502, 503, 504)
- ✅ Configurable `max_retries` (default: 3)
- **Impact**: Improves reliability against transient failures

### 3. **Input Validation**
- ✅ URL scheme validation (only http/https allowed)
- ✅ Base URL structure validation
- ✅ API key validation (non-empty string)
- ✅ Endpoint path traversal prevention (`..` blocked)
- ✅ JSON response structure validation
- **Impact**: Prevents injection attacks and malformed inputs

### 4. **Secure Configuration Handling**
- ✅ Environment variable support (`OPENPROJECT_API_KEY`, `OPENPROJECT_BASE_URL`)
- ✅ File permission checks (warns if config.json is world-readable)
- ✅ Proper error messages without exposing secrets
- **Impact**: Prevents credential leakage

### 5. **Resource Management**
- ✅ Connection pooling with session reuse
- ✅ Proper cleanup in `__del__` and `finally` blocks
- ✅ Close sessions explicitly with `close()` method
- **Impact**: Prevents resource leaks and connection exhaustion

### 6. **Error Handling**
- ✅ Specific exception handling for different error types
- ✅ Proper logging without exposing sensitive data
- ✅ Graceful degradation with helpful error messages
- ✅ Exit codes for automation (0=success, 1=failure)
- **Impact**: Easier debugging and monitoring in production

### 7. **Logging**
- ✅ Structured logging with levels (INFO, WARNING, ERROR)
- ✅ Logs to stderr, data to stdout (Singer convention)
- ✅ No secrets in logs
- ✅ Request/response debugging info
- **Impact**: Production observability without security risks

### 8. **Content Type Validation**
- ✅ Verifies API responses are JSON
- ✅ Warns on unexpected content types
- **Impact**: Prevents parsing non-JSON responses

## Production Best Practices

### Configuration

**Recommended: Use Environment Variables**
```bash
export OPENPROJECT_API_KEY="your_key_here"
export OPENPROJECT_BASE_URL="https://your-instance.com/api/v3"
python run_with_config.py
```

**Alternative: Secure config.json**
```bash
# Create config with restricted permissions
touch config.json
chmod 600 config.json  # Owner read/write only
# Edit and add credentials
```

### File Permissions
```bash
# Verify config.json permissions
ls -la config.json
# Should show: -rw------- (600)

# If not, fix it:
chmod 600 config.json
```

### Deployment Checklist

- [ ] Use environment variables for secrets (never commit config.json)
- [ ] Set appropriate timeout values for your network
- [ ] Configure retry settings based on API rate limits
- [ ] Enable logging and monitor for errors
- [ ] Use HTTPS URLs only (enforced by code)
- [ ] Implement monitoring/alerting on tap failures
- [ ] Set up log rotation for long-running processes
- [ ] Test with production-like data volumes
- [ ] Document incident response procedures
- [ ] Regular API key rotation

### Monitoring

**Key Metrics to Monitor:**
- Request success/failure rate
- Response times
- Retry counts
- Number of records extracted
- API rate limit status

**Log Patterns to Alert On:**
- `HTTP error: 401` - Invalid credentials
- `HTTP error: 429` - Rate limit exceeded
- `Request timed out` - Network/performance issues
- `Connection error` - Network connectivity issues

### Rate Limiting

OpenProject may have rate limits. Consider:
- Adding delays between requests if processing many resources
- Implementing backoff when hitting rate limits
- Using pagination for large result sets

### Secrets Management

**Never:**
- ❌ Commit config.json with real credentials
- ❌ Log API keys
- ❌ Include credentials in error messages
- ❌ Share config files via insecure channels

**Always:**
- ✅ Use environment variables in production
- ✅ Rotate API keys regularly
- ✅ Use secret management systems (AWS Secrets Manager, HashiCorp Vault, etc.)
- ✅ Audit access to secrets
- ✅ Use different keys for dev/staging/prod

### Network Security

- Use HTTPS only (enforced by code)
- Consider using VPN or private networking for self-hosted instances
- Implement network timeouts appropriate for your infrastructure
- Use firewall rules to restrict outbound connections if needed

### Error Recovery

The tap implements automatic retry for transient errors:
- Network timeouts
- HTTP 429 (rate limit)
- HTTP 500/502/503/504 (server errors)

For permanent errors (401, 403, 404), the tap fails fast.

## Testing for Production

### Load Testing
```bash
# Test with multiple concurrent runs
for i in {1..10}; do
  python run_with_config.py &
done
wait
```

### Failure Testing
```bash
# Test with invalid credentials
OPENPROJECT_API_KEY="invalid" python run_with_config.py

# Test with unreachable server
OPENPROJECT_BASE_URL="https://unreachable.example.com/api/v3" python run_with_config.py

# Test timeout behavior
# (Requires network simulation tools like tc or toxiproxy)
```

### Security Testing
```bash
# Check file permissions
python -c "import os, stat; s = os.stat('config.json'); print(oct(s.st_mode)[-3:])"

# Verify no secrets in logs
python run_with_config.py 2>&1 | grep -i "api_key\|password\|secret"
# Should return nothing
```

## Remaining Considerations

### Future Enhancements

1. **Pagination**: Implement for large datasets (OpenProject API supports offset/pageSize)
2. **Incremental Sync**: Use state file to track last sync and fetch only new records
3. **Multiple Streams**: Add work packages, users, time entries, etc.
4. **Rate Limit Handling**: Explicit handling of `Retry-After` header
5. **Circuit Breaker**: Stop making requests after consecutive failures
6. **Metrics Export**: Prometheus/StatsD metrics for production monitoring
7. **Health Checks**: Endpoint to verify tap health
8. **Data Validation**: Schema validation for extracted records
9. **Compression**: Support gzip/deflate for large responses
10. **Caching**: Cache schema files and configuration

### Known Limitations

- No pagination implemented yet (may miss data if >100 projects)
- Single stream (projects) only
- No incremental sync (full sync each time)
- No built-in deduplication
- Basic error recovery (no circuit breaker)

## Compliance

### GDPR/Data Privacy
- API keys are personal data - handle accordingly
- Implement data retention policies
- Log only necessary information
- Provide data deletion capabilities

### Audit Trail
- All API requests are logged (without sensitive data)
- Failed authentication attempts logged
- Configuration changes should be tracked externally

## Support

For security issues, please report privately to the maintainers.
