# Testing tap_open_project with a Real OpenProject Account

This guide explains how to test the Singer tap with an actual OpenProject account.

## Prerequisites

1. An OpenProject account (you can use the free community instance or your own)
2. Python 3.7+ with the tap installed
3. Your OpenProject API key

## Step 1: Get Your API Key

### Option A: Using OpenProject Community Instance (Free)

1. Go to https://community.openproject.org/
2. Create a free account or log in
3. Navigate to your account page: Click your avatar → "My account"
4. In the left sidebar, click "Access tokens"
5. Click "Generate" to create a new API key
6. Copy the generated API key (you won't be able to see it again)

### Option B: Using Your Own OpenProject Instance

1. Log in to your OpenProject instance
2. Click your avatar in the top right → "My account"
3. Navigate to "Access tokens" in the left sidebar
4. Click "+ API" to generate a new API token
5. Copy the generated API key

## Step 2: Configure the Tap

Create a `config.json` file in the tap_open_project directory:

```json
{
  "base_url": "https://community.openproject.org/api/v3",
  "api_key": "YOUR_API_KEY_HERE"
}
```

Replace:
- `base_url`: Your OpenProject instance URL + `/api/v3`
  - Community: `https://community.openproject.org/api/v3`
  - Self-hosted: `https://your-domain.com/api/v3`
- `api_key`: The API key you copied in Step 1

## Step 3: Update the Code to Load Config

Update `streams.py` to load configuration from the config file:

```python
import json
import singer
from tap_open_project.http_client import HttpClient

class ProjectStream:
    name = "projects"
    schema = "schemas/projects.json"

    def __init__(self, client=None):
        self.client = client or HttpClient()

    def get_records(self):
        data = self.client.get("projects")
        return data.get("_embedded", {}).get("elements", [])

if __name__ == "__main__":
    # Load config
    with open('config.json') as f:
        config = json.load(f)
    
    # Initialize client with config
    client = HttpClient(
        base_url=config['base_url'],
        api_key=config['api_key']
    )
    stream = ProjectStream(client)
    projects = stream.get_records()
    
    # Emit Singer schema message
    with open('schemas/projects.json') as f:
        schema = json.load(f)
    singer.write_schema(stream.name, schema, ["id"])
    
    # Emit Singer record messages
    for project in projects:
        singer.write_record(stream.name, project)
```

## Step 4: Test the API Connection

First, test the API connection with a simple curl command:

```bash
# Test with curl (replace YOUR_API_KEY with your actual key)
curl -u apikey:YOUR_API_KEY https://community.openproject.org/api/v3/projects
```

If successful, you should see JSON output with projects.

## Step 5: Run the Tap

```bash
# Set PYTHONPATH and run
cd /path/to/surveilr
PYTHONPATH=singerio-surveilr-poc-github-tap .venv/bin/python singerio-surveilr-poc-github-tap/tap_open_project/streams.py
```

## Step 6: Verify Output

You should see Singer-formatted JSON output:

```json
{"type": "SCHEMA", "stream": "projects", "schema": {...}, "key_properties": ["id"]}
{"type": "RECORD", "stream": "projects", "record": {...}}
{"type": "RECORD", "stream": "projects", "record": {...}}
```

## OpenProject API Details

### Authentication Methods

The tap uses **API Key through Basic Auth** (recommended):
- Username: `apikey` (literal string, NOT your login name)
- Password: Your API key

### Available Endpoints

- **Projects**: `/api/v3/projects` - List all projects
- **Work Packages**: `/api/v3/work_packages` - List work packages
- **Users**: `/api/v3/users` - List users
- **Time Entries**: `/api/v3/time_entries` - List time entries

Full API documentation: https://www.openproject.org/docs/api/endpoints/

### Response Format

OpenProject API returns HAL+JSON format with embedded resources:

```json
{
  "_embedded": {
    "elements": [
      {"id": 1, "name": "Project 1", ...},
      {"id": 2, "name": "Project 2", ...}
    ]
  },
  "total": 2,
  "count": 2
}
```

Note: The tap extracts data from `_embedded.elements` path.

## Troubleshooting

### 401 Unauthorized
- Verify your API key is correct
- Check that you're using "apikey" as the username (not your login)
- Ensure the API key hasn't been revoked

### 403 Forbidden
- Check that your user account has permission to view projects
- Verify you're accessing the correct OpenProject instance

### Connection Error
- Verify the base_url is correct and includes `/api/v3`
- Check your network connection
- For self-hosted instances, ensure the API is accessible

### Empty Results
- Your account may not have access to any projects
- Try the community instance which has public projects

## Next Steps

1. Add more streams (work packages, users, etc.)
2. Implement pagination for large datasets
3. Add incremental sync with state management
4. Add filtering options
5. Package as a proper Singer tap with CLI arguments
