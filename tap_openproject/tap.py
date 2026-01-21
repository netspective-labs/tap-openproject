"""OpenProject tap class."""

from __future__ import annotations

from typing import List

from singer_sdk import Stream, Tap
from singer_sdk import typing as th

from tap_openproject import streams


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
        # Resolve project identifiers to IDs before initializing
        if config and isinstance(config, dict) and "project_identifiers" in config:
            self._resolve_project_identifiers_pre_init(config)
        
        super().__init__(config=config, parse_env_config=parse_env_config, validate_config=validate_config, **kwargs)

    def _resolve_project_identifiers_pre_init(self, config):
        """Resolve project identifiers to IDs using direct HTTP request."""
        import requests
        
        identifiers = config.get("project_identifiers", [])
        if not identifiers:
            return

        base_url = config.get("base_url")
        api_key = config.get("api_key")
        if not base_url or not api_key:
            return

        # Fetch projects
        url = f"{base_url}/projects"
        headers = {"User-Agent": config.get("user_agent", "tap-openproject/0.3.0")}
        auth = ("", api_key)  # Basic auth with empty username
        
        try:
            response = requests.get(url, headers=headers, auth=auth, timeout=config.get("timeout", 30))
            response.raise_for_status()
            data = response.json()
            
            # Extract projects from HAL response
            projects = data.get("_embedded", {}).get("elements", [])
            id_map = {p.get("identifier"): p.get("id") for p in projects if p.get("identifier")}
            
            resolved_ids = [id_map.get(ident) for ident in identifiers if ident in id_map]
            missing = [ident for ident in identifiers if ident not in id_map]
            if missing:
                # Can't log yet, but could store for later warning
                pass
            
            existing_ids = config.get("project_ids", [])
            config["project_ids"] = list(set(existing_ids + resolved_ids))
            
        except Exception:
            # If fetching fails, just continue without resolving
            pass

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
