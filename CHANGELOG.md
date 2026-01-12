# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Migrated to Meltano Singer SDK from legacy singer-python
- Replaced setup.py with modern pyproject.toml (Poetry)
- Complete rewrite of stream implementation using SDK RESTStream
- Updated JSON Schema with proper types and replication key

### Added
- Incremental sync support via `updatedAt` replication key
- Stream Maps capability for inline transformations
- Automatic pagination handling
- Built-in retry logic and error handling (SDK)
- Schema flattening support
- Batch processing capability
- Full JSON Schema validation
- `--about` flag for plugin metadata

### Removed
- Legacy http_client.py (replaced by SDK authenticator)
- Legacy context.py (no longer needed)
- Legacy run_with_config.py (replaced by SDK CLI)
- setup.py and setup.cfg (replaced by pyproject.toml)

## [0.2.0] - 2026-01-12

### Added
- **Meltano Singer SDK implementation** - Complete migration to modern SDK
- Incremental sync with state management
- Stream Maps for data transformation
- Comprehensive documentation (QUICKSTART, CONTRIBUTING)
- Meltano Hub plugin definition (meltano-hub.yml)
- Poetry-based dependency management
- Development dependencies (pytest, ruff)

### Changed
- Primary key changed from string to integer type
- Schema includes full OpenProject API response structure
- CLI now uses SDK built-in argument parser
- Improved error messages and logging

## [0.1.0] - 2026-01-08

### Added
- Initial release with legacy singer-python
- Projects stream basic extraction
- API key authentication
- Manual retry logic
- surveilr integration wrapper

[Unreleased]: https://github.com/surveilr/tap-openproject/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/surveilr/tap-openproject/releases/tag/v0.2.0
[0.1.0]: https://github.com/surveilr/tap-openproject/releases/tag/v0.1.0
