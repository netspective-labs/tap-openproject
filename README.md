# tap-openproject

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Singer SDK](https://img.shields.io/badge/Meltano-SDK-blue)](https://sdk.meltano.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A [Singer](https://www.singer.io/) tap for extracting data from [OpenProject](https://www.openproject.org/) API. Built with the [Meltano Singer SDK](https://sdk.meltano.com/).

## Features

- ✅ **Meltano SDK-based** - Modern Singer tap implementation
- ✅ **Incremental sync** - Efficient data extraction using `updatedAt` timestamp
- ✅ **Stream Maps** - Built-in inline transformation support
- ✅ **Automatic pagination** - Handles large datasets seamlessly
- ✅ **Schema validation** - Full JSON Schema with type checking
- ✅ **Rate limiting & retries** - Built-in resilience for API calls
- ✅ **Cloud & self-hosted** - Works with any OpenProject instance

## Installation

### Prerequisites

- Python 3.8 or higher
- pip or Poetry

### Install from Source

```bash
git clone https://github.com/surveilr/tap-openproject.git
cd tap-openproject

# Option 1: Using pip
pip install -e .

# Option 2: Using Poetry
pip install poetry
poetry install
```

## Quick Start

### 1. Create Configuration

Create a `config.json` file:

```json
{
  "api_key": "your-openproject-api-key",
  "base_url": "https://your-instance.openproject.com/api/v3",
  "start_date": "2024-01-01T00:00:00Z"
}
```

### 2. Discover Available Streams

```bash
tap-openproject --config config.json --discover > catalog.json
```

### 3. Run Extraction

```bash
tap-openproject --config config.json --catalog catalog.json
```

### 4. Incremental Sync

```bash
# State is automatically managed
tap-openproject --config config.json --catalog catalog.json --state state.json > output.singer
```

See [QUICKSTART.md](QUICKSTART.md) for more details.

### Getting Your API Key

1. Log into your OpenProject instance
2. Click your avatar → **My Account**
3. Navigate to **Access tokens** in the sidebar
4. Click **+ API** to generate a new token
5. Copy the token immediately (you won't see it again)
6. Use it as `api_key` in your configuration

## Configuration Options

## Configuration Options

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `api_key` | string | Yes | - | OpenProject API key |
| `base_url` | string | Yes | - | Base URL of OpenProject instance API (include `/api/v3`) |
| `timeout` | integer | No | 30 | HTTP request timeout in seconds |
| `max_retries` | integer | No | 3 | Maximum retry attempts for failed requests |
| `start_date` | datetime | No | - | ISO 8601 date for incremental sync starting point |
| `user_agent` | string | No | `tap-openproject/0.2.0` | User-Agent header value |

## Available Streams

### Projects

Extracts projects from your OpenProject instance.

**Primary Key:** `id`  
**Replication Key:** `updatedAt` (supports incremental sync)

**Schema Fields:**
- `id` (integer) - Unique project identifier
- `name` (string) - Project name
- `identifier` (string) - Project key
- `description` (object) - Project description with formatting (raw, html)
- `active` (boolean) - Whether project is active
- `public` (boolean) - Whether project is public
- `status` (string) - Project status
- `statusExplanation` (object) - Status details
- `createdAt` (datetime) - Creation timestamp
- `updatedAt` (datetime) - Last update timestamp (used for incremental sync)
- `_links` (object) - HAL hypermedia links
- `_type` (string) - Resource type

## Usage with Meltano

This tap is designed to work seamlessly with [Meltano](https://meltano.com/):

```bash
# Add the tap to your Meltano project
meltano add extractor tap-openproject --custom

# Configure
meltano config tap-openproject set api_key YOUR_API_KEY
meltano config tap-openproject set base_url https://your-instance.openproject.com/api/v3

# Run extraction
meltano run tap-openproject target-jsonl
```

### Configuration in meltano.yml

```yaml
plugins:
  extractors:
    - name: tap-openproject
      pip_url: -e /path/to/tap-openproject
      config:
        api_key: ${OPENPROJECT_API_KEY}
        base_url: https://your-instance.openproject.com/api/v3
        start_date: '2024-01-01T00:00:00Z'
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/surveilr/tap-openproject.git
cd tap-openproject

# Using Poetry (recommended)
poetry install
poetry shell

# Or using pip
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### Run Tests

```bash
poetry run pytest tests/ -v

# With coverage
poetry run pytest tests/ --cov=tap_openproject
```

### Code Quality

```bash
# Linting
poetry run ruff check .

# Formatting
poetry run ruff format .
```

## Project Structure

```
tap-openproject/
├── pyproject.toml           # Poetry dependencies & metadata
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── QUICKSTART.md
├── meltano-hub.yml          # Meltano Hub plugin definition
├── tap_openproject/
│   ├── __init__.py
│   ├── tap.py               # Main Tap class with SDK
│   ├── streams.py           # Stream definitions (SDK-based)
│   └── schemas/
│       └── projects.json    # JSON Schema for projects stream
├── tests/
│   └── test_projects_stream.py
└── examples/
    ├── config.example.json
    └── openproject.surveilr[singer].py
```

## SDK Capabilities

Built with Meltano Singer SDK, this tap supports:

- ✅ **catalog** - Stream and property selection
- ✅ **discover** - Automatic schema discovery
- ✅ **state** - Incremental replication with bookmarks
- ✅ **about** - Plugin metadata output
- ✅ **stream-maps** - Inline data transformation
- ✅ **schema-flattening** - Automatic nested object flattening
- ✅ **batch** - Efficient batch processing

```bash
# Check capabilities
tap-openproject --about --format=json
```

## Troubleshooting

### Authentication Errors (401)

- Verify your API key is correct and hasn't expired
- Ensure the API key has sufficient permissions
- Check that you're using Basic Auth format (handled automatically)

### Connection Errors

- Verify `base_url` includes `/api/v3` at the end
- Check that your OpenProject instance is accessible
- Verify network/firewall settings allow outbound HTTPS

### Rate Limiting (429)

- The SDK automatically retries with exponential backoff
- Adjust `max_retries` if needed
- Contact your OpenProject admin if limits persist

## Resources

- [OpenProject API Documentation](https://www.openproject.org/docs/api/)
- [Meltano Singer SDK](https://sdk.meltano.com/)
- [Singer Specification](https://hub.meltano.com/singer/spec)
- [Meltano Hub](https://hub.meltano.com/)

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

Built with the [Meltano Singer SDK](https://sdk.meltano.com/)
