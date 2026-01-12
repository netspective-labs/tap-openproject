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
            default="tap-openproject/0.2.0",
            description="User-Agent header for API requests",
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams.
        
        Returns:
            A list of discovered streams.
        """
        return [
            streams.ProjectsStream(self),
            streams.WorkPackagesStream(self),
        ]


if __name__ == "__main__":
    TapOpenProject.cli()
