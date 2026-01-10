# HTTP utilities for tap_openproject

import logging
import time
from urllib.parse import urljoin, urlparse
import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class HttpClient:
    # Security: Define allowed URL schemes
    ALLOWED_SCHEMES = ('https', 'http')
    DEFAULT_TIMEOUT = 30  # seconds
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_FACTOR = 2

    def __init__(self, base_url=None, api_key=None, timeout=None, max_retries=None):
        """
        Initialize HTTP client for OpenProject API.
        
        Args:
            base_url: Base URL for OpenProject instance (e.g., https://community.openproject.org/api/v3)
            api_key: API key from your OpenProject account page
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retries for failed requests (default: 3)
        
        Raises:
            ValueError: If base_url is invalid or uses insecure scheme
        """
        # Input validation
        if base_url:
            base_url = base_url.rstrip('/')  # Normalize URL
            parsed = urlparse(base_url)
            if parsed.scheme not in self.ALLOWED_SCHEMES:
                raise ValueError(f"Invalid URL scheme. Only {self.ALLOWED_SCHEMES} are allowed")
            if not parsed.netloc:
                raise ValueError("Invalid base_url: missing domain")
        
        self.base_url = base_url or "https://community.openproject.org/api/v3"
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        
        # Validate API key
        if api_key is not None and not isinstance(api_key, str):
            raise ValueError("api_key must be a string")
        if api_key is not None and len(api_key.strip()) == 0:
            raise ValueError("api_key cannot be empty")
            
        self.api_key = api_key
        # OpenProject uses Basic Auth with username "apikey" and password as the API key
        self.auth = HTTPBasicAuth('apikey', api_key) if api_key else None
        
        # Configure session with retry logic
        self.session = self._create_session()

    def _create_session(self):
        """Create a requests session with retry logic and connection pooling."""
        session = requests.Session()
        
        # Configure retry strategy for transient errors
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.DEFAULT_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP status codes
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Updated parameter name
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def get_headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "tap-open-project/1.0"  # Identify the client
        }

    def get(self, endpoint, params=None):
        """
        Make a GET request to the OpenProject API.
        
        Args:
            endpoint: API endpoint (without leading slash)
            params: Query parameters dict
            
        Returns:
            dict: Parsed JSON response
            
        Raises:
            requests.exceptions.RequestException: For network/HTTP errors
            ValueError: For invalid responses
        """
        # Sanitize endpoint to prevent path traversal
        endpoint = endpoint.lstrip('/')
        if '..' in endpoint or endpoint.startswith('/'):
            raise ValueError(f"Invalid endpoint: {endpoint}")
        
        # Use urljoin for safe URL construction
        url = urljoin(f"{self.base_url}/", endpoint)
        
        # Verify the constructed URL is still within our base domain (security check)
        if not url.startswith(self.base_url):
            raise ValueError(f"Constructed URL {url} is outside base URL {self.base_url}")
        
        try:
            logger.debug(f"GET request to {url}")
            response = self.session.get(
                url,
                params=params,
                headers=self.get_headers(),
                auth=self.auth,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Validate response is JSON
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type and 'application/hal+json' not in content_type:
                logger.warning(f"Unexpected content type: {content_type}")
            
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timed out after {self.timeout} seconds")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise
    
    def close(self):
        """Close the session and release resources."""
        if hasattr(self, 'session'):
            self.session.close()
