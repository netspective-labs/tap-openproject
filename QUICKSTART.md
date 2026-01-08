# Quick Reference: Testing tap_open_project

## TL;DR - Test in 5 Minutes

### 1. Get Free OpenProject Account
Visit: https://community.openproject.org/register

### 2. Get Your API Key
1. Log in → Click avatar → "My account"
2. Left sidebar → "Access tokens"
3. Click "Generate" → Copy the key

### 3. Create config.json
```bash
cd singerio-surveilr-poc-github-tap/tap_open_project
cat > config.json << 'EOF'
{
  "base_url": "https://community.openproject.org/api/v3",
  "api_key": "PASTE_YOUR_KEY_HERE"
}
EOF
```

### 4. Run the Tap
```bash
cd /path/to/surveilr
PYTHONPATH=singerio-surveilr-poc-github-tap .venv/bin/python singerio-surveilr-poc-github-tap/tap_open_project/run_with_config.py
```

## Expected Output

```json
{"type": "SCHEMA", "stream": "projects", ...}
{"type": "RECORD", "stream": "projects", "record": {"id": "...", "name": "...", ...}}
...
{"type": "STATE", "value": {"last_sync": "..."}}
```

## Quick Test with curl

```bash
# Test API access (replace YOUR_KEY)
curl -u apikey:YOUR_KEY https://community.openproject.org/api/v3/projects
```

## File Structure

```
tap_open_project/
├── config.json              # Your credentials (create this)
├── config.json.example      # Template
├── run_with_config.py       # Main script to test with real API
├── demo.py                  # Demo with mock data
├── http_client.py           # Handles OpenProject API calls
├── streams.py               # Defines data streams
├── schemas/projects.json    # JSON schema for projects
├── TESTING.md               # Full testing guide
└── README.md                # Main documentation
```

## Common Issues

**401 Unauthorized**
- Check API key is correct
- Username must be "apikey" (not your login name)

**No projects returned**
- OpenProject Community has public projects
- Check your account has project access

**Module not found**
- Set PYTHONPATH=singerio-surveilr-poc-github-tap
- Run from surveilr root directory

## Authentication Details

OpenProject uses Basic Authentication:
- Username: `apikey` (literal string)
- Password: Your API key

In Python:
```python
from requests.auth import HTTPBasicAuth
auth = HTTPBasicAuth('apikey', 'your_key_here')
```

## For More Details

See [TESTING.md](./TESTING.md) for comprehensive guide.
