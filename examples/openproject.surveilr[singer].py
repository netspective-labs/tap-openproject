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
tap_dir = script_dir / "tap_openproject"

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
        logger.info("This may take a few minutes on first run...")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], 
                         check=True)
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
    
    # Check if tap-openproject (SDK version) is already installed
    try:
        result = subprocess.run(
            [python_cmd, "-c", "import tap_openproject; from tap_openproject.tap import TapOpenProject; print('ok')"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and "ok" in result.stdout:
            logger.info("SDK-based tap-openproject already installed")
            return
    except:
        pass
    
    logger.info("Installing SDK-based tap-openproject...")
    try:
        # Upgrade pip first
        logger.info("Upgrading pip...")
        subprocess.run([pip_cmd, "install", "--upgrade", "pip"], 
                      check=True)
        
        # Install from GitHub feature branch first
        github_repo = os.getenv('TAP_OPENPROJECT_REPO', 
                                'git+https://github.com/avinashkurup/tap-openproject.git@feature/sdk-migration')
        
        try:
            logger.info(f"Installing tap-openproject (SDK version) from: {github_repo}")
            result = subprocess.run([pip_cmd, "install", github_repo], 
                          check=True, timeout=180)
            logger.info("Successfully installed SDK-based tap-openproject from GitHub")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.warning(f"GitHub installation failed: {e}")
            logger.info("Falling back to local installation...")
            
            # Fall back to local installation (parent directory of script)
            local_tap_dir = script_dir.parent / "tap-openproject"
            if local_tap_dir.exists() and (local_tap_dir / "pyproject.toml").exists():
                logger.info(f"Installing from local directory: {local_tap_dir}")
                subprocess.run([pip_cmd, "install", "-e", str(local_tap_dir)], 
                              check=True)
                logger.info("Successfully installed from local directory")
            else:
                raise Exception(f"Local tap directory not found or missing pyproject.toml: {local_tap_dir}")
        
        logger.info("SDK dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        raise


def ensure_dependencies():
    """Ensure all dependencies are available"""
    # First, always try to import the tap
    try:
        from tap_openproject.tap import TapOpenProject
        logger.info("SDK tap-openproject is already available")
        return
    except ImportError:
        pass
    
    # Check if we're in the tap-openproject source directory
    # (parent dir has pyproject.toml with tap-openproject)
    in_tap_project = False
    parent_pyproject = script_dir.parent / "pyproject.toml"
    if parent_pyproject.exists():
        try:
            with open(parent_pyproject) as f:
                content = f.read()
                if 'name = "tap-openproject"' in content:
                    in_tap_project = True
        except:
            pass
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if in_venv and not in_tap_project:
        # In a managed venv (not source project), tap should have been installed
        logger.error("Virtual environment is active but SDK tap-openproject is missing")
        logger.error("This shouldn't happen - installation may have failed")
        sys.exit(1)
    
    # Not in a venv (or in tap project without tap), need to set up managed venv
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

# Now safe to import tap components (SDK-based)
from tap_openproject.tap import TapOpenProject
import io
import json


def normalize_base_url(base_url: str) -> str:
    """Ensure base URL ends with /api/v3 for OpenProject API."""
    base_url = base_url.rstrip('/')
    if not base_url.endswith('/api/v3'):
        base_url = f"{base_url}/api/v3"
    return base_url


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
        
        # Validate API key format (basic check)
        if len(api_key) < 20:
            logger.warning("API key seems too short - may be invalid")
        
        # Normalize base URL to ensure /api/v3 suffix
        base_url = normalize_base_url(base_url)
        
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
    schema = load_schema()
    
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
    """Run discovery mode using SDK tap and output catalog to stdout."""
    # Create a minimal config (just for discovery, doesn't need credentials)
    config = {
        "api_key": "dummy",  # Not used for discovery
        "base_url": "https://community.openproject.org/api/v3"
    }
    
    # Create tap instance (SDK instantiation without parse_args)
    tap = TapOpenProject(config=config)
    
    # Run discovery
    catalog = tap.catalog_dict
    json.dump(catalog, sys.stdout, indent=2)
    sys.stdout.write('\n')
    logger.info("Discovery mode completed using SDK tap")


def do_sync(args=None, config_file=None, state_file=None, catalog_file=None):
    """
    Execute the OpenProject tap using SDK and output Singer messages.
    
    Args:
        args: Parsed arguments (for surveilr stdin data)
        config_file: Path to config file (optional)
        state_file: Path to state file (optional)
        catalog_file: Path to catalog file (optional)
    """
    try:
        # Load configuration
        config = get_config(args, config_file)
        
        logger.info(f"Connecting to OpenProject at {config['base_url']} using SDK tap")
        
        # Create tap instance with config
        tap = TapOpenProject(config=config, parse_args=False, state=state_file, catalog=catalog_file)
        
        # Capture stdout to get Singer messages
        tap.sync_all()
        
        logger.info("SDK tap sync completed successfully")
        
    except Exception as e:
        logger.error(f"Error running SDK tap: {e}", exc_info=True)
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
