# tap-openproject

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Singer Tap](https://img.shields.io/badge/singer-tap-blue)](https://www.singer.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A [Singer](https://www.singer.io/) tap for extracting data from [OpenProject](https://www.openproject.org/) API with [surveilr](https://github.com/surveilr/surveilr) integration support.

## Features

- ✅ Extract projects with full metadata (name, description, status, dates)
- ✅ API authentication with rate limiting and retry logic
- ✅ Singer protocol compliant (SCHEMA, RECORD, STATE messages)
- ✅ Configurable timeout and retry settings
- ✅ Support for both cloud and self-hosted OpenProject instances
- ✅ surveilr integration for automated data ingestion workflows

## Installation

### From GitHub

```bash
pip install git+https://github.com/surveilr/tap-openproject.git
```

### From Source

```bash
git clone https://github.com/surveilr/tap-openproject.git
cd tap-openproject
pip install -e .
```

## Quick Start

### 1. Create Configuration File

Create a `config.json` file with your OpenProject credentials:

```json
{
  "api_key": "your-openproject-api-key",
  "base_url": "https://your-instance.openproject.com/api/v3",
  "timeout": 30,
  "max_retries": 3
}
```

### 2. Run Discovery Mode

Discover available streams:

```bash
python -m tap_open_project.run_with_config --config config.json --discover > catalog.json
```

### 3. Run Sync Mode

Extract data:

```bash
python -m tap_open_project.run_with_config --config config.json --catalog catalog.json
```

## Configuration Options

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `api_key` | string | Yes | - | OpenProject API key |
| `base_url` | string | Yes | - | Base URL of OpenProject instance |
| `timeout` | integer | No | 30 | Request timeout in seconds |
| `max_retries` | integer | No | 3 | Maximum number of retry attempts |
| `start_date` | string | No | - | Filter projects updated after this date |

### Getting an API Key

1. Log into your OpenProject instance
2. Go to **My Account** → **Access tokens**
3. Click **+ API** to generate a new token
4. Copy the token and use it as `api_key` in your config

## Available Streams

### Projects

Extracts all projects from your OpenProject instance.

**Schema:**
- `id` (string) - Unique project identifier
- `name` (string) - Project name
- `identifier` (string) - Project key/identifier
- `description` (string) - Project description
- `public` (boolean) - Whether project is public
- `active` (boolean) - Whether project is active
- `status` (string) - Project status
- `statusExplanation` (string) - Status explanation
- `createdAt` (string) - Creation timestamp
- `updatedAt` (string) - Last update timestamp

**Key Properties:** `id`

## Usage with surveilr

This tap includes a surveilr-compatible wrapper for seamless integration:

### Using the Wrapper Script

```bash
# Place in your surveilr project
./openproject.surveilr[singer].py
```

### Configuration via .env File

```bash
# .env
OPENPROJECT_API_KEY=your-api-key-here
OPENPROJECT_BASE_URL=https://your-instance.openproject.com/api/v3
OPENPROJECT_TIMEOUT=30
OPENPROJECT_MAX_RETRIES=3
```

### Integration with surveilr

```bash
surveilr ingest files \
  --capex-stdin-key "start_date" \
  --capex-stdin-sql "SELECT date('now', '-30 days') as start_date" \
  ./openproject.surveilr[singer].py
```

The wrapper automatically:
- Creates an isolated virtual environment (`.tap-venv`)
- Installs required dependencies
- Manages configuration from `.env` files
- Outputs Singer-formatted JSON to stdout

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/surveilr/tap-openproject.git
cd tap-openproject

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e .
pip install pytest pytest-cov black flake8
```

### Run Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black tap_open_project/
flake8 tap_open_project/
```

## Project Structure

```
tap-openproject/
├── README.md
├── LICENSE
├── setup.py
├── setup.cfg
├── MANIFEST.in
├── .gitignore
├── tap_open_project/
│   ├── __init__.py
│   ├── http_client.py      # HTTP client with retry logic
│   ├── streams.py           # Stream definitions
│   ├── context.py           # Shared context
│   ├── run_with_config.py   # Entry point
│   └── schemas/
│       └── projects.json    # JSON schema for projects
├── tests/
│   └── test_projects_stream.py
└── examples/
    ├── config.json.example
    ├── .env.example
    └── openproject.surveilr[singer].py  # surveilr wrapper
```

## Singer Specification Compliance

This tap follows the [Singer specification](https://github.com/singer-io/getting-started/blob/master/docs/SPEC.md):

- ✅ Discovery mode (`--discover`)
- ✅ Schema messages
- ✅ Record messages
- ✅ State messages
- ✅ Catalog-based stream selection
- ✅ Metadata conventions

## Troubleshooting

### Authentication Errors (401)

- Verify your API key is correct
- Check that the API key hasn't expired
- Ensure the API key has sufficient permissions

### Connection Errors

- Verify the `base_url` is correct and includes `/api/v3`
- Check that your OpenProject instance is accessible
- Verify firewall/network settings

### Rate Limiting (429)

- The tap automatically retries with exponential backoff
- Adjust `max_retries` in config if needed
- Consider reducing concurrent requests

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues:** [GitHub Issues](https://github.com/surveilr/tap-openproject/issues)
- **OpenProject API Docs:** https://docs.openproject.org/api/
- **Singer Spec:** https://github.com/singer-io/getting-started/blob/master/docs/SPEC.md

## Related Projects

- [surveilr](https://github.com/surveilr/surveilr) - Resource surveillance and ingestion framework
- [Singer.io](https://www.singer.io/) - Open source ETL standard
- [OpenProject](https://www.openproject.org/) - Open source project management

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

---

Built with ❤️ for the Singer and surveilr communities
PYTHONPATH=singerio-surveilr-poc-github-tap .venv/bin/python singerio-surveilr-poc-github-tap/tap_open_project/tests/test_projects_stream.py
```

## API Documentation

- OpenProject API Docs: https://www.openproject.org/docs/api/
- API Introduction: https://www.openproject.org/docs/api/introduction/
- Endpoints Reference: https://www.openproject.org/docs/api/endpoints/

## License

See parent project license.
