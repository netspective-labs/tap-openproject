"""OpenProject tap class."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from singer_sdk import Stream, Tap
from singer_sdk import typing as th

from tap_openproject import streams

logger = logging.getLogger(__name__)


class TapOpenProject(Tap):
    """Singer tap for OpenProject API.
    
    Built with the Meltano Singer SDK.
    """

    name = "tap-openproject"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType,
            required=True,
            secret=True,
            description="OpenProject API key from My Account → Access tokens",
        ),
        th.Property(
            "base_url",
            th.StringType,
            required=True,
            default="https://community.openproject.org/api/v3",
            description="Base URL of your OpenProject instance (e.g., https://instance.openproject.com/api/v3)",
        ),
        th.Property(
            "timeout",
            th.IntegerType,
            default=30,
            description="HTTP request timeout in seconds",
        ),
        th.Property(
            "max_retries",
            th.IntegerType,
            default=3,
            description="Maximum number of retry attempts for failed requests",
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            description="Filter projects updated after this date (ISO 8601 format)",
        ),
        th.Property(
            "user_agent",
            th.StringType,
            default="tap-openproject/0.3.0",
            description="User-Agent header for API requests",
        ),
        th.Property(
            "project_ids",
            th.ArrayType(th.IntegerType),
            description="List of project IDs to filter data extraction (optional, for per-project ingestion)",
        ),
        th.Property(
            "project_identifiers",
            th.ArrayType(th.StringType),
            description="List of project identifiers (slugs) to filter data extraction (optional, resolved to IDs internally)",
        ),
    ).to_dict()

    def __init__(self, config=None, parse_env_config=False, validate_config=True, **kwargs):
        # Pre-process config to resolve project_identifiers BEFORE parent init
        # This is necessary because the Singer SDK freezes config after init
        config = self._preprocess_config(config)

        super().__init__(config=config, parse_env_config=parse_env_config, validate_config=validate_config, **kwargs)

    def _preprocess_config(self, config):
        """Pre-process config to resolve project_identifiers before SDK initialization.

        The Singer SDK freezes config after __init__, so we must resolve identifiers first.
        """
        # If config is already a dict, resolve in place
        if config and isinstance(config, dict):
            if config.get("project_identifiers") and not config.get("project_ids"):
                self._resolve_project_identifiers(config)
            return config

        # If config is a file path or list of paths, read and merge them
        if config:
            config_paths = config if isinstance(config, list) else [config]
            merged_config = {}
            for config_path in config_paths:
                if isinstance(config_path, (str, Path)) and Path(config_path).exists():
                    with open(config_path) as f:
                        file_config = json.load(f)
                        merged_config.update(file_config)

            # Resolve identifiers if present
            if merged_config.get("project_identifiers") and not merged_config.get("project_ids"):
                self._resolve_project_identifiers(merged_config)

            return merged_config

        return config

    def _resolve_project_identifiers(self, config):
        """Resolve project identifiers to IDs using direct HTTP request.

        Fetches all projects (with pagination) and maps identifiers to IDs.
        Logs warnings for any identifiers that cannot be resolved.
        """
        import requests

        identifiers = config.get("project_identifiers", [])
        if not identifiers:
            return

        base_url = config.get("base_url", "").rstrip("/")
        api_key = config.get("api_key")
        if not base_url or not api_key:
            logger.warning(
                "Cannot resolve project_identifiers: missing base_url or api_key"
            )
            return

        headers = {"User-Agent": config.get("user_agent", "tap-openproject/0.3.0")}
        auth = ("apikey", api_key)  # Basic auth per OpenProject docs
        timeout = config.get("timeout", 30)

        # Fetch all projects with pagination
        id_map = {}
        offset = 1
        page_size = 100

        try:
            while True:
                url = f"{base_url}/projects"
                params = {"offset": offset, "pageSize": page_size}

                response = requests.get(
                    url, headers=headers, auth=auth, params=params, timeout=timeout
                )
                response.raise_for_status()
                data = response.json()

                # Extract projects from HAL response
                projects = data.get("_embedded", {}).get("elements", [])
                if not projects:
                    break

                for p in projects:
                    if p.get("identifier"):
                        id_map[p["identifier"]] = p["id"]

                # Check if there are more pages
                total = data.get("total", 0)
                if offset + len(projects) >= total:
                    break
                offset += page_size

            # Resolve identifiers to IDs
            resolved_ids = []
            missing = []
            for ident in identifiers:
                if ident in id_map:
                    resolved_ids.append(id_map[ident])
                else:
                    missing.append(ident)

            if missing:
                logger.warning(
                    f"Could not resolve project identifiers (not found): {missing}"
                )

            if resolved_ids:
                logger.info(
                    f"Resolved {len(resolved_ids)} project identifier(s) to IDs: "
                    f"{dict((k, v) for k, v in id_map.items() if k in identifiers)}"
                )
                existing_ids = config.get("project_ids") or []
                # Ensure all IDs are integers for consistent comparison
                all_ids = [int(id) for id in existing_ids] + [int(id) for id in resolved_ids]
                config["project_ids"] = list(set(all_ids))

        except requests.RequestException as e:
            logger.error(
                f"Failed to resolve project identifiers: {e}. "
                "Filtering by project_identifiers will not work."
            )

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams.

        Returns:
            A list of discovered streams.
        """
        return [
            # Core streams
            streams.ProjectsStream(self),
            streams.WorkPackagesStream(self),
            # Reference data streams
            streams.StatusesStream(self),
            streams.TypesStream(self),
            streams.PrioritiesStream(self),
            streams.RolesStream(self),
            # User data (may require admin access)
            streams.UsersStream(self),
            # Transactional/relationship streams
            streams.VersionsStream(self),
            streams.TimeEntriesStream(self),
            streams.RelationsStream(self),
            streams.MembershipsStream(self),
            streams.AttachmentsStream(self),
        ]


if __name__ == "__main__":
    TapOpenProject.cli()
