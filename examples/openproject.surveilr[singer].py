#!/usr/bin/env python3
"""
OpenProject Singer Tap wrapper for surveilr integration.

This script integrates tap_open_project with surveilr's ingestion system by:
1. Reading credentials from .env file (secure)
2. Accepting dynamic dates via stdin (flexible)
3. Outputting Singer-formatted JSON to stdout (compatible)
4. Supporting standard Singer --discover mode
5. Self-managing virtual environment and dependencies

Usage with surveilr:
    # Using dynamic date
    surveilr ingest files \\
      --capex-stdin-key "start_date" \\
      --capex-stdin-sql "SELECT date('now', '-30 days') as start_date" \\
      ./singerio-surveilr-poc-github-tap/openproject.surveilr[singer].py

    # Using .env defaults
    surveilr ingest files ./singerio-surveilr-poc-github-tap/openproject.surveilr[singer].py
    
Standard Singer usage:
    # Discovery mode
    python openproject.surveilr[singer].py --discover > catalog.json
    
    # Sync mode with config
    python openproject.surveilr[singer].py --config config.json
"""

import sys
import os
import json
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# Script directory
script_dir = Path(__file__).parent
tap_dir = script_dir / "tap_open_project"

# Configure logging to stderr (surveilr reads stdout for data)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


# =============================================================================
# VIRTUAL ENVIRONMENT AND DEPENDENCY MANAGEMENT
# =============================================================================

def setup_virtual_environment() -> Path:
    """Setup or use existing virtual environment for tap dependencies"""
    venv_path = script_dir / ".tap-venv"
    
    if not venv_path.exists():
        logger.info("Creating virtual environment for OpenProject tap...")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], 
                         check=True, capture_output=True)
            logger.info("Virtual environment created successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create virtual environment: {e}")
            raise
    
    return venv_path


def get_venv_python(venv_path: Path) -> str:
    """Get the Python executable from the virtual environment"""
    if os.name == 'nt':  # Windows
        return str(venv_path / "Scripts" / "python")
    else:  # Unix/Linux/macOS
        return str(venv_path / "bin" / "python")


def install_dependencies(venv_path: Path):
    """Install required dependencies in the virtual environment"""
    python_cmd = get_venv_python(venv_path)
    pip_cmd = str(venv_path / ("Scripts" if os.name == 'nt' else "bin") / "pip")
    
    # Check if dependencies are already installed
    try:
        result = subprocess.run(
            [python_cmd, "-c", "import requests, singer; print('ok')"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and "ok" in result.stdout:
            logger.info("Dependencies already installed")
            return
    except:
        pass
    
    logger.info("Installing tap dependencies (requests, singer-python)...")
    try:
        # Upgrade pip first
        subprocess.run([pip_cmd, "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        # Install required dependencies
        subprocess.run([pip_cmd, "install", "requests", "singer-python"], 
                      check=True, capture_output=True)
        logger.info("Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        raise


def ensure_dependencies():
    """Ensure all dependencies are available"""
    # Check if we're already in the virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if in_venv:
        # Already in a venv, check if dependencies are installed
        try:
            import requests
            import singer
            logger.info("Running in virtual environment with dependencies available")
            return
        except ImportError:
            logger.error("Virtual environment is active but dependencies are missing")
            logger.error("Please install: pip install requests singer-python")
            sys.exit(1)
    
    # Not in a venv, need to re-execute in our managed venv
    venv_path = setup_virtual_environment()
    install_dependencies(venv_path)
    
    # Re-execute this script in the virtual environment
    python_cmd = get_venv_python(venv_path)
    logger.info(f"Re-executing in virtual environment: {venv_path}")
    
    try:
        result = subprocess.run(
            [python_cmd] + sys.argv,
            check=False
        )
        sys.exit(result.returncode)
    except Exception as e:
        logger.error(f"Failed to re-execute in virtual environment: {e}")
        sys.exit(1)


# Ensure dependencies before importing tap modules
ensure_dependencies()

# Now safe to import tap components (after dependencies are ensured)
sys.path.insert(0, str(script_dir))
from tap_open_project.http_client import HttpClient
from tap_open_project.streams import ProjectStream
import singer


def load_env_file():
    """Load .env file from script directory."""
    env_file = script_dir / ".env"
    if not env_file.exists():
        logger.warning(f".env file not found at {env_file}")
        return
    
    logger.info(f"Loading environment from {env_file}")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()


def get_stdin_date(args):
    """
    Get date from stdin if provided by surveilr via --capex-stdin-*.
    
    surveilr passes stdin data as the first command line argument when using:
    --capex-stdin-key "start_date" --capex-stdin-sql "SELECT ... as start_date"
    
    Args:
        args: Parsed arguments (to check for unknown args that might be stdin data)
    
    Returns:
        str or None: Date value from stdin, or None if not provided
    """
    # Check if there are extra arguments (surveilr stdin data)
    if hasattr(args, 'stdin_data') and args.stdin_data:
        try:
            stdin_data = args.stdin_data[0]
            data = json.loads(stdin_data) if stdin_data.startswith('{') else {"start_date": stdin_data}
            start_date = data.get('start_date')
            if start_date:
                logger.info(f"Using start_date from stdin: {start_date}")
                return start_date
        except Exception as e:
            logger.warning(f"Could not parse stdin date: {e}")
    return None


def get_config(args=None, config_file=None):
    """
    Load configuration with priority:
    1. Config file (if provided via --config)
    2. stdin date (from --capex-stdin-*)
    3. Environment variables
    4. Defaults
    
    Args:
        args: Parsed arguments
        config_file: Path to config file (if using --config)
    
    Returns:
        dict: Configuration dictionary
    """
    config = {}
    
    # If config file provided, load it
    if config_file:
        logger.info(f"Loading config from {config_file}")
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        # Load .env file for surveilr mode
        load_env_file()
        
        # Get credentials from environment
        api_key = os.getenv('OPENPROJECT_API_KEY')
        base_url = os.getenv('OPENPROJECT_BASE_URL', 'https://community.openproject.org/api/v3')
        
        if not api_key:
            logger.error("OPENPROJECT_API_KEY not found in environment or .env file")
            sys.exit(1)
        
        config = {
            'api_key': api_key,
            'base_url': base_url,
            'timeout': int(os.getenv('OPENPROJECT_TIMEOUT', '30')),
            'max_retries': int(os.getenv('OPENPROJECT_MAX_RETRIES', '3'))
        }
    
    # Get date with priority: stdin > env > config
    if args:
        start_date = get_stdin_date(args) or os.getenv('OPENPROJECT_START_DATE') or config.get('start_date')
    else:
        start_date = os.getenv('OPENPROJECT_START_DATE') or config.get('start_date')
    
    if start_date:
        logger.info(f"Using start_date: {start_date}")
        config['start_date'] = start_date
    else:
        logger.info("No start_date provided (will fetch all projects)")
    
    # Ensure defaults
    config.setdefault('base_url', 'https://community.openproject.org/api/v3')
    config.setdefault('timeout', 30)
    config.setdefault('max_retries', 3)
    
    return config


def get_catalog():
    """
    Generate Singer catalog for available streams.
    
    Returns:
        dict: Singer catalog with available streams
    """
    # Load schema for projects stream
    schema_path = tap_dir / 'schemas' / 'projects.json'
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    catalog = {
        "streams": [
            {
                "tap_stream_id": "projects",
                "stream": "projects",
                "schema": schema,
                "key_properties": ["id"],
                "metadata": [
                    {
                        "breadcrumb": [],
                        "metadata": {
                            "selected": True,
                            "inclusion": "available"
                        }
                    }
                ]
            }
        ]
    }
    
    return catalog


def do_discover():
    """
    Run discovery mode and output catalog to stdout.
    """
    catalog = get_catalog()
    json.dump(catalog, sys.stdout, indent=2)
    sys.stdout.write('\n')
    logger.info("Discovery mode completed")


def do_sync(args=None, config_file=None, state_file=None, catalog_file=None):
    """
    Execute the OpenProject tap and output Singer messages.
    
    Args:
        args: Parsed arguments (for surveilr stdin data)
        config_file: Path to config file (optional)
        state_file: Path to state file (optional)
        catalog_file: Path to catalog file (optional)
    """
    try:
        # Load configuration
        config = get_config(args, config_file)
        
        logger.info(f"Connecting to OpenProject at {config['base_url']}")
        
        # Load state if provided
        state = {}
        if state_file and os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            logger.info(f"Loaded state from {state_file}")
        
        # Load catalog if provided, otherwise use default catalog
        if catalog_file and os.path.exists(catalog_file):
            with open(catalog_file, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            logger.info(f"Loaded catalog from {catalog_file}")
        else:
            # Use default catalog (all streams selected)
            catalog = get_catalog()
            logger.info("Using default catalog (all streams selected)")
        
        # Check if projects stream is selected
        sync_projects = False
        for stream_entry in catalog.get('streams', []):
            if stream_entry['tap_stream_id'] == 'projects':
                metadata = stream_entry.get('metadata', [])
                for meta in metadata:
                    if meta.get('breadcrumb') == []:
                        sync_projects = meta.get('metadata', {}).get('selected', False)
                        break
        
        if not sync_projects:
            logger.info("Projects stream not selected in catalog, skipping")
            return
        
        # Initialize HTTP client
        client = HttpClient(
            base_url=config['base_url'],
            api_key=config['api_key'],
            timeout=config['timeout'],
            max_retries=config['max_retries']
        )
        
        # Initialize stream
        stream = ProjectStream(client)
        
        # Fetch projects
        projects = stream.get_records()
        logger.info(f"Retrieved {len(projects)} projects")
        
        # Load and emit schema
        schema_path = tap_dir / stream.schema
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        # Output Singer messages to stdout (surveilr will capture this)
        singer.write_schema(stream.name, schema, ["id"])
        
        # Emit records
        for project in projects:
            singer.write_record(stream.name, project)
        
        # Emit state
        new_state = state.copy() if state else {}
        new_state.update({
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "projects_count": len(projects)
        })
        singer.write_state(new_state)
        
        logger.info(f"Successfully emitted {len(projects)} project records")
        
        # Clean up
        client.close()
        
    except Exception as e:
        logger.error(f"Error running tap: {e}", exc_info=True)
        sys.exit(1)


def parse_args():
    """
    Parse command line arguments.
    Supports both Singer standard args and surveilr stdin data.
    """
    parser = argparse.ArgumentParser(
        description='OpenProject Singer Tap (surveilr-compatible)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--discover',
        action='store_true',
        help='Run in discovery mode to output catalog'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to config file (JSON)'
    )
    
    parser.add_argument(
        '--state',
        type=str,
        help='Path to state file (JSON) for incremental syncs'
    )
    
    parser.add_argument(
        '--catalog',
        type=str,
        help='Path to catalog file (JSON) to specify which streams to sync'
    )
    
    # Capture any unknown args for surveilr stdin data
    parser.add_argument(
        'stdin_data',
        nargs='*',
        help='stdin data from surveilr (internal use)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    if args.discover:
        # Discovery mode
        logger.info("Running in discovery mode")
        do_discover()
    else:
        # Sync mode (standard Singer or surveilr)
        logger.info("Running in sync mode")
        do_sync(
            args=args,
            config_file=args.config,
            state_file=args.state,
            catalog_file=args.catalog
        )


if __name__ == "__main__":
    main()
