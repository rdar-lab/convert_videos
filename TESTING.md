# Unit Tests

This document describes comprehensive unit tests for the `convert_videos.py` module.

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest -v
```

### Run Tests with Coverage

```bash
pytest -v --cov=convert_videos --cov-report=term-missing
```

### Run Specific Test File

```bash
pytest test_convert_videos.py -v
pytest test_convert_videos_gui.py -v
pytest test_duplicate_detector.py -v
pytest test_docker_live.py -v  # Docker integration test (Linux only, requires Docker)
```

### Run Docker Integration Test

The Docker live integration test validates the full Docker workflow end-to-end:

```bash
# Requires: Linux OS, Docker installed, ffmpeg available
pytest test_docker_live.py -v -s
```

**Note:** This test is resource-intensive and:
- Only runs on Linux systems
- Requires Docker to be installed and running
- Builds a Docker image from the Dockerfile
- Creates and runs a container to test video conversion
- May take several minutes to complete
- Will skip automatically if prerequisites are not met
- Will skip if SSL/network issues prevent Docker build (environment issue)

### Run Specific Test Class

```bash
pytest test_convert_videos.py::TestFileSizeParsing -v
```

### Run Specific Test

```bash
pytest test_convert_videos.py::TestFileSizeParsing::test_parse_file_size_gigabytes -v
```

## Test Coverage

The test suite includes **82 tests** across four test files:

### test_convert_videos.py (65 tests)
- **File size parsing** - Various formats (bytes, KB, MB, GB) with validation
- **Validation functions** - Encoder types, formats, presets, and quality values
- **Preset mapping** - Mapping between x265 and NVENC encoder presets
- **Configuration loading** - YAML config file parsing with defaults and merging
- **Codec detection** - Mocked ffprobe calls to detect video codecs
- **Duration extraction** - Mocked ffprobe calls to get video durations
- **File discovery** - Finding eligible files by size, codec, and exclusion rules
- **Validation and finalization** - Comparing durations and handling success/failure
- **Conversion validation** - Parameter validation in convert_file function
- **Dependency checking** - Ensuring required tools are installed
- **Logging functionality** - Log file setup and configuration
- **Bundled dependencies** - PyInstaller frozen app dependency resolution

### test_convert_videos_gui.py (8 tests)
- **ConversionResult** - Result data structure for conversion operations
- **GUI helper methods** - Size formatting for display

### test_duplicate_detector.py (8 tests)
- **Duplicate detection** - Hash-based video duplicate detection
- **Hamming distance** - Similarity calculation
- **Thumbnail generation** - Comparison thumbnail creation

### test_docker_live.py (1 test)
- **Docker integration** - End-to-end Docker workflow testing
  - Prerequisites checking (Linux OS, Docker availability)
  - Docker image building from Dockerfile
  - Test video creation (minimal MP4 or ffmpeg-generated)
  - Configuration deployment
  - Container execution and video conversion
  - Result validation (converted file created, original removed)
  - Resource cleanup (containers and images)
  - Graceful skipping on environment issues

Current code coverage: **66%**

## Continuous Integration

Tests are automatically run via GitHub Actions on:
- Push to main/master/develop branches
- Pull requests targeting main/master/develop branches

The CI pipeline runs on multiple platforms using a matrix strategy:
- **Operating Systems**: Ubuntu Latest, Windows Latest, macOS Latest
- **Python Version**: 3.11
- **Test Files**: All test files (test_convert_videos.py, test_convert_videos_gui.py, test_duplicate_detector.py)
- **Strategy**: fail-fast is disabled to ensure all platform tests complete even if one fails

### Docker Integration Test Workflow

A separate GitHub Actions workflow (`test-docker-live.yml`) is available for Docker integration testing:
- **Trigger**: Manual only (workflow_dispatch) - not run automatically
- **Purpose**: Validates the complete Docker build and runtime workflow
- **Platform**: Ubuntu Latest only
- **Requirements**: Docker must be available (always true in GitHub Actions)
- **Duration**: ~5-10 minutes depending on Docker build cache

To run the Docker integration test manually in GitHub Actions:
1. Navigate to the "Actions" tab in the repository
2. Select "Docker Live Integration Tests" workflow
3. Click "Run workflow"
4. Optionally adjust the timeout parameter (default: 180 seconds)

## Cross-Platform Compatibility

Tests are designed to run on Windows, macOS, and Linux:
- Path operations use `pathlib.Path` for cross-platform compatibility
- Temporary directories use `tempfile.TemporaryDirectory()`
- Mock paths in tests are platform-independent
- Windows-specific executable extensions (.exe) are handled appropriately

## Test Structure

Tests are organized into logical test classes:

- `TestFileSizeParsing` - File size parsing and validation
- `TestValidationFunctions` - Input validation functions
- `TestPresetMapping` - Encoder preset mapping logic
- `TestConfigLoading` - Configuration file loading
- `TestGetCodec` - Video codec detection
- `TestGetDuration` - Video duration extraction
- `TestFindEligibleFiles` - File discovery and filtering
- `TestValidateAndFinalize` - Conversion validation and cleanup
- `TestConvertFile` - Main conversion function validation
- `TestCheckDependencies` - Dependency verification

## Writing New Tests

When adding new functionality to `convert_videos.py`:

1. Add corresponding tests to `test_convert_videos.py`
2. Use mocking for external dependencies (subprocess, file I/O)
3. Test both success and error cases
4. Follow the existing test naming convention: `test_<function_name>_<scenario>`
5. Run tests locally before committing
6. Ensure tests pass in CI before merging

## Mocking Strategy

Tests use Python's `unittest.mock` module to:
- Mock subprocess calls to ffprobe and HandBrakeCLI
- Mock file system operations when appropriate
- Create temporary directories for file-based tests
- Isolate tests from external dependencies
