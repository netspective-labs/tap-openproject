# 🚀 Quick Start Guide - SDK Version

## Installation

```bash
cd /home/avinash/Projects/resource-surveillance/src/tap-openproject

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate.fish  # or: source .venv/bin/activate

# Install dependencies
pip install singer-sdk requests

# Or use Poetry
pip install poetry
poetry install
```

## Basic Usage

### 1. Discovery Mode
```bash
# Discover available streams and their schemas
python -m tap_openproject.tap --discover > catalog.json
```

### 2. Create Config
```bash
cat > config.json << EOF
{
  "api_key": "YOUR_OPENPROJECT_API_KEY",
  "base_url": "https://community.openproject.org/api/v3",
  "start_date": "2024-01-01T00:00:00Z"
}
EOF
```

### 3. Run Extraction
```bash
# Full sync
python -m tap_openproject.tap --config config.json --catalog catalog.json

# With state for incremental sync
python -m tap_openproject.tap \
  --config config.json \
  --catalog catalog.json \
  --state state.json > output.singer
```

## Meltano Usage

### Add to Meltano Project
```bash
# From local path
meltano add --custom extractor tap-openproject \
  --pip_url -e /home/avinash/Projects/resource-surveillance/src/tap-openproject

# From GitHub (after pushing)
meltano add extractor tap-openproject --variant surveilr
```

### Configure
```bash
meltano config tap-openproject set api_key YOUR_KEY
meltano config tap-openproject set base_url https://your-instance.openproject.com/api/v3
```

### Run
```bash
# Discovery
meltano invoke tap-openproject --discover

# With target
meltano run tap-openproject target-jsonl

# Incremental sync (automatic)
meltano run tap-openproject target-jsonl
```

## Testing & Validation

### Check Capabilities
```bash
python -m tap_openproject.tap --about --format=json
```

### Verify Catalog
```bash
python -m tap_openproject.tap --discover | jq '.streams[] | {name: .tap_stream_id, primary_key: .key_properties, replication_key: .replication_key}'
```

### Test Extraction (Limited)
```bash
python -m tap_openproject.tap --config config.json --catalog catalog.json | head -20
```

## Configuration Reference

| Setting | Required | Default | Description |
|---------|----------|---------|-------------|
| `api_key` | Yes | - | OpenProject API key |
| `base_url` | Yes | `https://community.openproject.org/api/v3` | API base URL |
| `timeout` | No | 30 | Request timeout (seconds) |
| `max_retries` | No | 3 | Max retry attempts |
| `start_date` | No | - | Filter for incremental sync |

## Available Streams

- **projects**: OpenProject projects with full metadata
  - Primary key: `id`
  - Replication key: `updatedAt`
  - Supports incremental sync: ✅

## Troubleshooting

### Import Error
```bash
# Ensure SDK is installed
pip install singer-sdk requests
```

### Authentication Error
```bash
# Test API key
curl -u "apikey:YOUR_KEY" https://community.openproject.org/api/v3/projects
```

### No Output
```bash
# Check logs (stderr)
python -m tap_openproject.tap --config config.json 2>&1 | grep -i error
```

## Development

### Run Tests
```bash
pytest tests/
```

### Format Code
```bash
pip install ruff
ruff format .
ruff check --fix .
```

### Update Schema
Edit `tap_openproject/streams.py` - the schema is defined inline using Singer SDK types.

## Files Reference

- `tap_openproject/tap.py` - Main Tap class
- `tap_openproject/streams.py` - Stream definitions
- `pyproject.toml` - Dependencies and metadata
- `meltano-hub.yml` - Hub submission definition

## More Info

- [Full Migration Guide](SDK_MIGRATION.md)
- [Compliance Report](COMPLIANCE_REPORT.md)
- [Meltano SDK Docs](https://sdk.meltano.com/)
- [OpenProject API](https://www.openproject.org/docs/api/)
