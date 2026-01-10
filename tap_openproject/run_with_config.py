#!/usr/bin/env python3
"""
Singer tap for OpenProject - Main entry point with CLI argument handling.
"""
import argparse
import json
import logging
import os
import sys
import stat
from datetime import datetime, timezone
import singer
from tap_openproject.http_client import HttpClient
from tap_openproject.streams import ProjectStream

logger = logging.getLogger(__name__)

def check_file_permissions(file_path):
    """
    Check if config file has secure permissions (not world-readable).
    
    Args:
        file_path: Path to config file
        
    Returns:
        tuple: (is_secure, warning_message)
    """
    try:
        file_stat = os.stat(file_path)
        # Check if file is readable by others (octal 004)
        if file_stat.st_mode & stat.S_IROTH:
            return False, "Warning: config.json is world-readable. Run: chmod 600 config.json"
        # Check if file is readable by group (octal 040)
        if file_stat.st_mode & stat.S_IRGRP:
            return False, "Warning: config.json is group-readable. Run: chmod 600 config.json"
        return True, None
    except Exception as e:
        logger.warning(f"Could not check file permissions: {e}")
        return True, None  # Don't fail if we can't check

def load_config():
    """
    Load configuration from file or environment variables.
    
    Priority:
    1. Environment variables (OPENPROJECT_API_KEY, OPENPROJECT_BASE_URL)
    2. config.json file
    
    Returns:
        dict: Configuration dictionary
        
    Raises:
        ValueError: If configuration is invalid or missing
    """
    config = {}
    
    # Try environment variables first (more secure for production)
    if os.getenv('OPENPROJECT_API_KEY'):
        logger.info("Using configuration from environment variables")
        config['api_key'] = os.getenv('OPENPROJECT_API_KEY')
        config['base_url'] = os.getenv('OPENPROJECT_BASE_URL', 'https://community.openproject.org/api/v3')
        return config
    
    # Fall back to config file
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if not os.path.exists(config_path):
        raise ValueError(
            f"Error: config.json not found at {config_path}\n"
            "Please create config.json with your OpenProject credentials.\n"
            "See config.json.example for the template.\n"
            "Alternatively, set OPENPROJECT_API_KEY environment variable."
        )
    
    # Check file permissions for security
    is_secure, warning = check_file_permissions(config_path)
    if not is_secure:
        logger.warning(warning)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config.json: {e}")
    except Exception as e:
        raise ValueError(f"Failed to read config.json: {e}")
    
    return config


def load_config_file(config_path):
    """
    Load configuration from specified file path.
    
    Args:
        config_path: Path to config file
        
    Returns:
        dict: Configuration dictionary
    """
    if not os.path.exists(config_path):
        raise ValueError(f"Config file not found: {config_path}")
    
    # Check file permissions for security
    is_secure, warning = check_file_permissions(config_path)
    if not is_secure:
        logger.warning(warning)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {config_path}: {e}")
    except Exception as e:
        raise ValueError(f"Failed to read {config_path}: {e}")


def validate_config(config):
    """
    Validate configuration has required fields.
    
    Args:
        config: Configuration dictionary
        
    Raises:
        ValueError: If configuration is invalid
    """
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a dictionary")
    
    if 'api_key' not in config:
        raise ValueError("Missing required field 'api_key' in configuration")
    
    if not config['api_key'] or config['api_key'] == 'YOUR_API_KEY_HERE':
        raise ValueError("Please set your API key in config.json or OPENPROJECT_API_KEY environment variable")
    
    # Validate base_url if provided
    if 'base_url' in config:
        base_url = config['base_url']
        if not base_url.startswith('http://') and not base_url.startswith('https://'):
            raise ValueError(f"Invalid base_url: must start with http:// or https://")

def validate_config(config):
    """
    Validate configuration has required fields.
    
    Args:
        config: Configuration dictionary
        
    Raises:
        ValueError: If configuration is invalid
    """
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a dictionary")
    
    if 'api_key' not in config:
        raise ValueError("Missing required field 'api_key' in configuration")
    
    if not config['api_key'] or config['api_key'] == 'YOUR_API_KEY_HERE':
        raise ValueError("Please set your API key in config.json or OPENPROJECT_API_KEY environment variable")
    
    # Validate base_url if provided
    if 'base_url' in config:
        base_url = config['base_url']
        if not base_url.startswith('http://') and not base_url.startswith('https://'):
            raise ValueError(f"Invalid base_url: must start with http:// or https://")


def get_catalog():
    """
    Generate Singer catalog for discovery mode.
    
    Returns:
        dict: Singer catalog with available streams
    """
    # Load schema for projects stream
    schema_path = os.path.join(os.path.dirname(__file__), 'schemas/projects.json')
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


def do_sync(config, state, catalog):
    """
    Run sync mode to extract data.
    
    Args:
        config: Configuration dictionary
        state: State dictionary for incremental syncs
        catalog: Catalog dictionary with stream selection
    """
    # Validate configuration
    validate_config(config)
    
    # Initialize HTTP client
    client = HttpClient(
        base_url=config.get('base_url', 'https://community.openproject.org/api/v3'),
        api_key=config['api_key'],
        timeout=config.get('timeout', 30),
        max_retries=config.get('max_retries', 3)
    )
    
    try:
        # Determine which streams to sync
        selected_streams = []
        
        if catalog:
            # Use catalog to determine selected streams
            for stream_entry in catalog.get('streams', []):
                metadata = stream_entry.get('metadata', [])
                # Check if stream is selected in metadata
                is_selected = False
                for meta in metadata:
                    if meta.get('breadcrumb') == []:
                        is_selected = meta.get('metadata', {}).get('selected', False)
                        break
                
                if is_selected:
                    selected_streams.append(stream_entry['tap_stream_id'])
        else:
            # No catalog provided, sync all streams
            selected_streams = ['projects']
        
        # Sync projects stream if selected
        if 'projects' in selected_streams:
            stream = ProjectStream(client)
            
            # Load and emit schema
            schema_path = os.path.join(os.path.dirname(__file__), stream.schema)
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            singer.write_schema(stream.name, schema, ["id"])
            
            # Fetch and emit records
            projects = stream.get_records()
            logger.info(f"Successfully fetched {len(projects)} projects")
            
            for project in projects:
                singer.write_record(stream.name, project)
            
            # Emit state with current timestamp
            new_state = state.copy() if state else {}
            new_state['last_sync'] = datetime.now(timezone.utc).isoformat()
            singer.write_state(new_state)
            
            logger.info("Tap completed successfully")
    
    finally:
        client.close()


def parse_args():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Singer tap for OpenProject',
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
    
    return parser.parse_args()


def main():
    """
    Main entry point for the tap.
    """
    # Parse command line arguments
    args = parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr)  # Log to stderr, data to stdout
        ]
    )
    
    try:
        if args.discover:
            # Discovery mode
            logger.info("Running in discovery mode")
            do_discover()
        else:
            # Sync mode
            logger.info("Running in sync mode")
            
            # Load configuration
            if args.config:
                config = load_config_file(args.config)
            else:
                # Try default config or environment variables
                config = load_config()
            
            # Load state if provided
            state = {}
            if args.state:
                if os.path.exists(args.state):
                    with open(args.state, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                else:
                    logger.warning(f"State file not found: {args.state}")
            
            # Load catalog if provided
            catalog = None
            if args.catalog:
                if os.path.exists(args.catalog):
                    with open(args.catalog, 'r', encoding='utf-8') as f:
                        catalog = json.load(f)
                else:
                    raise ValueError(f"Catalog file not found: {args.catalog}")
            
            # Run sync
            do_sync(config, state, catalog)
    
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running tap: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()

