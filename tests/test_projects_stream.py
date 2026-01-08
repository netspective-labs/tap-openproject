
import unittest
from unittest.mock import patch
import json
from tap_open_project.streams import ProjectStream

class DummyClient:
    def get(self, endpoint, params=None):
        return {
            "_embedded": {
                "projects": [{"id": "1", "name": "Test Project", "key": "TP"}]
            }
        }

class TestProjectStream(unittest.TestCase):
    @patch("singer.write_schema")
    @patch("singer.write_record")
    def test_singer_output(self, mock_write_record, mock_write_schema):
        stream = ProjectStream(DummyClient())
        projects = stream.get_records()
        # Simulate schema loading
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "key": {"type": "string"}
            }
        }
        # Call Singer output
        import singer
        singer.write_schema(stream.name, schema, [])
        for project in projects:
            singer.write_record(stream.name, project)
        # Assert Singer methods called
        mock_write_schema.assert_called_once_with(stream.name, schema, [])
        mock_write_record.assert_called_with(stream.name, {'id': '1', 'name': 'Test Project', 'key': 'TP'})

    def test_get_records(self):
        stream = ProjectStream(DummyClient())
        records = stream.get_records()
        self.assertEqual(records[0]["name"], "Test Project")

if __name__ == "__main__":
    unittest.main()
