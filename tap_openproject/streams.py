"""Stream definitions for tap-openproject."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import requests
from singer_sdk import typing as th
from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import APIKeyAuthenticator
from singer_sdk.exceptions import FatalAPIError, RetriableAPIError


class OpenProjectAuthenticator(APIKeyAuthenticator):
    """OpenProject API authenticator using Basic Auth with apikey."""

    def __init__(self, stream: RESTStream, api_key: str) -> None:
        """Initialize the authenticator.

        Args:
            stream: The stream instance to authenticate.
            api_key: The OpenProject API key.
        """
        self.api_key = api_key
        super().__init__(stream=stream, key="Authorization", value="", location="header")

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        """Authenticate a request by adding Basic Auth header.

        Args:
            request: The request to authenticate.

        Returns:
            The authenticated request.
        """
        credentials = base64.b64encode(f"apikey:{self.api_key}".encode()).decode()
        request.headers["Authorization"] = f"Basic {credentials}"
        return request


class OpenProjectStream(RESTStream):
    """Base stream class for OpenProject API with common functionality."""

    @property
    def url_base(self) -> str:
        """Return the base URL for the API.

        Returns:
            The base URL string.
        """
        base_url = self.config.get("base_url", "https://community.openproject.org/api/v3")
        return base_url.rstrip("/")

    @property
    def authenticator(self) -> OpenProjectAuthenticator:
        """Return the authenticator for this stream.

        Returns:
            The authenticator instance.
        """
        return OpenProjectAuthenticator(
            stream=self,
            api_key=self.config["api_key"]
        )

    @property
    def http_headers(self) -> dict:
        """Return HTTP headers for API requests.

        Returns:
            Dictionary of HTTP headers.
        """
        headers = super().http_headers
        headers["User-Agent"] = self.config.get("user_agent", "tap-openproject/0.3.0")
        headers["Accept"] = "application/json"
        return headers

    def _validate_datetime(self, date_string: str) -> None:
        """Validate ISO 8601 datetime format to prevent injection.

        Args:
            date_string: The date string to validate.

        Raises:
            ValueError: If the date format is invalid.
        """
        try:
            datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid date format: {date_string}. Must be ISO 8601 datetime.") from e

    @staticmethod
    def extract_id_from_href(href: Optional[str]) -> Optional[int]:
        """Extract numeric ID from HAL href link.

        Example: '/api/v3/projects/5' -> 5

        Args:
            href: The HAL href string.

        Returns:
            The extracted numeric ID, or None if extraction fails.
        """
        if not href:
            return None
        try:
            return int(href.rstrip('/').split('/')[-1])
        except (ValueError, IndexError):
            return None

    def flatten_link(self, links: dict, key: str, extract_id: bool = True) -> dict:
        """Extract title and optionally ID from a HAL link.

        Args:
            links: The _links object from the record.
            key: The link key to extract (e.g., 'status', 'type').
            extract_id: Whether to extract numeric ID from href.

        Returns:
            Dict with '{key}_title' and optionally '{key}_id' keys.
        """
        result = {}
        link_obj = links.get(key, {})

        if link_obj:
            result[f"{key}_title"] = link_obj.get("title")
            if extract_id:
                result[f"{key}_id"] = self.extract_id_from_href(link_obj.get("href"))
        else:
            result[f"{key}_title"] = None
            if extract_id:
                result[f"{key}_id"] = None

        return result

    def get_url_params(
        self,
        context: Optional[dict],
        next_page_token: Optional[Any],
    ) -> Dict[str, Any]:
        """Get URL query parameters for the request.

        Args:
            context: Stream context dictionary.
            next_page_token: Token for the next page of results.

        Returns:
            Dictionary of URL query parameters.
        """
        params: Dict[str, Any] = {}

        if next_page_token:
            params["offset"] = next_page_token

        # Only apply start_date filter for incremental streams with replication_key
        if (self.replication_key and
            self.config.get("start_date") and
            not self.get_starting_replication_key_value(context)):
            start_date = self.config["start_date"]
            self._validate_datetime(start_date)
            params["filters"] = f'[{{"{self.replication_key}":{{"operator":">=","values":["{start_date}"]}}}}]'

        return params

    def parse_response(self, response: requests.Response) -> Iterable[Dict[str, Any]]:
        """Parse the API response and yield records.

        Args:
            response: The HTTP response object.

        Yields:
            Individual record dictionaries.
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            if 500 <= response.status_code < 600:
                raise RetriableAPIError(f"HTTP {response.status_code}: {str(e)}") from e
            else:
                raise FatalAPIError(f"HTTP {response.status_code}: {str(e)}") from e

        try:
            data = response.json()
        except requests.JSONDecodeError as e:
            raise FatalAPIError(f"Invalid JSON response: {str(e)}") from e

        embedded = data.get("_embedded", {})
        records = embedded.get("elements", [])

        self.logger.info(f"Retrieved {len(records)} {self.name} records from page")

        for record in records:
            yield record

    def get_next_page_token(
        self,
        response: requests.Response,
        previous_token: Optional[Any],
    ) -> Optional[Any]:
        """Get the token for the next page of results.

        Args:
            response: The HTTP response object.
            previous_token: The previous pagination token.

        Returns:
            The next pagination token, or None if there are no more pages.
        """
        data = response.json()

        links = data.get("_links", {})
        if "nextByOffset" in links:
            total = data.get("total", 0)
            page_size = data.get("pageSize", len(data.get("_embedded", {}).get("elements", [])))
            current_offset = data.get("offset", 0)
            next_offset = current_offset + page_size

            if next_offset < total:
                return next_offset

        return None


# =============================================================================
# Core Streams
# =============================================================================

class ProjectsStream(OpenProjectStream):
    """Projects stream from OpenProject API."""

    name = "projects"
    path = "/projects"
    primary_keys = ["id"]
    replication_key = "updatedAt"

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True, description="Unique project identifier"),
        th.Property("_type", th.StringType, description="Resource type"),
        th.Property("identifier", th.StringType, description="Project key/identifier"),
        th.Property("name", th.StringType, description="Project name"),
        th.Property("active", th.BooleanType, description="Whether project is active"),
        th.Property("public", th.BooleanType, description="Whether project is public"),
        th.Property("description", th.ObjectType(
            th.Property("format", th.StringType),
            th.Property("raw", th.StringType),
            th.Property("html", th.StringType),
        ), description="Project description with formatting"),
        th.Property("status", th.StringType, description="Project status"),
        th.Property("statusExplanation", th.ObjectType(
            th.Property("format", th.StringType),
            th.Property("raw", th.StringType),
            th.Property("html", th.StringType),
        ), description="Status explanation"),
        th.Property("createdAt", th.DateTimeType, description="Creation timestamp"),
        th.Property("updatedAt", th.DateTimeType, description="Last update timestamp"),
        th.Property("_links", th.ObjectType(), description="HAL links"),
        # Flattened fields from _links
        th.Property("parent_id", th.IntegerType, description="Parent project ID"),
        th.Property("parent_title", th.StringType, description="Parent project name"),
    ).to_dict()

    def post_process(self, row: dict, context: Optional[dict] = None) -> Optional[dict]:
        """Extract parent project info from _links for easier querying.

        Args:
            row: Individual record dictionary.
            context: Stream context dictionary.

        Returns:
            Modified record with flattened fields.
        """
        if "_links" in row and row["_links"]:
            links = row["_links"]
            row.update(self.flatten_link(links, "parent"))
        else:
            row["parent_id"] = None
            row["parent_title"] = None
        return row


class WorkPackagesStream(OpenProjectStream):
    """Work packages stream from OpenProject API (includes bugs, tasks, features, etc.)."""

    name = "work_packages"
    path = "/work_packages"
    primary_keys = ["id"]
    replication_key = "updatedAt"

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True, description="Unique work package identifier"),
        th.Property("_type", th.StringType, description="Resource type"),
        th.Property("lockVersion", th.IntegerType, description="Lock version for optimistic locking"),
        th.Property("subject", th.StringType, description="Work package subject/title"),
        th.Property("description", th.ObjectType(
            th.Property("format", th.StringType),
            th.Property("raw", th.StringType),
            th.Property("html", th.StringType),
        ), description="Work package description with formatting"),
        th.Property("scheduleManually", th.BooleanType, description="Whether scheduling is manual"),
        th.Property("startDate", th.DateType, description="Start date"),
        th.Property("dueDate", th.DateType, description="Due date"),
        th.Property("derivedStartDate", th.DateType, description="Calculated start date"),
        th.Property("derivedDueDate", th.DateType, description="Calculated due date"),
        th.Property("estimatedTime", th.StringType, description="Estimated time duration (ISO 8601)"),
        th.Property("derivedEstimatedTime", th.StringType, description="Calculated estimated time"),
        th.Property("spentTime", th.StringType, description="Time spent on work package"),
        th.Property("percentageDone", th.IntegerType, description="Completion percentage"),
        th.Property("createdAt", th.DateTimeType, description="Creation timestamp"),
        th.Property("updatedAt", th.DateTimeType, description="Last update timestamp"),
        th.Property("position", th.IntegerType, description="Position in list"),
        th.Property("readonly", th.BooleanType, description="Whether work package is readonly"),
        th.Property("_links", th.ObjectType(), description="HAL links"),
        # Flattened fields from _links (titles)
        th.Property("type_title", th.StringType, description="Work package type (Bug, Task, Feature, etc.)"),
        th.Property("status_title", th.StringType, description="Status (Open, In Progress, Closed, etc.)"),
        th.Property("priority_title", th.StringType, description="Priority level"),
        th.Property("assignee_title", th.StringType, description="Assigned user name"),
        th.Property("project_title", th.StringType, description="Project name"),
        th.Property("author_title", th.StringType, description="Author name"),
        th.Property("responsible_title", th.StringType, description="Responsible user name"),
        th.Property("version_title", th.StringType, description="Version/milestone name"),
        # Flattened fields from _links (IDs for joins)
        th.Property("type_id", th.IntegerType, description="Work package type ID"),
        th.Property("status_id", th.IntegerType, description="Status ID"),
        th.Property("priority_id", th.IntegerType, description="Priority ID"),
        th.Property("assignee_id", th.IntegerType, description="Assignee user ID"),
        th.Property("project_id", th.IntegerType, description="Project ID"),
        th.Property("author_id", th.IntegerType, description="Author user ID"),
        th.Property("responsible_id", th.IntegerType, description="Responsible user ID"),
        th.Property("version_id", th.IntegerType, description="Version/milestone ID"),
        th.Property("parent_id", th.IntegerType, description="Parent work package ID"),
    ).to_dict()

    def post_process(self, row: dict, context: Optional[dict] = None) -> Optional[dict]:
        """Extract commonly used fields from _links for easier querying.

        Args:
            row: Individual record dictionary.
            context: Stream context dictionary.

        Returns:
            Modified record with flattened fields.
        """
        if "_links" in row and row["_links"]:
            links = row["_links"]
            # Extract all relevant links with both title and ID
            row.update(self.flatten_link(links, "type"))
            row.update(self.flatten_link(links, "status"))
            row.update(self.flatten_link(links, "priority"))
            row.update(self.flatten_link(links, "assignee"))
            row.update(self.flatten_link(links, "project"))
            row.update(self.flatten_link(links, "author"))
            row.update(self.flatten_link(links, "responsible"))
            row.update(self.flatten_link(links, "version"))
            row.update(self.flatten_link(links, "parent"))
        return row

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return context for child streams (attachments).

        Args:
            record: Individual record dictionary.
            context: Stream context dictionary.

        Returns:
            Context dictionary for child streams.
        """
        return {
            "work_package_id": record["id"],
            "work_package_title": record.get("subject"),
        }


# =============================================================================
# Reference Data Streams (typically full refresh)
# =============================================================================

class StatusesStream(OpenProjectStream):
    """Work package statuses reference data."""

    name = "statuses"
    path = "/statuses"
    primary_keys = ["id"]
    replication_key = None  # Full refresh only

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True, description="Unique status identifier"),
        th.Property("_type", th.StringType, description="Resource type"),
        th.Property("name", th.StringType, description="Status name (e.g., 'New', 'In progress', 'Closed')"),
        th.Property("color", th.StringType, description="Hex color code"),
        th.Property("isClosed", th.BooleanType, description="Whether this status represents a closed state"),
        th.Property("isDefault", th.BooleanType, description="Whether this is the default status"),
        th.Property("isReadonly", th.BooleanType, description="Whether work packages with this status are readonly"),
        th.Property("defaultDoneRatio", th.IntegerType, description="Default percentage done for this status"),
        th.Property("position", th.IntegerType, description="Display order position"),
        th.Property("_links", th.ObjectType(), description="HAL links"),
    ).to_dict()


class TypesStream(OpenProjectStream):
    """Work package types reference data (Bug, Task, Feature, etc.)."""

    name = "types"
    path = "/types"
    primary_keys = ["id"]
    replication_key = "updatedAt"

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True, description="Unique type identifier"),
        th.Property("_type", th.StringType, description="Resource type"),
        th.Property("name", th.StringType, description="Type name (e.g., 'Bug', 'Task', 'Feature')"),
        th.Property("color", th.StringType, description="Hex color code"),
        th.Property("position", th.IntegerType, description="Display order position"),
        th.Property("isDefault", th.BooleanType, description="Whether this is the default type"),
        th.Property("isMilestone", th.BooleanType, description="Whether this type represents a milestone"),
        th.Property("createdAt", th.DateTimeType, description="Creation timestamp"),
        th.Property("updatedAt", th.DateTimeType, description="Last update timestamp"),
        th.Property("_links", th.ObjectType(), description="HAL links"),
    ).to_dict()


class PrioritiesStream(OpenProjectStream):
    """Work package priorities reference data."""

    name = "priorities"
    path = "/priorities"
    primary_keys = ["id"]
    replication_key = None  # Full refresh only

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True, description="Unique priority identifier"),
        th.Property("_type", th.StringType, description="Resource type"),
        th.Property("name", th.StringType, description="Priority name (e.g., 'Low', 'Normal', 'High', 'Immediate')"),
        th.Property("color", th.StringType, description="Hex color code"),
        th.Property("position", th.IntegerType, description="Display order (lower = higher priority)"),
        th.Property("isDefault", th.BooleanType, description="Whether this is the default priority"),
        th.Property("isActive", th.BooleanType, description="Whether this priority is active"),
        th.Property("_links", th.ObjectType(), description="HAL links"),
    ).to_dict()


class RolesStream(OpenProjectStream):
    """Role definitions for project memberships."""

    name = "roles"
    path = "/roles"
    primary_keys = ["id"]
    replication_key = None  # Full refresh only

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True, description="Unique role identifier"),
        th.Property("_type", th.StringType, description="Resource type"),
        th.Property("name", th.StringType, description="Role name (e.g., 'Project admin', 'Member', 'Reader')"),
        th.Property("_links", th.ObjectType(), description="HAL links"),
    ).to_dict()


class UsersStream(OpenProjectStream):
    """User accounts for assignees, authors, responsible parties."""

    name = "users"
    path = "/users"
    primary_keys = ["id"]
    replication_key = "updatedAt"

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True, description="Unique user identifier"),
        th.Property("_type", th.StringType, description="Resource type"),
        th.Property("login", th.StringType, description="Username"),
        th.Property("firstName", th.StringType, description="First name"),
        th.Property("lastName", th.StringType, description="Last name"),
        th.Property("name", th.StringType, description="Full display name"),
        th.Property("email", th.StringType, description="Email address (may require admin access)"),
        th.Property("admin", th.BooleanType, description="Whether user is an admin"),
        th.Property("status", th.StringType, description="User status: active, registered, locked, invited"),
        th.Property("language", th.StringType, description="User's preferred language"),
        th.Property("createdAt", th.DateTimeType, description="Creation timestamp"),
        th.Property("updatedAt", th.DateTimeType, description="Last update timestamp"),
        th.Property("_links", th.ObjectType(), description="HAL links"),
        # Flattened field
        th.Property("avatar_url", th.StringType, description="User avatar URL"),
    ).to_dict()

    def parse_response(self, response: requests.Response) -> Iterable[Dict[str, Any]]:
        """Parse response with graceful handling of permission errors.

        Args:
            response: The HTTP response object.

        Yields:
            Individual record dictionaries.
        """
        if response.status_code == 403:
            self.logger.warning(
                "Insufficient permissions to access users endpoint. "
                "Users stream requires admin access. Skipping."
            )
            return
        yield from super().parse_response(response)

    def post_process(self, row: dict, context: Optional[dict] = None) -> Optional[dict]:
        """Extract avatar URL from _links.

        Args:
            row: Individual record dictionary.
            context: Stream context dictionary.

        Returns:
            Modified record with avatar_url field.
        """
        if "_links" in row and row["_links"]:
            links = row["_links"]
            row["avatar_url"] = links.get("avatar", {}).get("href")
        else:
            row["avatar_url"] = None
        return row


# =============================================================================
# Transactional/Relationship Streams
# =============================================================================

class VersionsStream(OpenProjectStream):
    """Project versions/milestones/releases."""

    name = "versions"
    path = "/versions"
    primary_keys = ["id"]
    replication_key = "updatedAt"

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True, description="Unique version identifier"),
        th.Property("_type", th.StringType, description="Resource type"),
        th.Property("name", th.StringType, description="Version name"),
        th.Property("description", th.ObjectType(
            th.Property("format", th.StringType),
            th.Property("raw", th.StringType),
            th.Property("html", th.StringType),
        ), description="Version description"),
        th.Property("startDate", th.DateType, description="Version start date"),
        th.Property("endDate", th.DateType, description="Version end date (due date)"),
        th.Property("status", th.StringType, description="Version status: open, locked, closed"),
        th.Property("sharing", th.StringType, description="Sharing scope: none, descendants, hierarchy, tree, system"),
        th.Property("createdAt", th.DateTimeType, description="Creation timestamp"),
        th.Property("updatedAt", th.DateTimeType, description="Last update timestamp"),
        th.Property("_links", th.ObjectType(), description="HAL links"),
        # Flattened fields
        th.Property("project_id", th.IntegerType, description="Project ID this version belongs to"),
        th.Property("project_title", th.StringType, description="Project name"),
    ).to_dict()

    def post_process(self, row: dict, context: Optional[dict] = None) -> Optional[dict]:
        """Extract project info from _links.

        Args:
            row: Individual record dictionary.
            context: Stream context dictionary.

        Returns:
            Modified record with flattened project fields.
        """
        if "_links" in row and row["_links"]:
            links = row["_links"]
            # definingProject contains the project info for versions
            defining_project = self.flatten_link(links, "definingProject")
            row["project_id"] = defining_project.get("definingProject_id")
            row["project_title"] = defining_project.get("definingProject_title")
        else:
            row["project_id"] = None
            row["project_title"] = None
        return row


class TimeEntriesStream(OpenProjectStream):
    """Time tracking entries for work packages."""

    name = "time_entries"
    path = "/time_entries"
    primary_keys = ["id"]
    replication_key = "updatedAt"

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True, description="Unique time entry identifier"),
        th.Property("_type", th.StringType, description="Resource type"),
        th.Property("comment", th.ObjectType(
            th.Property("format", th.StringType),
            th.Property("raw", th.StringType),
            th.Property("html", th.StringType),
        ), description="Time entry comment"),
        th.Property("spentOn", th.DateType, description="Date the time was spent"),
        th.Property("hours", th.StringType, description="ISO 8601 duration (e.g., 'PT2H30M')"),
        th.Property("ongoing", th.BooleanType, description="Whether time entry is currently running"),
        th.Property("createdAt", th.DateTimeType, description="Creation timestamp"),
        th.Property("updatedAt", th.DateTimeType, description="Last update timestamp"),
        th.Property("_links", th.ObjectType(), description="HAL links"),
        # Flattened fields
        th.Property("project_id", th.IntegerType, description="Project ID"),
        th.Property("project_title", th.StringType, description="Project name"),
        th.Property("work_package_id", th.IntegerType, description="Work package ID"),
        th.Property("work_package_title", th.StringType, description="Work package subject"),
        th.Property("user_id", th.IntegerType, description="User ID who logged the time"),
        th.Property("user_title", th.StringType, description="User name"),
        th.Property("activity_id", th.IntegerType, description="Activity type ID"),
        th.Property("activity_title", th.StringType, description="Activity type name"),
    ).to_dict()

    def post_process(self, row: dict, context: Optional[dict] = None) -> Optional[dict]:
        """Extract relationship IDs from _links.

        Args:
            row: Individual record dictionary.
            context: Stream context dictionary.

        Returns:
            Modified record with flattened relationship fields.
        """
        if "_links" in row and row["_links"]:
            links = row["_links"]
            row.update(self.flatten_link(links, "project"))

            # workPackage link
            wp = self.flatten_link(links, "workPackage")
            row["work_package_id"] = wp.get("workPackage_id")
            row["work_package_title"] = wp.get("workPackage_title")

            row.update(self.flatten_link(links, "user"))
            row.update(self.flatten_link(links, "activity"))
        return row


class RelationsStream(OpenProjectStream):
    """Work package relationships (blocks, relates, follows, etc.)."""

    name = "relations"
    path = "/relations"
    primary_keys = ["id"]
    replication_key = None  # Full refresh only

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True, description="Unique relation identifier"),
        th.Property("_type", th.StringType, description="Resource type"),
        th.Property("name", th.StringType, description="Relation display name"),
        th.Property("type", th.StringType, description="Relation type: relates, duplicates, blocks, precedes, follows, includes, partof, requires"),
        th.Property("reverseType", th.StringType, description="Reverse relation type"),
        th.Property("description", th.ObjectType(
            th.Property("format", th.StringType),
            th.Property("raw", th.StringType),
            th.Property("html", th.StringType),
        ), description="Relation description"),
        th.Property("delay", th.IntegerType, description="Delay in days (for scheduling relations)"),
        th.Property("_links", th.ObjectType(), description="HAL links"),
        # Flattened fields
        th.Property("from_work_package_id", th.IntegerType, description="Source work package ID"),
        th.Property("to_work_package_id", th.IntegerType, description="Target work package ID"),
    ).to_dict()

    def post_process(self, row: dict, context: Optional[dict] = None) -> Optional[dict]:
        """Extract work package IDs from _links.

        Args:
            row: Individual record dictionary.
            context: Stream context dictionary.

        Returns:
            Modified record with from/to work package IDs.
        """
        if "_links" in row and row["_links"]:
            links = row["_links"]
            row["from_work_package_id"] = self.extract_id_from_href(
                links.get("from", {}).get("href")
            )
            row["to_work_package_id"] = self.extract_id_from_href(
                links.get("to", {}).get("href")
            )
        else:
            row["from_work_package_id"] = None
            row["to_work_package_id"] = None
        return row


class MembershipsStream(OpenProjectStream):
    """Project membership assignments."""

    name = "memberships"
    path = "/memberships"
    primary_keys = ["id"]
    replication_key = "updatedAt"

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True, description="Unique membership identifier"),
        th.Property("_type", th.StringType, description="Resource type"),
        th.Property("createdAt", th.DateTimeType, description="Creation timestamp"),
        th.Property("updatedAt", th.DateTimeType, description="Last update timestamp"),
        th.Property("_links", th.ObjectType(), description="HAL links"),
        # Flattened fields
        th.Property("project_id", th.IntegerType, description="Project ID"),
        th.Property("project_title", th.StringType, description="Project name"),
        th.Property("principal_id", th.IntegerType, description="User or group ID"),
        th.Property("principal_title", th.StringType, description="User or group name"),
        th.Property("role_ids", th.ArrayType(th.IntegerType), description="Array of role IDs"),
        th.Property("role_titles", th.ArrayType(th.StringType), description="Array of role names"),
    ).to_dict()

    def post_process(self, row: dict, context: Optional[dict] = None) -> Optional[dict]:
        """Extract membership details from _links.

        Args:
            row: Individual record dictionary.
            context: Stream context dictionary.

        Returns:
            Modified record with flattened membership fields.
        """
        if "_links" in row and row["_links"]:
            links = row["_links"]
            row.update(self.flatten_link(links, "project"))
            row.update(self.flatten_link(links, "principal"))

            # Extract roles array
            roles = links.get("roles", [])
            row["role_ids"] = [
                self.extract_id_from_href(r.get("href"))
                for r in roles
                if r.get("href")
            ]
            row["role_titles"] = [
                r.get("title")
                for r in roles
                if r.get("title")
            ]
        else:
            row["project_id"] = None
            row["project_title"] = None
            row["principal_id"] = None
            row["principal_title"] = None
            row["role_ids"] = []
            row["role_titles"] = []
        return row


class AttachmentsStream(OpenProjectStream):
    """Attachments from work packages.

    Note: OpenProject doesn't have a global /attachments list endpoint.
    Attachments must be fetched per work package via /work_packages/{id}/attachments.
    This stream is a child of WorkPackagesStream.
    """

    name = "attachments"
    path = "/work_packages/{work_package_id}/attachments"
    primary_keys = ["id"]
    replication_key = None  # Full refresh per work package
    parent_stream_type = WorkPackagesStream

    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True, description="Unique attachment identifier"),
        th.Property("_type", th.StringType, description="Resource type"),
        th.Property("fileName", th.StringType, description="Original file name"),
        th.Property("fileSize", th.IntegerType, description="File size in bytes"),
        th.Property("description", th.ObjectType(
            th.Property("format", th.StringType),
            th.Property("raw", th.StringType),
            th.Property("html", th.StringType),
        ), description="User-provided description"),
        th.Property("contentType", th.StringType, description="MIME type of the file"),
        th.Property("digest", th.ObjectType(
            th.Property("algorithm", th.StringType),
            th.Property("hash", th.StringType),
        ), description="File checksum"),
        th.Property("createdAt", th.DateTimeType, description="Upload timestamp"),
        th.Property("_links", th.ObjectType(), description="HAL links"),
        # Flattened fields from _links
        th.Property("author_id", th.IntegerType, description="Uploader user ID"),
        th.Property("author_title", th.StringType, description="Uploader user name"),
        th.Property("work_package_id", th.IntegerType, description="Parent work package ID"),
        th.Property("work_package_title", th.StringType, description="Parent work package subject"),
        th.Property("download_url", th.StringType, description="Direct download URL"),
    ).to_dict()

    def get_url_params(
        self,
        context: Optional[dict],
        next_page_token: Optional[Any],
    ) -> Dict[str, Any]:
        """Get URL query parameters - no filtering for child stream.

        Args:
            context: Stream context dictionary.
            next_page_token: Token for the next page of results.

        Returns:
            Dictionary of URL query parameters.
        """
        params: Dict[str, Any] = {}
        if next_page_token:
            params["offset"] = next_page_token
        return params

    def post_process(self, row: dict, context: Optional[dict] = None) -> Optional[dict]:
        """Extract attachment metadata from _links and add work package context.

        Args:
            row: Individual record dictionary.
            context: Stream context dictionary containing work_package_id.

        Returns:
            Modified record with flattened fields.
        """
        # Add work package context from parent stream
        if context:
            row["work_package_id"] = context.get("work_package_id")
            row["work_package_title"] = context.get("work_package_title")
        else:
            row["work_package_id"] = None
            row["work_package_title"] = None

        if "_links" in row and row["_links"]:
            links = row["_links"]

            # Author info
            row.update(self.flatten_link(links, "author"))

            # Download URL
            download_location = links.get("downloadLocation", {})
            row["download_url"] = download_location.get("href")
        else:
            row["author_id"] = None
            row["author_title"] = None
            row["download_url"] = None
        return row
