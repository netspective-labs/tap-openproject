# tap-open-project Usage Guide

This Singer tap for OpenProject now supports standard Singer CLI arguments.

## Installation

```bash
pip install -e .
```

This will install the `tap-open-project` command.

## Usage

### Discovery Mode

Output the catalog (available streams and their schemas):

```bash
tap-open-project --discover > catalog.json
```

### Sync Mode

#### Basic sync (uses default config.json or environment variables)

```bash
tap-open-project
```

#### Sync with specific config file

```bash
tap-open-project --config my-config.json
```

#### Sync with catalog (to select specific streams)

```bash
tap-open-project --config config.json --catalog catalog.json
```

#### Sync with state (for incremental syncs)

```bash
tap-open-project --config config.json --state state.json
```

#### Full sync with all options

```bash
tap-open-project --config config.json --catalog catalog.json --state state.json > output.json
```

## Configuration

Create a `config.json` file:

```json
{
  "api_key": "your-api-key-here",
  "base_url": "https://your-instance.openproject.com/api/v3",
  "timeout": 30,
  "max_retries": 3
}
```

Or use environment variables:
- `OPENPROJECT_API_KEY`
- `OPENPROJECT_BASE_URL`

## Catalog Format

The catalog defines which streams to sync. After running `--discover`, you can edit the catalog to select specific streams:

```json
{
  "streams": [
    {
      "tap_stream_id": "projects",
      "stream": "projects",
      "schema": {...},
      "key_properties": ["id"],
      "metadata": [
        {
          "breadcrumb": [],
          "metadata": {
            "selected": true,
            "inclusion": "available"
          }
        }
      ]
    }
  ]
}
```

Set `"selected": true` or `"selected": false` to control which streams are synced.

## State Format

State is used for incremental syncs:

```json
{
  "last_sync": "2026-01-07T10:30:00Z"
}
```

The tap will output a new state after each successful sync.

## Example Workflow

```bash
# 1. Discover available streams
tap-open-project --discover > catalog.json

# 2. Edit catalog.json to select desired streams (optional)

# 3. Run initial sync
tap-open-project --config config.json --catalog catalog.json > output.json 2> sync.log

# 4. Extract state for next run
tail -n 1 output.json > state.json

# 5. Run incremental sync
tap-open-project --config config.json --catalog catalog.json --state state.json > output2.json
```

## Using with Singer Targets

Pipe the output to any Singer target:

```bash
# To JSON files
tap-open-project --config config.json | target-json > output.json

# To CSV
tap-open-project --config config.json | target-csv

# To a database
tap-open-project --config config.json | target-postgres --config target-config.json
```
