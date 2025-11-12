# Changelog

All notable changes to GlassBox MVP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-11

### Added
- Comprehensive test suite for serializer module (`tests/test_serializer.py`)
- Environment configuration support via `.env.example`
- Input validation for `trace_id` parameter to prevent path traversal attacks
- Proper error handling in Streamlit dashboard with user-friendly error messages
- Console script entry points for `glassbox-dashboard` and `glassbox-api`
- Constants for magic numbers in tracer and analyzer modules
- Proper `__init__.py` exports for glassbox package

### Changed
- **BREAKING**: Fixed import paths from `glassbox_*` to `glassbox.*` in all modules
- **BREAKING**: Updated FastAPI lifecycle management from deprecated `@app.on_event` to modern `lifespan` context manager
- CORS configuration now uses environment variables with sensible defaults
- API model selection now configurable via `GLASSBOX_MODEL` environment variable
- API host and port now configurable via `GLASSBOX_HOST` and `GLASSBOX_PORT`
- Delete trace endpoint now uses serializer's delete method instead of duplicating logic
- Updated all placeholder URLs from `yourorg` to `glassbox-ai`

### Fixed
- Import errors in `api/server.py`, `dashboard/app.py`, and test files
- Security vulnerability: CORS now restricts origins instead of allowing all (`*`)
- Security vulnerability: Added trace_id format validation (prevents path traversal)
- Missing main() functions for package entry points
- Memory calculation magic numbers extracted to named constants
- Dashboard now properly displays errors to users instead of silent failures

### Removed
- Unused Node.js dependencies (`package.json`, `package-lock.json`, `node_modules/`)

### Security
- Implemented trace_id validation with regex pattern matching
- Restricted CORS to specific origins (configurable via environment)
- Added proper input validation for API endpoints

## [0.0.1] - 2025-10-25

### Added
- Initial MVP release
- Core tracer for capturing model internals
- Analyzer for ranking attention heads and computing token influence
- Serializer for generating JSON trace artifacts
- Streamlit dashboard for interactive visualization
- FastAPI REST API for programmatic access
- Support for GPT-2, Llama 2, and Mistral models
- Comprehensive README with examples and documentation
