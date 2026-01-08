# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of tap-openproject
- Projects stream with full metadata extraction
- Singer protocol compliance (SCHEMA, RECORD, STATE messages)
- HTTP client with retry logic and rate limiting
- surveilr integration wrapper
- Self-contained virtual environment management
- Configuration via JSON files or environment variables

### Features
- Extract projects from OpenProject API
- Support for both cloud and self-hosted instances
- Configurable timeout and retry settings
- API key authentication
- Comprehensive error handling
- Logging to stderr (Singer compliant)

## [0.1.0] - 2026-01-08

### Added
- Initial beta release
- Core functionality for OpenProject data extraction
- Documentation and examples
- MIT License

[Unreleased]: https://github.com/surveilr/tap-openproject/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/surveilr/tap-openproject/releases/tag/v0.1.0
