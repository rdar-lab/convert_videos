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
pytest -v --cov=src --cov-report=term-missing
```

### Run Docker Integration Test

The Docker live integration test validates the full Docker workflow end-to-end:

```bash
# Requires: Linux OS, Docker installed
# Note: Docker tests are excluded from default test runs
pytest tests/test_docker_live.py -v -s -m docker
```

**Note:** This test is resource-intensive and:
- **Excluded from default test runs** - must use `-m docker` flag
- Only runs on Linux systems
- Requires Docker to be installed and running
- Uses static test video file (tests/test_fixtures/test_video.mp4)
- Builds a Docker image from the Dockerfile
- Creates and runs a container to test video conversion
- May take several minutes to complete
- Will skip automatically if prerequisites are not met
- Will skip if SSL/network issues prevent Docker build (environment issue)
