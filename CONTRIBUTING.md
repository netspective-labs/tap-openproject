# Contributing to tap-openproject

Thank you for contributing! This tap is built with the [Meltano Singer SDK](https://sdk.meltano.com/).

## Code of Conduct

Be respectful, inclusive, and collaborative.

## How to Contribute

### Reporting Issues

Check existing issues first, then include:

- Clear description and steps to reproduce
- Expected vs actual behavior
- Environment: Python version, OS, OpenProject instance version
- Relevant logs (remove sensitive data)

### Suggesting Features

- Describe the use case and benefits
- Check if it's supported by the Singer SDK
- Consider if it should be a stream-level or tap-level feature

### Pull Requests

1. Fork and create a feature branch from `main`
2. Follow SDK patterns and conventions
3. Add tests for new functionality
4. Update documentation (README, CHANGELOG)
5. Ensure tests pass: `poetry run pytest`
6. Run linting: `poetry run ruff check .`
7. Submit PR with clear description

## Development Setup

### Prerequisites

- Python 3.8+
- Poetry (recommended) or pip
- Git
- OpenProject API key for testing

### Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/tap-openproject.git
cd tap-openproject

# Install with Poetry
poetry install
poetry shell

# Or with pip
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# With coverage
poetry run pytest --cov=tap_openproject

# Run specific test
poetry run pytest tests/test_projects_stream.py -v
```

### Code Style

We use `ruff` for linting and formatting:

```bash
# Check code
poetry run ruff check .

# Fix automatically
poetry run ruff check --fix .

# Format code
poetry run ruff format .
```

## SDK Development Guide

### Adding a New Stream

1. Define stream class in `tap_openproject/streams.py`:

```python
class NewStream(RESTStream):
    name = "new_stream"
    path = "/endpoint"
    primary_keys = ["id"]
    replication_key = "updated_at"  # If incremental
    
    schema = th.PropertiesList(
        th.Property("id", th.IntegerType, required=True),
        # ... more properties
    ).to_dict()
```

2. Register in `tap_openproject/tap.py`:

```python
def discover_streams(self) -> List[Stream]:
    return [
        streams.ProjectsStream(self),
        streams.NewStream(self),  # Add here
    ]
```

3. Add tests in `tests/test_new_stream.py`

### Working with SDK Features

- **Stream Maps**: Inherited automatically from SDK
- **Pagination**: Override `get_next_page_token()` method
- **Authentication**: Customize `OpenProjectAuthenticator`
- **Incremental**: Set `replication_key` on stream class

### Testing with Real API

Create `config.json` (gitignored):

```json
{
  "api_key": "YOUR_TEST_API_KEY",
  "base_url": "https://community.openproject.org/api/v3"
}
```

Run manually:

```bash
poetry run tap-openproject --config config.json --discover
poetry run tap-openproject --config config.json | head -20
```

## Documentation

Update these files when making changes:

- **README.md** - User-facing documentation
- **CHANGELOG.md** - Record all changes
- **QUICKSTART.md** - Quick reference guide
- **meltano-hub.yml** - Meltano Hub metadata

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with release date
3. Create git tag: `git tag v0.x.0`
4. Push tag: `git push --tags`
5. GitHub Actions will handle the rest (if configured)

## Getting Help

- [Meltano Singer SDK Docs](https://sdk.meltano.com/)
- [Meltano Slack](https://meltano.com/slack)
- [Singer Specification](https://hub.meltano.com/singer/spec)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
cd tap-openproject

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e .
pip install pytest pytest-cov black flake8 mypy

# Run tests to verify setup
pytest tests/ -v
```

## Code Style

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

- **Line length:** 100 characters (not 79)
- **Indentation:** 4 spaces
- **Quotes:** Double quotes for strings
- **Imports:** Organized in three groups (standard library, third-party, local)

### Formatting

Use [Black](https://github.com/psf/black) for code formatting:

```bash
black tap_open_project/
```

### Linting

Run flake8 to check for issues:

```bash
flake8 tap_open_project/ --max-line-length=100
```

### Type Hints

Use type hints for function parameters and return values:

```python
def get_projects(client: HttpClient) -> List[Dict[str, Any]]:
    """Fetch all projects from the API."""
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=tap_open_project --cov-report=html

# Run specific test
pytest tests/test_projects_stream.py -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names: `test_should_extract_project_name()`
- Mock external API calls using `unittest.mock` or `responses`
- Aim for >80% code coverage

Example test:

```python
import pytest
from tap_open_project.http_client import HttpClient

def test_should_handle_authentication_error():
    """Test that 401 errors are handled gracefully."""
    client = HttpClient(
        base_url="https://test.openproject.com/api/v3",
        api_key="invalid-key"
    )
    
    with pytest.raises(AuthenticationError):
        client.get("projects")
```

## Documentation

### Docstrings

Use Google-style docstrings:

```python
def fetch_projects(client: HttpClient, start_date: Optional[str] = None) -> List[Dict]:
    """
    Fetch projects from OpenProject API.
    
    Args:
        client: Configured HTTP client instance
        start_date: Optional ISO 8601 date to filter projects
        
    Returns:
        List of project dictionaries with full metadata
        
    Raises:
        HTTPError: If API request fails
        ValueError: If start_date format is invalid
    """
    pass
```

### README Updates

When adding features, update:
- Feature list in README.md
- Configuration options table
- Usage examples
- Troubleshooting section (if relevant)

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(streams): add work packages stream

- Add WorkPackageStream class
- Implement pagination for large datasets
- Add work_packages.json schema

Closes #42

fix(http_client): handle rate limiting correctly

- Add exponential backoff for 429 responses
- Increase default max_retries to 5
- Log retry attempts to stderr
```

## Adding New Streams

To add a new stream (e.g., work packages, time entries):

1. **Create schema file:** `tap_open_project/schemas/stream_name.json`
2. **Add stream class:** Inherit from base stream in `streams.py`
3. **Implement `get_records()`** method
4. **Add tests:** Create `tests/test_stream_name.py`
5. **Update documentation:** Add to README.md

Example:

```python
class WorkPackageStream:
    """Stream for extracting work packages."""
    
    name = "work_packages"
    schema = "schemas/work_packages.json"
    key_properties = ["id"]
    
    def __init__(self, client: HttpClient):
        self.client = client
    
    def get_records(self) -> List[Dict[str, Any]]:
        """Fetch all work packages."""
        data = self.client.get("work_packages")
        # Transform and return records
        return data.get("_embedded", {}).get("elements", [])
```

## Release Process

1. Update version in `setup.py`
2. Update CHANGELOG.md with release notes
3. Create a git tag: `git tag -a v0.2.0 -m "Release v0.2.0"`
4. Push tag: `git push origin v0.2.0`
5. Create GitHub release with changelog

## Questions?

- Open an issue for general questions
- Join discussions in GitHub Discussions
- Check existing documentation in README.md

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
