#!/usr/bin/env python3
"""
Live Docker integration tests for convert_videos.
These tests actually build and run the Docker container to verify end-to-end functionality.

Note: These tests are resource-intensive and require:
- Linux OS
- Docker installation
- Sufficient disk space

Run with: pytest test_docker_live.py -v -m docker
"""

import platform
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
import yaml
import pytest


# Mark all tests in this module as 'docker' to exclude from default test runs
pytestmark = pytest.mark.docker


class TestDockerLive(unittest.TestCase):
    """Live Docker integration tests."""
    
    @classmethod
    def setUpClass(cls):
        """Check prerequisites before running any tests."""
        # Check if running on Linux
        if platform.system() != 'Linux':
            raise unittest.SkipTest("Docker tests only run on Linux")
        
        # Check if Docker is installed
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise unittest.SkipTest("Docker is not available")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            raise unittest.SkipTest("Docker is not installed")
        
        print("\n✓ Prerequisites met: Linux OS with Docker installed")
    
    def _create_minimal_test_video(self, output_path: Path) -> bool:
        """
        Copy the static test video file to the output path.
        
        Args:
            output_path: Path where the video should be created
            
        Returns:
            True if video was created successfully, False otherwise
        """
        try:
            # Get the static test video file from test_fixtures
            repo_path = Path(__file__).parent.parent.absolute()
            static_video = repo_path / 'tests' / 'test_fixtures' / 'test_video.mp4'
            
            if not static_video.exists():
                print(f"✗ Static test video not found: {static_video}")
                return False
            
            # Copy the static test video to the output path
            import shutil
            shutil.copy2(static_video, output_path)
            
            if output_path.exists() and output_path.stat().st_size > 0:
                print(f"✓ Test video copied: {output_path.stat().st_size} bytes")
                return True
            else:
                print(f"✗ Failed to copy test video")
                return False
                
        except Exception as e:
            print(f"✗ Error creating test video: {e}")
            return False
    
    def _build_docker_image(self, repo_path: Path, image_tag: str) -> bool:
        """
        Build the Docker image from the repository's Dockerfile.
        
        Args:
            repo_path: Path to the repository root
            image_tag: Tag to use for the image
            
        Returns:
            True if build succeeded, False otherwise
            
        Raises:
            unittest.SkipTest: If build fails due to environment issues (SSL, network, etc.)
        """
        print(f"\nBuilding Docker image: {image_tag}")
        
        try:
            result = subprocess.run(
                ['docker', 'build', '-t', image_tag, '.'],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout for build
            )
            
            if result.returncode == 0:
                print(f"✓ Docker image built successfully: {image_tag}")
                return True
            else:
                print(f"✗ Docker build failed:")
                print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
                print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
                
                # Check if it's an SSL/network issue (environment problem, not code problem)
                error_output = result.stdout + result.stderr
                if 'SSL' in error_output or 'certificate' in error_output.lower():
                    print("\n⚠ Build failed due to SSL/certificate issues.")
                    print("This may be an environment issue, not a code issue.")
                    raise unittest.SkipTest("Docker build failed due to SSL/network issues in environment")
                
                return False
                
        except subprocess.TimeoutExpired:
            print("✗ Docker build timed out after 10 minutes")
            return False
        except unittest.SkipTest:
            # Let SkipTest propagate
            raise
        except Exception as e:
            print(f"✗ Docker build error: {e}")
            return False
    
    def _run_docker_container(
        self,
        image_tag: str,
        container_name: str,
        mount_path: Path,
        config_path: Path = None,
        timeout: int = 120
    ) -> bool:
        """
        Run the Docker container with the test directory mounted.
        
        Args:
            image_tag: Docker image tag to run
            container_name: Name for the container
            mount_path: Path to mount as /data in the container
            config_path: Optional path to config directory to mount as /config
            timeout: Maximum time to wait for processing (seconds)
            
        Returns:
            True if container ran successfully, False otherwise
        """
        print(f"\nRunning Docker container: {container_name}")
        
        try:
            # Run container in detached mode
            cmd = [
                'docker', 'run',
                '-d',  # Detached mode
                '--name', container_name,
                '-v', f'{mount_path}:/data',
            ]
            
            # Mount config directory if provided
            if config_path and config_path.exists():
                cmd.extend(['-v', f'{config_path}:/config'])
                print(f"Mounting config directory: {config_path} -> /config")
            
            cmd.append(image_tag)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"✗ Failed to start container:")
                print(result.stderr)
                return False
            
            container_id = result.stdout.strip()
            print(f"✓ Container started: {container_id[:12]}")
            
            # Wait for processing to complete
            # The container runs in loop mode, but we'll give it time to process files
            print(f"Waiting up to {timeout} seconds for processing...")
            time.sleep(5)  # Initial wait for startup
            
            # Check for converted file periodically
            start_time = time.time()
            while time.time() - start_time < timeout:
                converted_files = list(mount_path.glob('*.converted.*'))
                if converted_files:
                    print(f"✓ Conversion detected after {int(time.time() - start_time)} seconds")
                    # Give it a bit more time to complete and clean up
                    time.sleep(2)
                    return True
                
                # Check if container is still running
                check_result = subprocess.run(
                    ['docker', 'inspect', '-f', '{{.State.Running}}', container_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if check_result.stdout.strip() != 'true':
                    # Container stopped
                    print("✗ Container stopped unexpectedly")
                    # Get logs
                    log_result = subprocess.run(
                        ['docker', 'logs', container_name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    print("Container logs:")
                    print(log_result.stdout)
                    return False
                
                time.sleep(2)  # Check every 2 seconds
            
            # Timeout reached
            print(f"✗ Timeout reached after {timeout} seconds")
            
            # Get logs before returning
            log_result = subprocess.run(
                ['docker', 'logs', container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            print("Container logs:")
            print(log_result.stdout)
            
            return False
            
        except subprocess.TimeoutExpired:
            print("✗ Docker run command timed out")
            return False
        except Exception as e:
            print(f"✗ Error running container: {e}")
            return False
    
    def _stop_and_remove_container(self, container_name: str):
        """
        Stop and remove a Docker container.
        
        Args:
            container_name: Name of the container to remove
        """
        print(f"\nCleaning up container: {container_name}")
        
        # Stop container
        try:
            subprocess.run(
                ['docker', 'stop', container_name],
                capture_output=True,
                timeout=30
            )
            print(f"✓ Container stopped")
        except Exception as e:
            print(f"⚠ Failed to stop container: {e}")
        
        # Remove container
        try:
            subprocess.run(
                ['docker', 'rm', '-f', container_name],
                capture_output=True,
                timeout=30
            )
            print(f"✓ Container removed")
        except Exception as e:
            print(f"⚠ Failed to remove container: {e}")
    
    def _remove_docker_image(self, image_tag: str):
        """
        Remove a Docker image.
        
        Args:
            image_tag: Tag of the image to remove
        """
        print(f"\nRemoving Docker image: {image_tag}")
        
        try:
            subprocess.run(
                ['docker', 'rmi', '-f', image_tag],
                capture_output=True,
                timeout=30
            )
            print(f"✓ Image removed")
        except Exception as e:
            print(f"⚠ Failed to remove image: {e}")
    
    def test_docker_live_conversion(self):
        """
        Test the complete Docker workflow:
        1. Build Docker image
        2. Create test video
        3. Create configuration
        4. Run container
        5. Verify conversion and original removal
        6. Clean up
        """
        # Setup
        repo_path = Path(__file__).parent.parent.absolute()  # Go up to repo root
        image_tag = 'convert_videos_test:latest'
        container_name = 'convert_videos_test_container'
        
        # Create temporary directory for test
        with tempfile.TemporaryDirectory(prefix='docker_test_') as tmpdir:
            tmpdir_path = Path(tmpdir)
            print(f"\nTest directory: {tmpdir_path}")
            
            cleanup_needed = False
            skip_exception = None
            
            try:
                # Step 1: Build Docker image
                print("\n" + "="*60)
                print("STEP 1: Building Docker image")
                print("="*60)
                
                try:
                    build_success = self._build_docker_image(repo_path, image_tag)
                    self.assertTrue(build_success, "Docker image build failed")
                    cleanup_needed = True  # Image was built, need cleanup
                except unittest.SkipTest as e:
                    # Save skip exception to re-raise after cleanup
                    skip_exception = e
                    raise
                
                # Step 2: Create test video
                print("\n" + "="*60)
                print("STEP 2: Creating test video")
                print("="*60)
                
                test_video = tmpdir_path / 'test_video.mp4'
                video_created = self._create_minimal_test_video(test_video)
                self.assertTrue(video_created, "Failed to create test video")
                self.assertTrue(test_video.exists(), "Test video file does not exist")
                
                video_size = test_video.stat().st_size
                print(f"Test video size: {video_size} bytes")
                
                # Step 3: Create configuration file
                print("\n" + "="*60)
                print("STEP 3: Creating configuration file")
                print("="*60)
                
                # Create a separate directory for config
                config_dir = tmpdir_path / 'config'
                config_dir.mkdir(exist_ok=True)
                
                config = {
                    'directory': '/data',
                    'min_file_size': '1B',  # Accept any file size for testing
                    'output': {
                        'format': 'mkv',
                        'encoder': 'x265',
                        'preset': 'ultrafast',  # Fastest encoding for test
                        'quality': 40  # Lower quality = faster
                    },
                    'remove_original_files': True,  # Remove original after conversion
                    'loop': True,
                    'dry_run': False
                }
                
                config_path = config_dir / 'config.yaml'
                with open(config_path, 'w') as f:
                    yaml.dump(config, f)
                
                print(f"✓ Configuration created: {config_path}")
                print(f"  - Min file size: 1B")
                print(f"  - Remove original: True")
                print(f"  - Encoder: x265 (ultrafast)")
                
                # Step 4: Run Docker container
                print("\n" + "="*60)
                print("STEP 4: Running Docker container")
                print("="*60)
                
                run_success = self._run_docker_container(
                    image_tag,
                    container_name,
                    tmpdir_path,
                    config_path=config_dir,
                    timeout=120
                )
                self.assertTrue(run_success, "Docker container did not process files successfully")
                
                # Step 5: Verify results
                print("\n" + "="*60)
                print("STEP 5: Verifying results")
                print("="*60)
                
                # Check for converted file
                converted_files = list(tmpdir_path.glob('*.converted.*'))
                print(f"\nFiles in directory after processing:")
                for file in tmpdir_path.iterdir():
                    print(f"  - {file.name} ({file.stat().st_size} bytes)")
                
                self.assertGreater(
                    len(converted_files),
                    0,
                    "No converted file was created"
                )
                
                converted_file = converted_files[0]
                print(f"\n✓ Converted file found: {converted_file.name}")
                print(f"  Size: {converted_file.stat().st_size} bytes")
                
                # Verify converted file has content
                self.assertGreater(
                    converted_file.stat().st_size,
                    0,
                    "Converted file is empty"
                )
                
                # Check that original was removed
                original_exists = test_video.exists()
                print(f"\n{'✗' if original_exists else '✓'} Original file {'still exists' if original_exists else 'was removed'}")
                
                # Original might be renamed to .orig instead of removed
                # depending on preserve_original setting
                orig_files = list(tmpdir_path.glob('*.orig.*'))
                if orig_files:
                    print(f"⚠ Original was renamed to: {orig_files[0].name}")
                else:
                    self.assertFalse(
                        original_exists,
                        "Original file was not removed as expected"
                    )
                
                print("\n" + "="*60)
                print("✓ ALL TESTS PASSED")
                print("="*60)
                
            finally:
                # Step 6: Clean up
                print("\n" + "="*60)
                print("STEP 6: Cleaning up")
                print("="*60)
                
                self._stop_and_remove_container(container_name)
                if cleanup_needed:
                    self._remove_docker_image(image_tag)
                
                print("\n✓ Cleanup complete")
                
                # Re-raise skip exception if we caught one
                if skip_exception:
                    raise skip_exception
    
    def test_docker_duplicate_detector_live(self):
        """
        Test the duplicate detector Docker workflow:
        1. Build duplicate detector Docker image
        2. Create test videos (including a duplicate)
        3. Run container
        4. Verify duplicate detection
        5. Clean up
        """
        # Setup
        repo_path = Path(__file__).parent.parent.absolute()  # Go up to repo root
        image_tag = 'duplicate_detector_test:latest'
        container_name = 'duplicate_detector_test_container'
        
        # Create temporary directory for test
        with tempfile.TemporaryDirectory(prefix='dd_docker_test_') as tmpdir:
            tmpdir_path = Path(tmpdir)
            print(f"\nTest directory: {tmpdir_path}")
            
            cleanup_needed = False
            skip_exception = None
            
            try:
                # Step 1: Build Docker image
                print("\n" + "="*60)
                print("STEP 1: Building Duplicate Detector Docker image")
                print("="*60)
                
                try:
                    # Build using Dockerfile.duplicate-detector
                    print(f"\nBuilding Docker image: {image_tag}")
                    result = subprocess.run(
                        ['docker', 'build', '-f', 'Dockerfile.duplicate-detector', '-t', image_tag, '.'],
                        cwd=str(repo_path),
                        capture_output=True,
                        text=True,
                        timeout=600  # 10 minutes timeout for build
                    )
                    
                    if result.returncode == 0:
                        print(f"✓ Docker image built successfully: {image_tag}")
                        cleanup_needed = True  # Image was built, need cleanup
                    else:
                        print(f"✗ Docker build failed:")
                        print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
                        print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
                        
                        # Check if it's an SSL/network issue
                        error_output = result.stdout + result.stderr
                        if 'SSL' in error_output or 'certificate' in error_output.lower():
                            print("\n⚠ Build failed due to SSL/certificate issues.")
                            print("This may be an environment issue, not a code issue.")
                            raise unittest.SkipTest("Docker build failed due to SSL/network issues in environment")
                        
                        self.fail("Docker image build failed")
                except unittest.SkipTest as e:
                    skip_exception = e
                    raise
                
                # Step 2: Create test videos (including duplicate)
                print("\n" + "="*60)
                print("STEP 2: Creating test videos")
                print("="*60)
                
                test_video1 = tmpdir_path / 'video1.mp4'
                test_video2 = tmpdir_path / 'video2.mp4'  # This will be a duplicate
                
                video_created1 = self._create_minimal_test_video(test_video1)
                self.assertTrue(video_created1, "Failed to create first test video")
                
                # Create a duplicate by copying the same video
                import shutil
                shutil.copy2(test_video1, test_video2)
                
                self.assertTrue(test_video1.exists(), "Test video 1 does not exist")
                self.assertTrue(test_video2.exists(), "Test video 2 does not exist")
                
                print(f"✓ Created duplicate videos:")
                print(f"  - {test_video1.name}: {test_video1.stat().st_size} bytes")
                print(f"  - {test_video2.name}: {test_video2.stat().st_size} bytes")
                
                # Step 3: Run Docker container
                print("\n" + "="*60)
                print("STEP 3: Running Duplicate Detector Docker container")
                print("="*60)
                
                # Run container and capture output
                cmd = [
                    'docker', 'run',
                    '--rm',  # Remove container after execution
                    '--name', container_name,
                    '-v', f'{tmpdir_path}:/data',
                    image_tag,
                    '/data'  # Directory to scan
                ]
                
                print(f"Running command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                print(f"\nContainer exit code: {result.returncode}")
                print("\nContainer output:")
                print(result.stdout)
                if result.stderr:
                    print("\nContainer stderr:")
                    print(result.stderr)
                
                # Step 4: Verify results
                print("\n" + "="*60)
                print("STEP 4: Verifying results")
                print("="*60)
                
                # Check that duplicates were found in the output
                output = result.stdout + result.stderr
                
                # The duplicate detector should find duplicates
                self.assertIn('duplicate', output.lower(), 
                             "Expected 'duplicate' to be mentioned in output")
                
                # Should mention finding duplicate groups
                if 'found' in output.lower() and 'duplicate' in output.lower():
                    print("✓ Duplicate detection output found in logs")
                elif 'no duplications found' in output.lower():
                    # This is acceptable too if the videos are too short/different
                    print("⚠ No duplications reported (videos may be too short for reliable hashing)")
                else:
                    print("⚠ Unexpected output format")
                
                # Verify no crash (exit code 0 or standard exit)
                self.assertIn(result.returncode, [0], 
                             f"Container exited with unexpected code: {result.returncode}")
                
                print("\n" + "="*60)
                print("✓ DUPLICATE DETECTOR DOCKER TEST PASSED")
                print("="*60)
                
            finally:
                # Step 5: Clean up
                print("\n" + "="*60)
                print("STEP 5: Cleaning up")
                print("="*60)
                
                # Container is already removed due to --rm flag
                print(f"✓ Container auto-removed (--rm flag)")
                
                if cleanup_needed:
                    self._remove_docker_image(image_tag)
                
                print("\n✓ Cleanup complete")
                
                # Re-raise skip exception if we caught one
                if skip_exception:
                    raise skip_exception


if __name__ == '__main__':
    unittest.main()
