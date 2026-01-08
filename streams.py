
# Stream definitions for tap_open_project
import json
import logging
import os
import singer
from tap_open_project.http_client import HttpClient

logger = logging.getLogger(__name__)

class ProjectStream:
    name = "projects"
    schema = "schemas/projects.json"

    def __init__(self, client=None):
        self.client = client or HttpClient()

    def get_records(self):
        """
        Fetch project records from OpenProject API.
        
        Returns:
            list: List of project records
            
        Raises:
            ValueError: If API response structure is unexpected
            requests.exceptions.RequestException: For network/HTTP errors
        """
        try:
            data = self.client.get("projects")
            
            # Validate response structure
            if not isinstance(data, dict):
                raise ValueError(f"Expected dict response, got {type(data)}")
            
            # OpenProject returns data in _embedded.elements (not projects)
            embedded = data.get("_embedded", {})
            if not isinstance(embedded, dict):
                raise ValueError(f"Expected dict in _embedded, got {type(embedded)}")
            
            # Try both 'elements' and 'projects' for compatibility
            records = embedded.get("elements") or embedded.get("projects", [])
            
            if not isinstance(records, list):
                raise ValueError(f"Expected list of records, got {type(records)}")
            
            logger.info(f"Retrieved {len(records)} project records")
            return records
            
        except Exception as e:
            logger.error(f"Failed to fetch project records: {e}")
            raise
    
    def __del__(self):
        """Cleanup resources when stream is destroyed."""
        if hasattr(self, 'client') and hasattr(self.client, 'close'):
            self.client.close()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    client = None
    try:
        client = HttpClient()
        stream = ProjectStream(client)
        projects = stream.get_records()
        
        # Load and emit schema
        schema_path = os.path.join(os.path.dirname(__file__), stream.schema)
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        singer.write_schema(stream.name, schema, ["id"])
        
        # Emit Singer record messages
        for project in projects:
            singer.write_record(stream.name, project)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        if client:
            client.close()
