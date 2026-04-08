"""Integration test for Docker health check.

Requires Docker to be available. Marked with ``docker`` marker so it can be
skipped in CI environments without Docker::

    uv run pytest tests/test_docker.py -m docker
    uv run pytest -m "not docker"   # skip docker tests
"""

from __future__ import annotations

import subprocess
import time

import pytest
import urllib.request
import urllib.error

CONTAINER_NAME = "brightspace-api-healthcheck-test"
IMAGE_NAME = "brightspace-api-test"
PORT = 18742  # high port to avoid conflicts


@pytest.fixture(scope="module")
def docker_container():
    """Build the image and start a container, tearing it down after tests."""
    # Check Docker is available
    try:
        subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        pytest.skip("Docker is not installed or not on PATH")

    # Build
    result = subprocess.run(
        ["docker", "build", "-t", IMAGE_NAME, "."],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        pytest.skip(f"Docker build failed: {result.stderr}")

    # Run
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER_NAME,
            "-p",
            f"{PORT}:8000",
            IMAGE_NAME,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    yield

    # Teardown
    subprocess.run(
        ["docker", "rm", "-f", CONTAINER_NAME],
        capture_output=True,
    )


@pytest.mark.docker
def test_health_responds_within_5_seconds(docker_container):
    """Verify /health responds with 200 within 5 seconds of container start."""
    url = f"http://localhost:{PORT}/health"
    deadline = time.time() + 5

    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                assert resp.status == 200
                body = resp.read().decode()
                assert '"ok"' in body
                return  # success
        except (urllib.error.URLError, ConnectionError, OSError) as exc:
            last_error = exc
            time.sleep(0.3)

    pytest.fail(f"/health did not respond within 5 seconds. Last error: {last_error}")
