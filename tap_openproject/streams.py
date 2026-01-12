"""Stream definitions for tap-openproject."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urljoin

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
        # Store api_key for later use
        self.api_key = api_key
        # OpenProject uses Basic Auth with username "apikey" and password as the API key
        # We'll handle the auth in __call__ method, so we just initialize parent with dummy values
        super().__init__(stream=stream, key="Authorization", value="", location="header")
    
    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        """Authenticate a request by adding Basic Auth header.
        
        Args:
            request: The request to authenticate.
            
        Returns:
            The authenticated request.
        """
        # Manually set Basic Auth header
        credentials = base64.b64encode(f"apikey:{self.api_key}".encode()).decode()
        request.headers["Authorization"] = f"Basic {credentials}"
        return request


class ProjectsStream(RESTStream):
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
    ).to_dict()

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
        headers["User-Agent"] = self.config.get("user_agent", "tap-openproject/0.2.0")
        headers["Accept"] = "application/json"
        return headers

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
        
        # Add pagination parameters if available
        if next_page_token:
            params["offset"] = next_page_token
        
        # Add start_date filter if configured and replication is not resuming
        if self.config.get("start_date") and not self.get_starting_replication_key_value(context):
            start_date = self.config["start_date"]
            # Validate start_date is a valid ISO 8601 datetime to prevent injection
            try:
                datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid start_date format: {start_date}. Must be ISO 8601 datetime.") from e
            params["filters"] = f'[{{"updatedAt":{{"operator":">=","values":["{start_date}"]}}}}]'
        
        return params

    def parse_response(self, response: requests.Response) -> Iterable[Dict[str, Any]]:
        """Parse the API response and yield records.
        
        Args:
            response: The HTTP response object.
            
        Yields:
            Individual record dictionaries.
        """
        # Check HTTP status before parsing
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            # Determine if error is retriable (5xx) or fatal (4xx)
            if 500 <= response.status_code < 600:
                raise RetriableAPIError(f"HTTP {response.status_code}: {str(e)}") from e
            else:
                raise FatalAPIError(f"HTTP {response.status_code}: {str(e)}") from e
        
        # Parse JSON response with error handling
        try:
            data = response.json()
        except requests.JSONDecodeError as e:
            raise FatalAPIError(f"Invalid JSON response: {str(e)}") from e
        
        # OpenProject returns data in _embedded.elements
        embedded = data.get("_embedded", {})
        records = embedded.get("elements", [])
        
        self.logger.info(f"Retrieved {len(records)} project records from page")
        
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
        
        # Check if there's a next page
        links = data.get("_links", {})
        if "nextByOffset" in links:
            # Extract offset from the next page link or calculate it
            total = data.get("total", 0)
            page_size = data.get("pageSize", len(data.get("_embedded", {}).get("elements", [])))
            current_offset = data.get("offset", 0)
            next_offset = current_offset + page_size
            
            if next_offset < total:
                return next_offset
        
        return None


class WorkPackagesStream(RESTStream):
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
        th.Property("_links", th.ObjectType(
            th.Property("type", th.ObjectType(
                th.Property("href", th.StringType),
                th.Property("title", th.StringType, description="Work package type: Bug, Task, Feature, etc."),
            )),
            th.Property("status", th.ObjectType(
                th.Property("href", th.StringType),
                th.Property("title", th.StringType, description="Status: Open, In Progress, Closed, etc."),
            )),
            th.Property("priority", th.ObjectType(
                th.Property("href", th.StringType),
                th.Property("title", th.StringType, description="Priority level"),
            )),
            th.Property("assignee", th.ObjectType(
                th.Property("href", th.StringType),
                th.Property("title", th.StringType, description="Assigned user"),
            )),
            th.Property("project", th.ObjectType(
                th.Property("href", th.StringType),
                th.Property("title", th.StringType, description="Project name"),
            )),
        ), description="HAL links with essential metadata"),
        # Flattened convenience fields extracted from _links
        th.Property("type_title", th.StringType, description="Work package type extracted from _links.type.title"),
        th.Property("status_title", th.StringType, description="Status extracted from _links.status.title"),
        th.Property("priority_title", th.StringType, description="Priority extracted from _links.priority.title"),
        th.Property("assignee_title", th.StringType, description="Assignee extracted from _links.assignee.title"),
        th.Property("project_title", th.StringType, description="Project extracted from _links.project.title"),
    ).to_dict()

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
        headers["User-Agent"] = self.config.get("user_agent", "tap-openproject/0.2.0")
        headers["Accept"] = "application/json"
        return headers

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
        
        # Add pagination parameters if available
        if next_page_token:
            params["offset"] = next_page_token
        
        # Add start_date filter if configured and replication is not resuming
        if self.config.get("start_date") and not self.get_starting_replication_key_value(context):
            start_date = self.config["start_date"]
            # Validate start_date is a valid ISO 8601 datetime to prevent injection
            try:
                datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid start_date format: {start_date}. Must be ISO 8601 datetime.") from e
            params["filters"] = f'[{{"updatedAt":{{"operator":">=","values":["{start_date}"]}}}}]'
        
        return params

    def parse_response(self, response: requests.Response) -> Iterable[Dict[str, Any]]:
        """Parse the API response and yield records.
        
        Args:
            response: The HTTP response object.
            
        Yields:
            Individual record dictionaries.
        """
        # Check HTTP status before parsing
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            # Determine if error is retriable (5xx) or fatal (4xx)
            if 500 <= response.status_code < 600:
                raise RetriableAPIError(f"HTTP {response.status_code}: {str(e)}") from e
            else:
                raise FatalAPIError(f"HTTP {response.status_code}: {str(e)}") from e
        
        # Parse JSON response with error handling
        try:
            data = response.json()
        except requests.JSONDecodeError as e:
            raise FatalAPIError(f"Invalid JSON response: {str(e)}") from e
        
        # OpenProject returns data in _embedded.elements
        embedded = data.get("_embedded", {})
        records = embedded.get("elements", [])
        
        self.logger.info(f"Retrieved {len(records)} work package records from page")
        
        for record in records:
            yield record

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
            row["type_title"] = links.get("type", {}).get("title")
            row["status_title"] = links.get("status", {}).get("title")
            row["priority_title"] = links.get("priority", {}).get("title")
            row["assignee_title"] = links.get("assignee", {}).get("title")
            row["project_title"] = links.get("project", {}).get("title")
        return row

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
        
        # Check if there's a next page
        links = data.get("_links", {})
        if "nextByOffset" in links:
            # Extract offset from the next page link or calculate it
            total = data.get("total", 0)
            page_size = data.get("pageSize", len(data.get("_embedded", {}).get("elements", [])))
            current_offset = data.get("offset", 0)
            next_offset = current_offset + page_size
            
            if next_offset < total:
                return next_offset
        
        return None
